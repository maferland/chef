#!/usr/bin/env python3
"""
chef:publish — map a chef:plan session to mise.'s ingest API and push it.

Usage:
  python3 publish.py [session-path] [--dry-run] [--model NAME]

Args:
  session-path  path to a session folder (default: most recent ./sessions/*/)
  --dry-run     print the mapped mise. payload, skip the network call
  --model       value for source.model provenance (default: null)

Env (never hardcode, never commit):
  MISE_BASE_URL   e.g. http://localhost:3000 or https://mise.maferland.com
  MISE_API_KEY    household bearer token (Authorization: Bearer <key>)

Reads: {session}/plan.md (required), {session}/shopping.md (optional).
Writes: {session}/published.json on a successful (non-dry-run) publish.

chef:plan is the only session shape this parses today — it is the only skill
that saves a full recipe (grouped ingredients + numbered steps) in one file.
chef:prep sessions are NOT supported: plan.md there lists meal summaries
(protein/veg/base/portions), not per-meal ingredients and steps, so there is
nothing to map onto mise.'s recipe schema without inventing content chef
never wrote. See SKILL.md "Known gaps".
"""

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from glob import glob
from pathlib import Path

UNIT_WORDS = {
    "g", "kg", "mg", "ml", "mL", "l", "L", "cl",
    "tbsp", "tsp", "cup", "cups", "oz", "lb", "lbs",
    "clove", "cloves", "sprig", "sprigs", "bunch", "bunches",
    "pinch", "pinches", "whole", "slice", "slices", "can", "cans",
    "piece", "pieces",
}

QTY_RE = re.compile(r"^[\d½¼¾⅓⅔⅛./\-–\s]+$")


