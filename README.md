# chef

Meal planning assistant for Claude Code. Plan recipes, source culinary inspiration, and generate shopping lists.

## Install

```
/plugin add maferland/chef
```

Or for local development, register in `~/.claude/settings.json`:

```json
"extraKnownMarketplaces": {
  "chef-marketplace": {
    "source": {
      "source": "directory",
      "path": "/path/to/chef"
    }
  }
}
```

Then enable: `chef@chef-marketplace`

## Usage

```
/chef:init
```
Run once after installing. Creates `~/.claude/chef/config.md` with defaults — edit it or follow up with `/chef:configure`.

```
/chef:configure
```
Interactively update any config field. Saved to `~/.claude/chef/config.md`.

```
/chef:plan weeknight dinner for 2, 45min, Italian
/chef:plan dinner party for 6, want to impress, have leftover duck
/chef:plan something quick, I have eggs and leeks
```
Get 3–5 recipe proposals matched to your context, pick one, receive a full recipe with grouped ingredients + shopping list.

```
/chef:source Joe Beef Montreal
/chef:source modern Japanese omakase techniques
/chef:source Normand Laprise
```
Research a restaurant, chef, or cuisine style. Produces an inspiration brief you can feed into `chef:plan`:

```
/chef:plan dinner party for 4, inspired by the Joe Beef brief
```

```
/chef:pair duck breast with mole
/chef:pair (uses last recipe from session)
```
Suggest drink pairings — wine, beer, cocktail, and non-alcoholic — matched to the occasion.

```
/chef:print
/chef:print shopping
/chef:print timeline
```
Generate print-ready PDFs from a saved session (shopping list + day-of timeline). Requires Chrome.

## Support

<a href="https://www.buymeacoffee.com/maferland"><img src="https://img.shields.io/badge/Buy%20Me%20A%20Coffee-support-yellow?logo=buymeacoffee&logoColor=white" alt="Buy Me A Coffee"></a>

## License

[MIT](LICENSE)
