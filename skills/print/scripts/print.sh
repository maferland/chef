#!/usr/bin/env bash
# chef:print — generate print-ready PDFs from a chef session
#
# Usage:
#   print.sh [session-path] [shopping|timeline|all]
#
# Args:
#   session-path  path to session folder (default: most recent ./sessions/*/)
#   target        which files to print (default: all)
#
# Requires: Python3 (always available on macOS), Chrome (for PDF)
# Fallback: generates HTML if Chrome not found — open in browser → Cmd+P

set -euo pipefail

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SESSION_PATH="${1:-}"
TARGET="${2:-all}"

# ── Find session ────────────────────────────────────────────────────────────

if [ -z "$SESSION_PATH" ]; then
  SESSION_PATH=$(ls -td ./sessions/*/ 2>/dev/null | head -1 || true)
  if [ -z "$SESSION_PATH" ]; then
    echo "Error: No sessions/ folder found in current directory."
    echo "Run /chef:plan first to generate a session."
    exit 1
  fi
  echo "Using most recent session: $SESSION_PATH"
fi

if [ ! -d "$SESSION_PATH" ]; then
  echo "Error: Session folder not found: $SESSION_PATH"
  exit 1
fi

# ── Determine target files ──────────────────────────────────────────────────

FILES=()
case "$TARGET" in
  all)      FILES=("plan" "shopping" "timeline") ;;
  shopping) FILES=("shopping") ;;
  timeline) FILES=("timeline") ;;
  plan)     FILES=("plan") ;;
  *)        echo "Unknown target '$TARGET'. Use: plan, shopping, timeline, or all"; exit 1 ;;
esac

# ── Markdown → HTML converter ───────────────────────────────────────────────

convert_md_to_html() {
  local input="$1"
  local output="$2"

  python3 - "$input" "$output" << 'PYEOF'
import sys
import re
import html as html_lib

src = open(sys.argv[1]).read()

CSS = """
@page { size: letter; margin: 2cm; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 13px; line-height: 1.6; color: #1a1a1a; max-width: 100%;
}
h1 {
  font-size: 20px; margin-bottom: 4px;
  border-bottom: 2px solid #1a1a1a; padding-bottom: 6px;
}
h2 { font-size: 15px; margin-top: 20px; margin-bottom: 6px; color: #333; }
h3 { font-size: 13px; margin-top: 14px; margin-bottom: 4px; color: #555; }
p.meta { color: #666; font-size: 12px; margin-bottom: 16px; margin-top: 0; }
ul { padding-left: 0; list-style: none; margin: 4px 0; }
li { padding: 3px 0; display: flex; align-items: flex-start; gap: 8px; }
li::before { content: "☐"; font-size: 14px; flex-shrink: 0; margin-top: 1px; }
hr { border: none; border-top: 1px solid #ddd; margin: 16px 0; }
.prep-ahead {
  background: #fffbea; border-left: 4px solid #f59e0b;
  padding: 10px 14px; margin: 12px 0; border-radius: 0 4px 4px 0;
}
.prep-ahead h2 { color: #92400e; margin-top: 0; }
.prep-ahead li::before { content: "⭐"; }
em { font-style: italic; color: #666; }
strong { font-weight: 600; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 12px; }
th { background: #f5f5f5; font-weight: 600; text-align: left; padding: 6px 10px; border: 1px solid #ddd; }
td { padding: 5px 10px; border: 1px solid #ddd; vertical-align: top; }
tr:nth-child(even) { background: #fafafa; }
@media print {
  body { font-size: 12px; }
  h2 { page-break-after: avoid; }
  li { page-break-inside: avoid; }
}
"""

SEPARATOR_RE = re.compile(r'^\|\s*[-:]+[-| :]*\|$')

def md_inline(text):
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(?!\*)(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    return text

def is_table_row(line):
    s = line.strip()
    return s.startswith('|') and s.endswith('|')

def is_separator_row(line):
    return bool(SEPARATOR_RE.match(line.strip()))

lines = src.split('\n')
body_parts = []
i = 0
in_prep_ahead = False
in_ul = False

def close_ul():
    global in_ul
    if in_ul:
        body_parts.append('</ul>')
        in_ul = False

def open_ul():
    global in_ul
    if not in_ul:
        body_parts.append('<ul>')
        in_ul = True

META_RE = re.compile(r'^\*\*\s*(Date|Guests?):', re.IGNORECASE)

while i < len(lines):
    line = lines[i]

    if is_table_row(line):
        close_ul()
        table_lines = []
        while i < len(lines) and is_table_row(lines[i]):
            table_lines.append(lines[i])
            i += 1
        html_table = ['<table>']
        header_done = False
        for tline in table_lines:
            if is_separator_row(tline):
                continue
            cells = [c.strip() for c in tline.strip().strip('|').split('|')]
            tag = 'th' if not header_done else 'td'
            header_done = True
            html_table.append('<tr>' + ''.join(f'<{tag}>{md_inline(html_lib.escape(c))}</{tag}>' for c in cells) + '</tr>')
        html_table.append('</table>')
        body_parts.append('\n'.join(html_table))
        continue

    if line.startswith('# '):
        close_ul()
        body_parts.append(f'<h1>{md_inline(html_lib.escape(line[2:]))}</h1>')
        i += 1
        continue

    if line.startswith('## '):
        close_ul()
        raw = line[3:]
        is_prep = '⭐' in raw or 'Prep Ahead' in raw or 'Day Before' in raw
        if in_prep_ahead and not is_prep:
            body_parts.append('</div>')
            in_prep_ahead = False
        if is_prep and not in_prep_ahead:
            body_parts.append('<div class="prep-ahead">')
            in_prep_ahead = True
        body_parts.append(f'<h2>{md_inline(html_lib.escape(raw))}</h2>')
        i += 1
        continue

    if line.startswith('### '):
        close_ul()
        body_parts.append(f'<h3>{md_inline(html_lib.escape(line[4:]))}</h3>')
        i += 1
        continue

    if line.strip() == '---':
        close_ul()
        if in_prep_ahead:
            body_parts.append('</div>')
            in_prep_ahead = False
        body_parts.append('<hr>')
        i += 1
        continue

    if line.startswith('- '):
        open_ul()
        raw = re.sub(r'^\[[ x]\] ', '', line[2:])
        body_parts.append(f'<li>{md_inline(html_lib.escape(raw))}</li>')
        i += 1
        continue

    if META_RE.match(line):
        close_ul()
        body_parts.append(f'<p class="meta">{md_inline(html_lib.escape(line))}</p>')
        i += 1
        continue

    if line.strip():
        close_ul()
        body_parts.append(f'<p>{md_inline(html_lib.escape(line))}</p>')
        i += 1
        continue

    close_ul()
    i += 1

close_ul()
if in_prep_ahead:
    body_parts.append('</div>')

html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>{CSS}</style>
</head>
<body>
{''.join(body_parts)}
</body>
</html>"""

with open(sys.argv[2], 'w') as out:
    out.write(html)
print(f"  HTML generated: {sys.argv[2]}")
PYEOF
}

# ── Process each file ────────────────────────────────────────────────────────

GENERATED=()
SESSION_ABS="$(cd "$SESSION_PATH" && pwd)"

for FILE in "${FILES[@]}"; do
  MD="${SESSION_ABS}/${FILE}.md"
  HTML="${SESSION_ABS}/${FILE}.html"

  if [ ! -f "$MD" ]; then
    echo "⚠️  ${FILE}.md not found in $SESSION_PATH — skipping"
    continue
  fi

  echo "Processing ${FILE}.md..."
  convert_md_to_html "$MD" "$HTML"

  if [ -f "$CHROME" ]; then
    PDF_ABS="${SESSION_ABS}/${FILE}.pdf"
    HTML_ABS="$(realpath "$HTML")"
    "$CHROME" \
      --headless=new \
      --no-sandbox \
      --disable-gpu \
      --print-to-pdf="$PDF_ABS" \
      --no-pdf-header-footer \
      --print-to-pdf-no-header \
      "file://$HTML_ABS" 2>/dev/null
    rm -f "$HTML"
    echo "  ✓ PDF saved: $PDF_ABS"
    GENERATED+=("$PDF_ABS")
  else
    echo "  ✓ HTML saved: $HTML"
    echo "    (Chrome not found — open in browser and press Cmd+P → Save as PDF)"
    GENERATED+=("$HTML")
  fi
done

# ── Summary ──────────────────────────────────────────────────────────────────

echo ""
COUNT=${#GENERATED[@]}
echo "Done. Generated $COUNT file(s):"
if [ "$COUNT" -gt 0 ]; then
  for f in "${GENERATED[@]}"; do
    echo "  $f"
  done
  # Open generated files
  for f in "${GENERATED[@]}"; do
    open "$f" 2>/dev/null || true
  done
else
  echo "  (nothing generated — check that shopping.md and timeline.md exist in the session folder)"
fi