def fail(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def find_session_dir(arg: str | None) -> Path:
    if arg:
        path = Path(arg)
        if not path.is_dir():
            fail(f"session folder not found: {path}")
        return path

    candidates = sorted(glob("./sessions/*/"), key=lambda p: Path(p).stat().st_mtime, reverse=True)
    if not candidates:
        fail("no ./sessions/*/ folder found. Run /chef:plan first, or pass a session path.")
    return Path(candidates[0])


def split_ingredient_line(line: str) -> dict:
    """Best-effort split of a chef:plan ingredient bullet into quantity/unit/item.

    chef writes lines like "1 whole chicken (~1.5 kg)" or "Salt, freshly ground
    black pepper" — there is no delimiter, so this is a heuristic over chef's
    own consistent phrasing, not a general parser.
    """
    tokens = line.split()
    qty_tokens = []
    i = 0
    while i < len(tokens) and QTY_RE.match(tokens[i]):
        qty_tokens.append(tokens[i])
        i += 1

    unit = None
    if i < len(tokens) and tokens[i].rstrip(",") in UNIT_WORDS:
        unit = tokens[i].rstrip(",")
        i += 1

    item = " ".join(tokens[i:]).strip() or line.strip()
    quantity = " ".join(qty_tokens) if qty_tokens else None

    return {
        "quantity": quantity,
        "unit": unit,
        "item": item,
        "notes": None,
        "group": None,
    }


def parse_time_minutes(meta_line: str) -> int | None:
    hm = re.search(r"(\d+)\s*h\s*(\d+)?", meta_line)
    if hm:
        hours = int(hm.group(1))
        minutes = int(hm.group(2)) if hm.group(2) else 0
        return hours * 60 + minutes

    m = re.search(r"(\d+)\s*min", meta_line)
    if m:
        return int(m.group(1))

    return None


def parse_servings(meta_line: str) -> int:
    m = re.search(r"Serves\s+(\d+)", meta_line, re.IGNORECASE)
    return int(m.group(1)) if m else 2


def parse_recipe(markdown: str) -> dict:
    lines = markdown.splitlines()

    title = None
    meta_line = ""
    for idx, line in enumerate(lines):
        if line.startswith("# "):
            title = line[2:].strip()
            # first non-blank line after the header is the meta line
            for follow in lines[idx + 1:]:
                if follow.strip():
                    meta_line = follow.strip()
                    break
            break

    if not title:
        fail("no recipe title found (expected a top-level '# Recipe Name' heading in plan.md)")

    ingredients = []
    current_group = None
    in_ingredients = False
    for line in lines:
        if re.match(r"^#{1,3}\s+Ingredients", line, re.IGNORECASE):
            in_ingredients = True
            continue
        if in_ingredients and re.match(r"^#{1,3}\s+\S", line):
            break
        if not in_ingredients:
            continue

        bold = re.match(r"^\*\*(.+?)\*\*$", line.strip())
        if bold:
            current_group = bold.group(1).strip()
            continue

        if line.strip().startswith("- "):
            parsed = split_ingredient_line(line.strip()[2:].strip())
            parsed["group"] = current_group
            ingredients.append(parsed)

    if not ingredients:
        fail("no ingredients found under an 'Ingredients' heading in plan.md")

    steps = []
    in_instructions = False
    for line in lines:
        if re.match(r"^#{1,3}\s+Instructions", line, re.IGNORECASE):
            in_instructions = True
            continue
        if in_instructions and re.match(r"^#{1,3}\s+\S", line):
            break
        if not in_instructions:
            continue

        step = re.match(r"^\d+\.\s+(.*)", line.strip())
        if step:
            steps.append(step.group(1).strip())
        elif steps and line.strip():
            # continuation of the previous numbered step
            steps[-1] = f"{steps[-1]} {line.strip()}"

    if not steps:
        fail("no numbered steps found under an 'Instructions' heading in plan.md")

    tips = []
    in_tips = False
    for line in lines:
        if re.match(r"^#{1,3}\s+Tips", line, re.IGNORECASE):
            in_tips = True
            continue
        if in_tips and re.match(r"^#{1,3}\s+\S", line):
            break
        if in_tips and line.strip().startswith("- "):
            tips.append(line.strip()[2:].strip())

    return {
        "title": title,
        "description": "\n".join(f"- {tip}" for tip in tips) if tips else None,
        "servings": parse_servings(meta_line),
        "time_minutes": parse_time_minutes(meta_line),
        "ingredients": ingredients,
        "steps": steps,
    }


def parse_shopping(markdown: str) -> list[dict]:
    """Optional: shopping.md → grocery_items for the collection payload."""
    items = []
    store = None
    for line in markdown.splitlines():
        heading = re.match(r"^##\s+(.+)", line)
        if heading and heading.group(1).strip().lower() not in {"order ahead"}:
            store = heading.group(1).strip()
            continue

        bullet = re.match(r"^-\s+\[([ x])\]\s+(.*)", line)
        if not bullet:
            continue

        checked = bullet.group(1) == "x"
        text = re.sub(r"\*\(([^)]*)\)\*", "", bullet.group(2)).strip()
        note_match = re.search(r"\*\(([^)]*)\)\*", bullet.group(2))
        parsed = split_ingredient_line(text)

        items.append({
            "item": parsed["item"],
            "quantity": parsed["quantity"],
            "store": store,
            "category": None,
            "checked": checked,
            "notes": note_match.group(1) if note_match else None,
        })

    return items


def normalized_ingredients_key(ingredients: list[dict]) -> str:
    parts = sorted(
        f"{i['quantity'] or ''}|{i['unit'] or ''}|{i['item'].strip().lower()}" for i in ingredients
    )
    return "\n".join(parts)


def recipe_idempotency_key(title: str, ingredients: list[dict]) -> str:
    payload = f"{title.strip().lower()}\n{normalized_ingredients_key(ingredients)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_recipe_payload(recipe: dict, model: str | None) -> dict:
    return {
        "title": recipe["title"],
        "description": recipe["description"],
        "servings": recipe["servings"],
        "time_minutes": recipe["time_minutes"],
        "ingredients": recipe["ingredients"],
        "steps": recipe["steps"],
        "nutrition": None,
        "source": {"kind": "ai-agent", "agent": "chef", "model": model, "url": None},
        "verified": False,
        "visibility": "private",
        "idempotency_key": recipe_idempotency_key(recipe["title"], recipe["ingredients"]),
        "tags": [],
    }


def build_collection_payload(recipe_payload: dict, grocery_items: list[dict], model: str | None) -> dict:
    collection_key_src = f"{recipe_payload['title'].strip().lower()}\n{recipe_payload['idempotency_key']}"
    return {
        "title": recipe_payload["title"],
        "starts_on": None,
        "source": {"kind": "ai-agent", "agent": "chef", "model": model, "url": None},
        "idempotency_key": hashlib.sha256(collection_key_src.encode("utf-8")).hexdigest(),
        "grocery_items": grocery_items,
        "recipes": [recipe_payload],
    }


def post_json(base_url: str, api_key: str, path: str, payload: dict) -> dict:
    url = base_url.rstrip("/") + path
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return {"status": response.status, "body": json.loads(response.read().decode("utf-8"))}
    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8")
        try:
            parsed = json.loads(error_body)
        except json.JSONDecodeError:
            parsed = {"error": error_body}
        fail(f"POST {path} failed ({error.code}): {parsed.get('error', parsed)} {parsed.get('issues', '')}".strip())
    except urllib.error.URLError as error:
        fail(f"could not reach {url}: {error.reason}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("session_path", nargs="?", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--model", default=None)
    args = parser.parse_args()

    session_dir = find_session_dir(args.session_path)
    plan_path = session_dir / "plan.md"
    if not plan_path.is_file():
        fail(f"{plan_path} not found — chef:publish only supports chef:plan sessions today (see SKILL.md)")

    recipe = parse_recipe(plan_path.read_text())

    shopping_path = session_dir / "shopping.md"
    grocery_items = parse_shopping(shopping_path.read_text()) if shopping_path.is_file() else []

    recipe_payload = build_recipe_payload(recipe, args.model)
    collection_payload = build_collection_payload(recipe_payload, grocery_items, args.model)

    if args.dry_run:
        print(json.dumps(collection_payload, indent=2))
        print("\n(dry run — nothing was sent)")
        return

    base_url = os.environ.get("MISE_BASE_URL")
    api_key = os.environ.get("MISE_API_KEY")
    if not base_url or not api_key:
        fail("MISE_BASE_URL and MISE_API_KEY must be set in the environment (never hardcode these).")

    result = post_json(base_url, api_key, "/api/v1/collections", collection_payload)
    collection = result["body"]["collection"]
    duplicate = result["body"].get("duplicate", False)

    published = {
        "collection_id": collection["id"],
        "duplicate": duplicate,
        "url": f"{base_url.rstrip('/')}/collections/{collection['id']}",
        "published_at": datetime.now(timezone.utc).isoformat(),
    }
    (session_dir / "published.json").write_text(json.dumps(published, indent=2) + "\n")

    verb = "Already published" if duplicate else "Published"
    print(f"{verb}: {recipe_payload['title']}")
    print(f"mise. collection: {published['url']}")
    print("(the /collections/:id page isn't built yet in mise. as of this writing — see SKILL.md)")


if __name__ == "__main__":
    main()
