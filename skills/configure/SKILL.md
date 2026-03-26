---
name: configure
description: Set up chef preferences — location, dietary restrictions, number of people, cuisine preferences, skill level, and preferred grocery stores. Use when user wants to configure chef or set their cooking profile.
user_invocable: true
---

# Chef Configure

Set up the user's cooking profile, saved to `~/.claude/chef/config.md`. Create the file if it doesn't exist; update fields if it does.

## Fields to Configure

Walk through each field interactively, showing the current value if one exists:

| Field | Description | Example |
|---|---|---|
| `location` | City + province/country | `Montreal, QC` |
| `preferred_stores` | Grocery stores nearby | `IGA Plateau, Metro Jean-Talon, SAQ` |
| `dietary` | Restrictions or preferences | `none`, `vegetarian`, `no nuts, gluten-free` |
| `people` | Default number of people to cook for | `2` |
| `cuisine_preference` | Favourite cuisines | `French, Italian, Japanese` |
| `skill_level` | Cooking confidence | `beginner`, `intermediate`, `advanced` |
| `oven_temp_unit` | Preferred unit for oven temps | `fahrenheit` (default), `celsius` |

## Workflow

1. Read `~/.claude/chef/config.md` if it exists — show current values
2. For each field with no value (or all if first run), ask the user
3. **Output the full config as a markdown code block in your response — do this BEFORE calling Write.** Use YAML frontmatter format with `---` delimiters. Do NOT use bullet lists. Example:
   ```
   ---
   location: Montreal, QC
   preferred_stores: IGA Plateau, Metro Jean-Talon, SAQ
   dietary: none
   people: 2
   cuisine_preference: French, Italian, Japanese
   skill_level: intermediate
   ---
   ```
4. Then write the config to `~/.claude/chef/config.md`
5. Confirm saved (or show the content to paste manually if write is blocked)

## Output Format

```markdown
---
location: Montreal, QC
preferred_stores: IGA Plateau, Metro Jean-Talon, SAQ
dietary: none
people: 2
cuisine_preference: French, Italian, Japanese
skill_level: intermediate
oven_temp_unit: fahrenheit
---
```

## Notes

- `preferred_stores` is also used by the grocer skill — keep it accurate
- For partial updates (e.g. "change my location"): only update that field; keep all others unchanged; always show the new value explicitly (e.g. "Updating location → Quebec City, QC") before writing
- Confirm the saved config at the end
