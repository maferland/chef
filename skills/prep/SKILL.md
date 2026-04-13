---
name: prep
description: Plan a weekly meal prep session — batch cooking for 4 days, 3 portions per day. Factors in ingredients to use up, health goals, and this week's grocery deals. Use when the user wants to plan a Sunday meal prep or weekly food prep.
user_invocable: true
---

# Chef Prep

Plan a weekly meal prep session. Output: a set of recipes that cover 4 days × 3 portions, a component plan (cook once, use twice), a combined shopping list, and a timed prep session order.

## Inputs

Accept any combination of:
- **Ingredients to use up**: "I have half a butternut squash, 2 chicken breasts, some kale"
- **Proteins/ingredients desired**: "want salmon this week", "plant-based this week"
- **Health override**: e.g. "lighter this week" (overrides config)
- **Prep time available**: default 2–3 hours

## Workflow

```
1. Read ~/.claude/chef/config.md → extract health_goals, dietary, people, preferred_stores
2. Run chef:grocery-check → get this week's deals (uses cache if fresh)
3. Plan meals
4. Output meal plan + component map + shopping list + prep session timeline
5. Save to ./sessions/{YYYY-MM-DD}-prep/
```

## Step 1: Read Config

Read `~/.claude/chef/config.md`. Key fields for prep:
- `health_goals` — drives macro balance of the week
- `dietary` — hard constraints
- `people` — portions per meal (prep targets 3 portions per person per day, 4 days)
- `preferred_stores` — passed to grocery-check

**Health goal defaults if not set:**
- Lots of vegetables (at least half the plate)
- One lean protein per meal
- Limit refined carbs — prefer whole grains, legumes, root vegetables

## Step 2: Grocery Check

Invoke `chef:grocery-check` (integrated mode — returns deals, no formatted output).

Use deals to bias protein selection: if chicken thighs are 40% off, lean toward chicken as the batch protein.

## Step 3: Plan Meals

**Target: 12 portions over 4 days (3 per day)**

Structure:
- **1 large batch** (6 portions) — the anchor dish, highest effort, reheats well. Braises, grain bowls, soups, roasted protein + veg all work.
- **1–2 smaller recipes** (3 portions each) — lighter, faster, complement the batch

**Component strategy:** look for shared components across meals. Examples:
- Roast a full tray of veg once → use in 2 different meals
- Make one grain base → serve differently each time
- Poach or roast a protein → slice differently for two contexts

**Health balance across the week:**
- Vary proteins (fish, poultry, legume — don't repeat the same protein 4 days)
- At least one plant-forward meal
- Include at least 3 distinct vegetables across the week
- Avoid heavy carb-on-carb (pasta + bread + rice all in one week)

**Format for each proposed meal:**
```
1. **[Name]** — [portions] · [time to make] · reheats: [yes/no/notes]
   Protein: X · Veg: Y, Z · Grain/base: W
   On sale this week: [ingredient] ↓XX%
   Uses up: [ingredient from fridge]
```

Be opinionated — recommend the plan you'd make and explain why.

## Step 4: Component Map

After the meal plan, output a component map showing shared prep:

```markdown
## Component Map

| Component | Prep once | Used in |
|---|---|---|
| Roasted sweet potato | 800g, 400°F 25min | Meal 1 bowl + Meal 2 side |
| Quinoa | 300g dry | Meal 1 base + lunch addition |
| Poached chicken | 600g | Meal 2 sliced + Meal 3 shredded |
```

## Step 5: Shopping List

Combined list for the whole week, grouped by store (from `preferred_stores`). Mark items already on hand (from "use up" input) as "(already have)". Include all ingredients including staples — mark common ones as "(pantry check)".

## Step 6: Prep Session Timeline

A timed order of operations for the prep session (default 2.5h). Start with what takes longest, run things in parallel where possible.

```markdown
## Prep Session (2h30)

**0:00** — Preheat oven to 400°F (200°C). Start braise on stovetop (45 min unattended).
**0:10** — Prep and roast veg tray (25 min).
**0:15** — Cook grains (20 min).
**0:35** — Veg out of oven. While cooling, prep meal 2 components.
**1:00** — Braise check. Assemble grain bowls, portion into containers.
...
**2:15** — Label and refrigerate. Note what freezes well.
```

## Step 7: Save Files

Save to `{sessionDir}/{YYYY-MM-DD}-prep/`:
- `plan.md` — full meal plan + component map + notes
- `shopping.md` — shopping list by store
- `timeline.md` — prep session order

## Health Goal Reference

| Config value | Meaning |
|---|---|
| `balanced` | Even macros, variety-first |
| `high_protein` | 30g+ protein per meal, lean cuts |
| `plant_forward` | Mostly plant protein (legumes, tofu, tempeh), meat max 2×/week |
| `low_carb` | Limit grains/starchy veg, prioritize protein + non-starchy veg |
| `light` | Lower calorie density, lots of veg, smaller portions |

## Common Mistakes

- Planning meals that don't reheat well (avoid dishes with crispy textures as the main event)
- Repeating the same protein 4 days — vary it
- Forgetting to note freeze vs. fridge for each component
- Shopping list that doesn't account for what's already on hand
