---
name: plan
description: Plan a meal — propose recipes based on context (occasion, time, season, skill level), let the user pick one, then output a full recipe with grouped ingredients and step-by-step instructions. Use when the user wants to cook something and needs ideas or a recipe.
user_invocable: true
---

# Chef Plan

Help the user decide what to cook and produce a complete recipe ready to execute.

## CRITICAL: Propose First, Never Ask

**NEVER ask clarifying questions before proposing.** Go straight to proposals every time.

Silently apply defaults for anything not provided:
- dietary: none
- people: 2
- skill_level: intermediate
- time: 45 minutes

State your defaults in ONE line at the top, then propose immediately. Example: "(No config — assuming 2 people, intermediate skill, no restrictions.)"

**Special case — "surprise me":** Skip the proposal list entirely. Go straight to the full recipe output (Step 4 + Step 5) for the dish you'd pick. Do not list options and ask which one.

## Inputs

Accept any combination of:
- **Occasion / context**: weeknight dinner, date night, dinner party, Sunday brunch, quick lunch, special occasion
- **Time available**: e.g. "30 minutes", "1 hour", "all afternoon"
- **Number of people** (overrides config)
- **Dietary override**: e.g. "one guest is vegan tonight"
- **Mood / craving**: e.g. "something comforting", "light and fresh", "I want to impress"
- **Ingredients to use up / pantry constraint**: e.g. "I have leftover chicken and leeks" or "I only have X, Y, Z"
- **Other dishes on the table**: e.g. "a friend is making birria" — calibrate portions and avoid overlap accordingly
- **Uncertain guest count**: e.g. "probably 6–8" — propose at the higher end, note the range
- **Source brief**: if a `chef:source` brief was produced earlier in the session, incorporate it as inspiration

## Workflow

```
1. Read ~/.claude/chef/config.md (if it exists) → use defaults for missing fields
2. Propose 3–5 recipes immediately
3. User picks (or says "surprise me" → Claude picks the best fit)
4. Output full recipe
5. Output drink pairing
6. Output shopping list
7. Save to event file
```

## Step 1: Read Config

Read `~/.claude/chef/config.md` if it exists. Use what's there. Fill gaps with defaults. Do not pause.

## Step 2: Propose Recipes

