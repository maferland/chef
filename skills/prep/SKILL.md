---
name: prep
description: Plan a weekly meal prep session — batch cooking based on your config (prep_days, people, prep_extras). Factors in ingredients to use up, health goals, and this week's grocery deals. Use when the user wants to plan a Sunday meal prep or weekly food prep.
user_invocable: true
---

# Chef Prep

Plan a weekly meal prep session. Output: a meal plan, component reuse map, shopping list, timed prep timeline, and saved session files.

## Inputs

Accept any combination of:
- **Ingredients to use up**: "I have half a butternut squash, 2 chicken breasts, some kale"
- **Proteins/ingredients desired**: "want salmon this week", "plant-based this week"
- **Health override**: e.g. "lighter this week" (overrides config for this session)
- **Prep time available**: overrides config default

## Workflow

```
1. Read ~/.claude/chef/config.md → calculate portions, extract health_goals/dietary/stores
2. Run chef:grocery-check → get this week's deals (uses cache if fresh)
3. Plan meals
4. Output meal plan + component map + shopping list + prep timeline
5. Save session files
```

## Step 1: Read Config + Calculate Portions

Read `~/.claude/chef/config.md`. Extract:
- `people` — people eating each meal
- `prep_days` — days to prep for (default: 4)
- `prep_extras` — extra portions per meal beyond `people` (default: 0, e.g. 1 for packed next-day lunches)
- `health_goals` — weekly macro/diet target
- `dietary` — hard constraints (never violate)
- `preferred_stores` — passed to grocery-check
- `prep_time` — available prep session time (default: 2h30)

**Portion formula:**
```
portions_per_meal = people + prep_extras
total_portions    = prep_days × portions_per_meal
anchor_batch      = portions_per_meal × 2
```

Show the calculated targets at the top of your output:
```
Prep target: 4 days · 3 portions/meal (2 people + 1 packed lunch) · 12 total
Structure: 1 anchor ×6 + 2 lighter ×3
```

## Step 2: Grocery Check

Invoke `chef:grocery-check` (integrated mode — returns deals data, no formatted output).

Use deals to bias protein selection toward what's on sale. A 40%+ deal on a protein should strongly influence the anchor batch choice.

## Step 3: Plan Meals

**Constraint priority (when conflicts arise):**
1. `dietary` — hard, never violate
2. `health_goals` — hard for the week's balance, soft for a single meal
3. use-up ingredients — soft, use them unless they conflict with #1 or #2
4. grocery deals — nice-to-have, can be overridden

**Structure:**
- **Anchor batch** (`anchor_batch` portions) — highest effort, must reheat well. Braises, grain bowls, soups, roasted protein + veg.
- **Lighter recipes** — `portions_per_meal` each, faster, complement the anchor

**Health balance across the week:**
- Vary proteins (don't repeat the same protein every day)
- At least one plant-forward meal
- At least 3 distinct vegetables across the week
- Avoid carb stacking (pasta + rice + bread in same week)

**Format per proposed meal:**
```
1. **[Name]** — [portions] · [time] · reheats: [yes/well/poorly]
   Protein: X · Veg: Y, Z · Base: W
   On sale: [ingredient ↓XX%]  (if applicable)
   Uses up: [ingredient]  (if applicable)
```

Be opinionated — recommend the plan you'd pick and explain why.

## Step 4: Component Map

Every component listed MUST appear in ≥2 meals. If no genuine reuse exists for a recipe, note it as "standalone" — do not fabricate reuse.

```markdown
## Component Map

| Component | Prep once | Used in |
|---|---|---|
| Roasted sweet potato | 800g, 400°F (200°C) 25min | Meal 1 bowl + Meal 2 side |
| Quinoa | 300g dry | Meal 1 base + Meal 3 addition |
| Poached chicken | 600g | Meal 2 sliced + Meal 3 shredded |
```

## Step 5: Shopping List

Grouped by store (`preferred_stores`). Include all ingredients — mark accordingly:
- `(already have)` — from use-up input
- `(pantry check)` — common staples

## Step 6: Prep Session Timeline

Timed order for the prep session, using `prep_time` from config (default 2h30). Start longest tasks first; run independent tasks in parallel.

```markdown
## Prep Session (2h30)

**0:00** — Preheat oven to 400°F (200°C). Start braise (45 min unattended).
**0:10** — Prep + roast veg tray (25 min).
**0:15** — Cook grains (20 min).
...
**2:15** — Label + refrigerate. Note what freezes vs. fridge only.
```

## Step 7: Save Session Files

Save to `{sessionDir}/{YYYY-MM-DD}-prep/`:
- `plan.md` — meal plan + component map
- `shopping.md` — shopping list by store
- `timeline.md` — prep session order
- `metadata.md` — session context:

```markdown
---
date: YYYY-MM-DD
people: 2
prep_days: 4
prep_extras: 1
portions_per_meal: 3
total_portions: 12
health_goals: high_protein
dietary: none
prep_time: 2h30
deals_used:
  - "Chicken thighs Metro ↓43%"
ingredients_to_use_up:
  - "2 chicken breasts"
  - "kale (large bunch)"
---
```

## Health Goal Reference

| Config value | Practical meaning |
|---|---|
| `balanced` | Variety across proteins, veg, and grains — no single macro dominates. Aim for a different protein each day. |
| `high_protein` | At least one significant protein source per meal (meat, fish, eggs, legumes). Limit refined carbs as the main base. |
| `plant_forward` | Max 2 meat-based meals per week. Legumes, tofu, or tempeh in at least 2 meals. |
| `low_carb` | No grains as the main base. Max 1 starchy veg per week (sweet potato, squash). Prioritize protein + non-starchy veg. |
| `light` | Veg-heavy plates. Nothing fried or cream-heavy as the main event. Smaller anchor batches. |

## Common Mistakes

- Planning dishes that don't reheat well as the anchor (avoid crispy-main dishes)
- Repeating the same protein all week
- Not noting freeze vs. fridge for each component
- Inventing component reuse that doesn't exist — mark standalone recipes honestly
- Use-up ingredients overriding health goals or dietary constraints
