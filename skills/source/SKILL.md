---
name: source
description: Research culinary inspiration from restaurants, food media, and chef profiles. Use when the user wants to cook something inspired by a specific restaurant, cuisine style, chef, or dish. Crawls menus and food content, then outputs an inspiration brief for chef:plan.
user_invocable: true
---

# Chef Source

Research culinary inspiration from the real world — restaurants, chefs, food media — and produce a structured brief that `chef:plan` can use as a creative starting point.

## Inputs

Accept any of:
- **Restaurant name + city**: "Joe Beef, Montreal" / "French Laundry, Napa"
- **Cuisine style**: "modern Japanese", "Québécois bistro", "Neapolitan pizza"
- **Chef name**: "Massimo Bottura", "Normand Laprise"
- **Dish name**: "classic duck confit", "pâté chinois elevated"
- **Vibe**: "something you'd find in a Paris brasserie on a Tuesday night"

## Workflow

```
1. WebSearch — find menus, reviews, press coverage, chef interviews
2. WebFetch — extract content from 2–4 high-signal pages
3. Synthesize → inspiration brief
4. Suggest: "pass this to chef:plan to build a meal around it"
```

## Step 1: WebSearch Strategy

Run 2–3 targeted searches:

```
1. "[restaurant/chef] menu [year]"
2. "[restaurant/chef] signature dishes recipe technique"
3. "[cuisine style] key ingredients techniques [region]"
```

Prioritize:
- Official restaurant websites (menu pages)
- Food media: Bon Appétit, Saveur, Food52, Ricardo Cuisine, Le Devoir (for Québécois)
- Chef interviews or books excerpts
- Award/recognition write-ups (Michelin, Gault&Millau, Canada's 100 Best)

Avoid: recipe aggregators (AllRecipes, Tasty) — too generic for this use case.

## Step 2: WebFetch

Fetch 2–4 pages from the search results. For each:
- Extract: dish names, key ingredients, techniques, flavor profiles, plating notes, seasonal philosophy
- Note: any quotes from the chef about their approach
- Flag: dishes marked as signatures or "must-try"

## Step 3: Inspiration Brief

Output a structured brief with these sections:

```markdown
# Inspiration Brief: [Subject]

## Identity
One paragraph: the restaurant/chef/cuisine's core identity, philosophy, and what makes it distinctive.

## Signature Dishes & Elements
- **[Dish name]**: key ingredients, technique, why it's notable
- **[Dish name]**: ...

## Flavor Profiles
- Dominant: [e.g. "umami-forward, deeply savory"]
- Accent: [e.g. "bright acid from yuzu, herbal freshness"]
- Texture play: [e.g. "crispy skin vs silky interior"]

## Key Techniques
- [Technique]: brief description and when it's used
- ...

## Pantry & Ingredient Signatures
What ingredients define this cooking style that you'd want to have on hand.

## Seasonal / Local Notes
Any emphasis on terroir, local sourcing, or seasonal rotation.

## Home Cook Adaptation Notes
What a home cook can realistically replicate, and what requires restaurant equipment or skill.

## Suggested Direction for chef:plan
One or two sentences suggesting how to turn this into a meal plan.
e.g. "Use this brief with chef:plan to build a 2-course dinner inspired by Joe Beef's approach to Quebec comfort food — think game, root vegetables, rich reductions."
```

## Notes

- If the subject is obscure and search returns little signal, say so clearly and offer adjacent alternatives
- For Québécois restaurants/cuisine, also check: ricardocuisine.com, ledevoir.com, lapresse.ca, iamhungry.ca
- Keep the brief usable: don't paste raw menu items — synthesize into actionable cooking direction
- Always end with the "Suggested Direction for chef:plan" section so the user knows next steps
