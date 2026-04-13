---
name: grocery-check
description: Check this week's grocery deals from local stores. Scrapes digital flyers via Playwright and caches results until the flyer expires (Quebec flyers run Thu–Wed). Use before chef:prep or standalone to see what's on sale.
user_invocable: true
---

# Chef Grocery Check

Fetch this week's deals from the user's preferred stores. Cache results so Playwright only runs once per flyer cycle.

## Cache Logic

Cache file: `~/.claude/chef/flyer-cache.json`

Format:
```json
{
  "fetched_at": "2026-04-12T10:00:00",
  "expires_at": "2026-04-16T23:59:59",
  "stores": {
    "Metro": [
      { "item": "chicken thighs", "regular": "$6.99/kg", "sale": "$3.99/kg", "note": "limit 2" },
      { "item": "salmon fillet", "regular": "$24.99/kg", "sale": "$16.99/kg" }
    ],
    "IGA": [...]
  }
}
```

**Before scraping, always check the cache:**
1. Read `~/.claude/chef/flyer-cache.json`
2. If it exists AND `expires_at` is in the future → return cached deals, skip Playwright
3. If missing or expired → scrape, update cache, return fresh deals

**Expiry calculation:** Quebec flyers run Thursday to Wednesday. Set `expires_at` to the next Wednesday at 23:59:59 (if today is Wednesday, expires tonight):
```python
from datetime import datetime, timedelta
today = datetime.now()
# Wednesday = weekday 2 (Mon=0 … Sun=6)
days_until_wed = (2 - today.weekday()) % 7
if days_until_wed == 0:
    days_until_wed = 7  # today is Wednesday — already the last day, expires tonight
expires = (today + timedelta(days=days_until_wed)).replace(hour=23, minute=59, second=59)
```

## Scraping Workflow (when cache is stale)

Use Playwright MCP. Scrape each store in `preferred_stores` from config. Focus on protein, produce, and dairy — skip cleaning products, personal care, etc.

### Store URLs

| Store | Flyer URL |
|---|---|
| Metro | `https://www.metro.ca/fr/circulaire` |
| IGA | `https://www.iga.net/fr/circulaire` |
| Maxi | `https://www.maxi.ca/fr/circulaire` |
| Provigo | `https://www.provigo.ca/fr/circulaire` |
| Super C | `https://www.superc.ca/fr/circulaire` |

### Per-store flow
```
1. browser_navigate → flyer URL
2. browser_snapshot → read the visual layout (flyer sites vary by store; use visual parsing)
3. Look for deal cards: each card typically has a product name, sale price, and regular/was price
4. If cards aren't obvious from snapshot, take a screenshot and extract visually
5. Extract: item name, regular price, sale price, any quantity limits
6. Filter to food items only (protein, produce, dairy, pantry staples)
7. browser_close
```

Flyer sites are JS-rendered — use Playwright, not WebFetch. DOM structure varies across stores; rely on visual/snapshot parsing rather than fixed CSS selectors. If a store's layout changes, fall back to a screenshot and extract what's visible.

If a store's flyer fails to load, skip it and note the failure. Don't block the whole run.

## Output Format

Always show:
- Cache status: "Using cached deals (expires Wed Apr 16)" or "Fetched fresh deals"
- Deals grouped by store, sorted by % discount descending
- Flag exceptional deals (>40% off) prominently

```markdown
## This Week's Deals
*Cached — expires Wed Apr 16*

### Metro
- **Chicken thighs** — $3.99/kg (was $6.99) ↓43%
- Salmon fillet — $16.99/kg (was $24.99) ↓32%

### IGA
- **Ground beef (lean)** — $5.99/kg (was $9.99) ↓40%
```

## Standalone vs. Integrated

- **Standalone** (`/chef:grocery-check`): show deals and stop
- **Standalone with force-refresh** (`/chef:grocery-check force-refresh`): bypass cache, re-scrape all stores
- **Called by `chef:prep`**: return deals dict for meal planning — skip the formatted output, just pass data