For each recipe, include:
- **Name** (in the language of the cuisine or bilingual)
- **Time**: total active + passive time
- **Difficulty**: beginner / intermediate / advanced (must match user's skill_level or be one step above at most)
- **Why it fits**: one sentence — season, occasion, mood, ingredients on hand
- **The key technique**: one thing the user will learn or practice

Format as a numbered list. Be opinionated — explain which one you'd recommend and why.

Example:
```
1. **Poulet rôti aux herbes** — 1h15 (20min active) · Intermediate
   Simple classic. Fits a Sunday dinner and uses up thyme from the garden.
   Technique: dry-brining overnight for crispier skin.
   → Recommended: best effort-to-wow ratio for 2 people.

2. **Pasta cacio e pepe** — 25min · Intermediate
   ...
```

## Step 3: User Picks

- If user says "surprise me" or gives no preference: pick the one you recommended
- If user picks by number, name, or partial description: confirm it

## Step 4: Full Recipe Output

### Header
```
# [Recipe Name]
[Cuisine] · [Total time] · [Difficulty] · Serves [N]
```

### Ingredients

Group by category. Use metric for most measurements (mL, g), with practical equivalents when helpful (e.g. "250 mL (1 cup)").

```markdown
## Ingredients

**Produce**
- 1 whole chicken (~1.5 kg)
- 4 cloves garlic
- 1 lemon

**Pantry**
- 30 mL (2 tbsp) olive oil
- Salt, freshly ground black pepper

**Herbs & Spices**
- 5–6 sprigs fresh thyme
- 2 sprigs rosemary
```

Categories to use (only include non-empty ones):
- Produce
- Protein (meat, fish, eggs)
- Dairy
- Pantry (oils, vinegars, canned goods, grains, pasta)
- Herbs & Spices
- Wine & Spirits (flag if from SAQ when in preferred_stores)
- Other

### Instructions

Number each step. Include:
- Timing cues ("after 5 minutes...", "until golden, ~8 min")
- **Always include both °C and °F for all temperatures.** Ordering follows `oven_temp_unit` in config (default: Fahrenheit first for oven temps). Examples: `400°F (200°C)` for oven, `135°F (57°C)` for internal doneness
- Visual/sensory cues ("until the butter smells nutty", "the skin should pull away easily")
- When to rest, cool, or wait

### Tips

2–4 bullet points covering:
- The #1 mistake to avoid
- A make-ahead shortcut if applicable
- A substitution for hard-to-find ingredients

## Step 5: Drink Pairing

After Tips, always include a drink pairing section. Match the drink style to the occasion — junk food night gets beer or cocktail as primary, fine dining gets wine.

```markdown
## Drink Pairing

🍷 **Primary**: [Name] — [one sentence why] *(SAQ ~$XX if applicable)*
🍺 **Alt**: [Name] — [different angle]
🥤 **Non-alc**: [Name] — [why it works]
```

- Be specific (e.g. "Côtes du Rhône rouge", not "a red wine")
- SAQ price only if `preferred_stores` includes SAQ
- Non-alc is always required

## Step 6: In-chat summary

Output a brief summary in chat: the dish name, total time, and that 3 files have been saved (see Step 7). Do not re-print the full recipe in chat after saving.

## Step 7: Save 3 Files

Save 3 separate files to `{sessionDir}/{YYYY-MM-DD}-{slug}/` where `sessionDir` is:
- The value of `sessionDir` if provided in the test/session context (e.g. `/tmp/chef-tests`)
- Otherwise `./sessions` in the **current working directory**

`slug` = short kebab-case event name (e.g. `mexican-dinner-party`, `date-night-italian`). `sessions/` is in `.gitignore`.

---

### `plan.md` — Full recipe reference

Event header (date, guests, context) + menu table + recipe (ingredients, instructions, tips) + drink pairing.
Do NOT include the timeline or shopping list — those are separate files.

---

### `timeline.md` — Day-of run-of-show

Checkbox format. **Prep-ahead items must be visually distinct** — put them in a clearly labelled block at the top with a note on why they benefit from being done early.

```markdown
# Day-of Timeline — [Event]
**Date:** … · **Guests:** …

---

## ⭐ Prep Ahead
*Do these before the day — all improve with time.*

- [ ] **[Task]** — [why it's better made ahead, e.g. "mole deepens overnight"]
- [ ] **[Task]** — [e.g. "score + salt duck overnight = crispier skin"]

---

## Day of

### [X]h before guests
- [ ] [Task]

### [X] min before eating
- [ ] [Task]

### During dinner
- [ ] [Task]

### Dessert
- [ ] [Task]
```

---

### `shopping.md` — Grocery list by store

Group items by **store**, not category — one trip per section. Include **everything** in the recipe, including pantry staples (salt, pepper, olive oil, etc.) — mark common staples with `*(pantry check)*` so the user can verify quickly without skipping them entirely. Note any items that need ordering ahead.

```markdown
# Shopping List — [Event]
**Date:** … · **Guests:** …

---

## Order Ahead
- [ ] [item] — [where to order]

## [Store Name]
- [ ] [item] [quantity] *(any note)*

## [Store Name]
- [ ] [item]

## SAQ
- [ ] [wine/spirit] ×[N bottles] (~$XX) — [brief note]
```

---

Confirm all 3 save paths to the user at the end.

## Contextual Rules

### Collaborative dinners
When other dishes are specified ("a friend is making birria", "we're also having X"):
- Explicitly note the contrast your dish provides
- Calibrate quantities relative to the full table — with multiple mains, individual portions are smaller
- Never propose a dish that duplicates the protein, technique, or flavor profile of another confirmed dish

### Seasonal ingredients
When a key ingredient is out of season or potentially unavailable, proactively flag it and offer the best substitute — do not wait to be asked. Examples:
- Fresh corn in winter → frozen (pat dry, small batches)
- Fresh tomatoes in winter → San Marzano canned for sauces, cherry tomatoes for salads
- Stone fruit out of season → note it, suggest alternative

### Specialty / hard-to-source ingredients
For any ingredient that may be hard to find (specialty chiles, specific cuts, imported items), automatically include a tiered fallback in the Tips section:
- Option A: ideal (all ingredients available)
- Option B: 2 most common substitutes
- Option C: widely available fallback

### Plating (dinner party occasions)
For dinner parties, date nights, or any "impress" occasion, include a brief plating note after the instructions:
- How to plate individually vs family-style
- One technique detail (smear vs pool, off-center vs centered, garnish placement)
- What the dish should look like when it lands on the table

## Common Mistakes to Avoid

- Proposing recipes far above the user's skill level
- Giving vague timings ("cook until done") — always add visual/sensory cues
- Forgetting to note passive time (resting, marinating, chilling)
- Using cup/oz when the user is in Canada — prefer metric + practical equivalent
- Writing temperatures in only one unit — always pair °F and °C
- Omitting the shopping list
- **Pantry constraint**: if the user says "I only have X, Y, Z", for each proposed recipe mentally walk through every ingredient it needs and check it against the provided list. For any ingredient NOT on the list (other than salt, pepper, and water which are always assumed), flag it inline — e.g. "⚠️ needs breadcrumbs — do you have any?" Do not claim a recipe is "100% pantry" without actually verifying ingredient by ingredient.
