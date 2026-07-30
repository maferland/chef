---
name: publish
description: Publish a chef:plan session to mise. (the shared household meal-planning app) — maps the saved recipe to mise.'s ingest API and pushes it as a collection. Use when the user wants to send a recipe or meal plan to mise., or asks to "publish", "send to mise", or "push to the app".
user_invocable: true
---

# Chef Publish

Push a saved `chef:plan` session to mise. so it shows up on both phones. Reads the session chef already saved — never re-derives or invents recipe content.

## Setup (once)

mise. auth is a personal API key, read from the environment — never store it in chef's config file or in this repo:

```bash
export MISE_BASE_URL="https://mise.maferland.com"   # or http://localhost:3000 for local dev
export MISE_API_KEY="..."                           # household bearer token, from mise. settings
```

If either is unset, the script fails with a clear error before doing anything else.

## Usage

```bash
python3 skills/publish/scripts/publish.py [session-path] [--dry-run] [--model NAME]
```

- **session-path**: a `chef:plan` session folder (e.g. `./sessions/2026-07-30-duck-mole/`). Omit to use the most recently modified `./sessions/*/`.
- **--dry-run**: print the mapped mise. payload and exit — no network call. Always run this first when debugging a mapping.
- **--model**: recorded as `source.model` (provenance). Optional.

## Workflow

1. Identify the session folder (argument, or most recent).
2. Run the script. It reads `plan.md` (required) and `shopping.md` (optional, folded into the collection's grocery list).
3. Report the result to the user:
   - Dry run: show the payload.
   - Real publish: report success/duplicate and the collection id. Mention the printed URL is a best guess (see Known gaps) — the phone view isn't live yet.
4. On any failure (auth, validation, network), show the script's error verbatim. Never say "published" unless the script confirmed it.

## Mapping (chef → mise.)

Everything goes through `POST /api/v1/collections`, one recipe per collection today:

| chef (`plan.md`) | mise. field |
|---|---|
| `# Recipe Name` heading | `recipes[0].title`, and the collection `title` |
| meta line (`Serves N`) | `recipes[0].servings` |
| meta line (`1h15` / `45min`) | `recipes[0].time_minutes` |
| `## Ingredients` groups + bullets | `recipes[0].ingredients[]` (`quantity`/`unit` split from the bullet text, `group` from the bold subheading) |
| `### Instructions` numbered list | `recipes[0].steps[]` (one string per step) |
| `### Tips` bullets | `recipes[0].description` (joined; mise. has no dedicated tips field) |
| `shopping.md` bullets, grouped by `## Store` | `grocery_items[]` (`store` from the heading, `notes` from a trailing `*(...)*` note, `checked` from `[x]`) |
| — (always) | `source: {kind: "ai-agent", agent: "chef", model, url: null}`, `verified: false`, `visibility: "private"` |
| `sha256(title + normalized ingredients)` | `idempotency_key` (recipe and, derived from it, the collection) |

Drink pairing (`## Drink Pairing`) has no field in mise.'s schema and is dropped.

## Known gaps — read before publishing a `chef:prep` week

**Only `chef:plan` sessions are supported.** `chef:prep`'s `plan.md` lists meal summaries (protein/veg/base, portions, reheats) — it does not carry per-meal ingredient lists or numbered steps the way `chef:plan`'s does. There is nothing in a `chef:prep` session to map onto mise.'s `ingredients`/`steps` fields without fabricating content chef never actually wrote. Pointing this script at a `chef:prep` session will fail with a clear error rather than guess.

If you want a week in mise., run `chef:plan` once per meal (so each has a real recipe), then publish each session — they'll land as separate collections until multi-recipe collections are wired up here.

**The printed link is a guess.** `{MISE_BASE_URL}/collections/{id}` follows the Next.js route mise.'s docs describe, but as of this writing mise.'s `src/app/` has no page route under that path yet — only the `/api/v1/*` ingest routes exist. The link may 404 until the phone view ships.

**Design-note deviation.** `docs/architecture.md`'s `chef:publish` notes propose storing the key as `mise.apiKey` in `~/.claude/chef/config.md` and falling back to a bare `POST /recipes` for single dishes. This skill instead reads the key from the environment (matches this repo's secret-handling convention, and `config.md` has no comparable env-var precedent) and always posts through `/collections`, because `POST /recipes` has no `grocery_items` field — going through `/collections` is the only way to keep `shopping.md` from being dropped, even for a single recipe.

## Notes

- Idempotent by design: re-running `chef:publish` on the same session produces the same `idempotency_key`, so mise. returns the existing collection instead of duplicating it.
- On success, the response is saved to `{session}/published.json` (collection id, duplicate flag, url, timestamp) so re-runs and `chef:print`-style tooling can find it later.
