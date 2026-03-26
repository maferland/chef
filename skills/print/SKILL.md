---
name: print
description: Generate print-ready PDFs from a chef session — shopping list and day-of timeline. Use when the user wants to print their shopping list or timeline.
user_invocable: true
---

# Chef Print

Generate print-ready PDFs from a saved chef session using `scripts/print.sh`.

## Usage

```bash
bash skills/print/scripts/print.sh [session-path] [shopping|timeline|all]
```

- **session-path**: path to the session folder (e.g. `./sessions/2026-03-25-mexican-dinner-party/`). Omit to use the most recently modified session.
- **target**: `shopping`, `timeline`, or `all` (default: `all`)

## Workflow

1. Identify the session folder — use the argument or find the most recent `./sessions/*/`
2. Run the script:

```bash
bash skills/print/scripts/print.sh "./sessions/2026-03-25-mexican-dinner-party/" all
```

3. The script handles everything:
   - Parses `shopping.md` and `timeline.md` to clean HTML with print CSS
   - Runs Chrome headless to generate PDFs
   - Falls back to HTML + Cmd+P instructions if Chrome not found
   - Opens the generated files automatically

4. Report the output paths to the user

## What the script produces

- `shopping.pdf` — grocery list grouped by store, checkboxes, letter-size
- `timeline.pdf` — day-of run-of-show, prep-ahead items highlighted in amber

## Notes

- The script is at `skills/print/scripts/print.sh` relative to the plugin root
- Requires Python3 (always on macOS) for markdown → HTML conversion
- Chrome is at `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`
- PDFs open automatically after generation
