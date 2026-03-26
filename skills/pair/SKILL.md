---
name: pair
description: Suggest drink pairings for a dish — wine, beer, cocktails, and non-alcoholic. Context-aware (junk food night gets beer/cocktail, fine dining gets wine). Use when the user asks what to drink with a dish, or call it after chef:plan for a full pairing.
user_invocable: true
---

# Chef Pair

Suggest drink pairings for a dish or meal. Cover all categories: wine, beer, cocktails, and non-alcoholic. Be context-aware — match the drink style to the occasion and food profile, not just default to wine.

## Inputs

Accept any of:
- **Dish name + description**: "duck breast with mole negro"
- **Cuisine + context**: "Mexican dinner party", "fancy junk food night"
- **Just "pair"** with no args: use the recipe or dish discussed most recently in the session
- **Dietary/preference constraints**: "no wine", "non-alcoholic only", "beer preferred"

## Workflow

1. Identify the dish and its key flavor profile: richness, acidity, spice, fat content, smoke, sweetness
2. Consider the occasion: formal dinner, casual junk food night, brunch, etc.
3. Output pairings in the structure below

## Output Format

```markdown
## Drink Pairing

🍷 **[Category]**: [Name] — [one-line reason why it works] *(SAQ ~$XX)* ← if wine and SAQ in config
🍺 **Alt**: [Name] — [why, different angle from primary]
🥤 **Non-alc**: [Name] — [why]
```

Categories for the primary: Wine / Cocktail / Beer / Spirits — pick whatever fits best for the occasion.

### Examples by context

**Fine dining (duck + mole):**
```
🍷 Primary: Côtes du Rhône rouge — earthy, peppery, holds up to the mole's depth (SAQ ~$22)
🍺 Alt: Modelo Negra — lighter, the mild bitterness cuts the richness
🥤 Non-alc: Hibiscus agua fresca — floral, acidic, echoes the chili
```

**Fancy junk food (smash burger):**
```
🍺 Primary: Craft lager or pilsner — crisp, cuts grease, never competes
🍸 Alt: Dirty martini — salty, cold, weirdly perfect with a burger
🥤 Non-alc: Egg cream or house-made cola — leans into the diner energy
```

**Brunch (eggs, lemon, herbs):**
```
🍷 Primary: Grüner Veltliner — herbaceous, zippy, echoes the lemon
🍹 Alt: Aperol Spritz — bitter, low-ABV, classic brunch energy
🥤 Non-alc: Sparkling water + elderflower cordial
```

## Rules

- **Match occasion first**: junk food night → beer or cocktail as primary, not wine
- **Be specific**: "red Burgundy" not "red wine"; "Modelo Negra" not "a dark beer"
- **One sentence per pairing** — explain WHY it works (flavor bridge, contrast, cut the fat, echo the spice, etc.)
- **SAQ note**: if wine is recommended AND `preferred_stores` in config includes SAQ, add approximate SAQ price range
- **Non-alc is always included** — never skip it. When all pairings must be non-alc, the three options must span genuinely different categories (e.g. one tea-based, one juice/shrub/fermented, one sparkling) — do NOT give three variations of sparkling water
- **Budget signal**: if the recipe is budget-friendly, keep pairings accessible; if it's a fancy occasion, go a tier up
- Never recommend the same style twice (primary and alt must be meaningfully different)
