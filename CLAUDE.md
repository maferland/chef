# chef — plugin dev repo

This is the **development repository** for the chef Claude Code plugin.
It is not a project where the chef plugin is meant to be *used* — it is where it is *built and tested*.

## Testing

When running verdict tests in `tests/verdict/`:
- Treat each test as self-contained — do not apply personal chef config values (`~/.claude/chef/config.md`) to skill behavior under evaluation
- Test prompts include all necessary context (dietary, people, skill level, time) and should be evaluated on that context alone
- If a test prompt omits a field, use the skill's built-in defaults (2 people, intermediate, no restrictions) — not the user's personal config
- Test runs set `sessionDir: /tmp/chef-tests` in the env — sessions generated during tests go there, not into `./sessions/`
