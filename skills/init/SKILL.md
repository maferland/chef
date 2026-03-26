---
name: init
description: Bootstrap the chef config file with sensible defaults. Use once after installing the plugin. If config already exists, shows current values and offers to reset.
user_invocable: true
---

# Chef Init

Bootstrap `~/.claude/chef/config.md` with template defaults so the user can get started immediately.

## Workflow

1. Check if `~/.claude/chef/config.md` already exists
   - **Exists**: show current values, tell the user to run `/chef:configure` to update any field
   - **Does not exist**: write the default config, tell user what to edit

2. Write the default config (new installs only):

```
---
location: # your city, e.g. Montreal, QC
preferred_stores: # e.g. IGA, Metro, SAQ
dietary: none
people: 2
cuisine_preference: # e.g. French, Italian, Japanese
skill_level: intermediate
oven_temp_unit: fahrenheit
---
```

3. Confirm the file was written and tell the user the two next steps:
   - Edit `~/.claude/chef/config.md` to fill in location and preferences
   - Or run `/chef:configure` for an interactive setup

## Notes

- Create `~/.claude/chef/` directory if it doesn't exist
- Do NOT overwrite an existing config without asking
- This is a one-time bootstrap — for updates, use `/chef:configure`
