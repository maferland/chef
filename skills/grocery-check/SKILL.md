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

### IGA — grid view has real sale prices

```
URL: https://www.iga.net/fr/circulaire?view=list
(or navigate to /fr/circulaire, dismiss tour, click second tab)

1. browser_navigate → https://www.iga.net/fr/circulaire?view=list
2. browser_wait_for (time: 4)
3. Accept cookies if dialog appears ("Tout accepter")
4. Dismiss tour modal if present ("Sauter" / "Fermer")
5. browser_snapshot → extract deals

Two item types in grid:

a) SALE items — identified by ÉCONOMISEZ marker:
   Pattern: generic: SALE_PRICE $ → generic: WAS_PRICE $ → ÉCONOMISEZ → generic: SAVINGS $
   Extract sale price, compute % = (1 - sale/was) × 100

b) Scene+ bonus items — identified by +TPS +TVQ after price:
   Pattern: generic: PRICE $ → paragraph: +TPS +TVQ → Achetez N et obtenez X PTS
   Extract: product + price + bonus points offer

Note: page lazy-loads ~20 items. Scroll or accept partial results.
In output, separate real discounts (ÉCONOMISEZ) from Scene+ bonus items.
```

### Stores without text-extractable flyers

If a store isn't listed above, skip it and note: "flyer not text-accessible for [store]".

---

## Extraction Rules

- **Food items only**: protein, produce, dairy, pantry staples — skip cleaning products, personal care, beer/wine unless in preferred_stores config
- **Flag exceptional deals**: >40% off shown prominently
- **IGA**: distinguish ÉCONOMISEZ (real discount) from Scene+ bonus items (regular price + points)
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

### IGA
- **McCain Superfries 650g** — $2.99 ↓50% (was $5.99)
- Tostitos 525g — $6.99 *(+250 pts Scene+)*
```

**Integrated mode** (called by `chef:prep`): return deals data directly, skip formatted output.

**Standalone with `force-refresh`**: bypass cache, re-scrape all stores.
