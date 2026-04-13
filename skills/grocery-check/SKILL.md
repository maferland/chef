---
name: grocery-check
description: Check this week's grocery deals from local stores using Playwright. Navigates each store's online flyer, extracts deals via accessibility tree (no OCR needed), caches to deals.md until Wednesday. Use before chef:prep or standalone.
user_invocable: true
---

# Chef Grocery Check

Navigate each store's online flyer page with Playwright, extract deals from the accessibility tree (text — no screenshots, no OCR), cache to `~/.claude/chef/flyer-cache/deals.md` until Wednesday.

## Cache Logic

Cache file: `~/.claude/chef/flyer-cache/deals.md`

**Format:**
```markdown
---
fetched_at: 2026-04-12T10:00:00
expires_at: 2026-04-16T23:59:59
---

## Metro
- **Couronne de brocoli** — $1.99 (was $3.99) ↓50%
- Filets de porc — $4.99 (was $6.99) ↓28%

## Super C
- **Filets d'aiglefin panés** — $11.99 (was $19.99) ↓40%
```

**Before scraping, always check cache:**
1. Read `~/.claude/chef/flyer-cache/deals.md`
2. If `expires_at` is in the future → return cached deals, skip Playwright
3. If missing or expired → scrape, write cache, return fresh deals

**`force-refresh` argument**: bypass cache and re-scrape.

**Expiry algorithm (Quebec flyers run Thu→Wed):**
```python
from datetime import datetime, timedelta
today = datetime.now()
days_until_wed = (2 - today.weekday()) % 7
if days_until_wed == 0:
    days_until_wed = 7  # today is Wed — expires end of tonight
expires = (today + timedelta(days=days_until_wed)).replace(hour=23, minute=59, second=59)
```

---

## Scraping Workflow

For each store in `preferred_stores`, navigate and extract using the store-specific pattern below. Always wait 5 seconds after navigation for JS to render.

### Metro

```
URL: https://www.metro.ca/fr/epicerie-en-ligne/circulaire?sortOrder=relevance&filter=%3Arelevance%3Aoption%3Asuggestion-for-you

1. browser_navigate → URL
2. If cookie consent dialog appears → click "Accept All"
3. browser_wait_for (time: 5)
4. browser_snapshot → extract deals

Pattern in snapshot:
  link "PRODUCT NAME" → /url: /fr/epicerie-en-ligne/allees/...
    → Prix régulier → text: REGULAR_PRICE
    → generic: SALE_PRICE

Discount = (1 - sale/regular) × 100
```

### Super C

```
URL: https://www.superc.ca/fr/epicerie-en-ligne/circulaire?sortOrder=relevance&filter=%3Arelevance%3Aoption%3Asuggestion-for-you

1. browser_navigate → URL
2. browser_wait_for (time: 5)
3. browser_snapshot → extract deals

Pattern in snapshot:
  link "PRODUCT NAME SIZE" → /url: /allees/...   ← note: /allees/ not /fr/epicerie-en-ligne/allees/
    → Prix régulier → text: REGULAR_PRICE
    → generic: SALE_PRICE
```

### Maxi

```
URL: https://www.maxi.ca/fr/deals/flyer

1. browser_navigate → URL
2. browser_wait_for (time: 5)
3. Dismiss location/store dialog if present
4. browser_snapshot → extract deals

Pattern in snapshot (English labels):
  generic: "sale" → text: $SALE_PRICE
  generic: "was"  → text: $WAS_PRICE
  paragraph: BRAND_NAME
  heading (level=3): PRODUCT_NAME

Note: lazy-loads ~20 items on first view. Accept partial results or scroll for more.
```

### IGA

```
URL: https://www.iga.net/fr/offres

1. browser_navigate → URL
2. browser_wait_for (time: 4)
3. Accept cookies if dialog present
4. Dismiss tour modal if appears (click "Sauter")
5. Click "Plus d'offres" tab
6. browser_wait_for (time: 2)
7. browser_snapshot → extract deals

Pattern in snapshot:
  generic: PRICE ($X,XX $)  → +TPS +TVQ line nearby
  paragraph → cursor=pointer: PRODUCT_NAME

Note: IGA's "Plus d'offres" shows Scene+ loyalty bonus deals — product is at regular price
but you earn bonus points. This is different from Metro/Super C sale prices.
Flag IGA deals as "Scene+ offer" not "% off regular price".
```

### Stores without text-extractable flyers

If a store isn't listed above, skip it and note: "flyer not text-accessible for [store]".

---

## Extraction Rules

- **Food items only**: protein, produce, dairy, pantry staples — skip cleaning products, personal care, beer/wine unless in preferred_stores config
- **Flag exceptional deals**: >40% off shown prominently
- **IGA caveat**: note these are Scene+ bonus offers, not price reductions
- **Failures**: if a store fails or returns no deals, skip and note — don't block the run

---

## Output

**Standalone mode** (`/chef:grocery-check`):

```markdown
## This Week's Deals
*Fetched Apr 12 · expires Wed Apr 16*

### Metro
- **Couronne de brocoli** — $1.99 (was $3.99) ↓50%
- Filets de porc — $4.99 (was $6.99) ↓28%
- Concombre anglais — $1.99 (was $2.99) ↓33%

### Super C
- **Filets d'aiglefin** — $11.99 (was $19.99) ↓40%
- Poulet BBQ — $4.99 (was $6.49) ↓23%

### IGA *(Scene+ offers — bonus points, not discounted prices)*
- Tostitos 525g — $6.99 (+500 pts)
```

**Integrated mode** (called by `chef:prep`): return deals data directly, skip formatted output.

**Standalone with `force-refresh`**: bypass cache, re-scrape all stores.
