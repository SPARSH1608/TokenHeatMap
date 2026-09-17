# TokenHeatMap

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)

A GitHub-contributions-style heatmap of your Claude token usage — generated
locally from your own Claude Code logs, embeddable in READMEs and portfolios.

![Example heatmap](./skills/token-heatmap/examples/token-heatmap-example.svg)

*(synthetic example data — install the skill to generate your own)*

## Status

**Phase 1: Claude Code only.** Data comes entirely from your local
`~/.claude/projects` session logs — nothing is sent anywhere. Support for
other agents (Codex, Copilot, etc.) and any hosted/always-live badge are
future phases, not implemented yet.

## What it is

A **Claude Code skill** (not an app or a server) that:

1. Reads your local Claude Code session transcripts.
2. Aggregates tokens processed per day.
3. Renders two output forms, both light/dark aware:
   - `token-heatmap.svg` — static, for README/markdown embeds.
   - `token-heatmap.html` — a self-contained interactive widget with real
     hover tooltips and a year selector, for portfolio sites.

Why two files: a markdown `![]()` image always renders as a flat `<img>`, so
hover/focus interactivity never runs there no matter what's inside the SVG —
that's a browser platform limit. The `.html` widget is for contexts where
you control the page's own HTML/JS (an `<iframe>` or inline embed).

## Install

Copy the skill into your own Claude Code skills directory:

```bash
git clone https://github.com/SPARSH1608/TokenHeatMap.git
cp -r TokenHeatMap/skills/token-heatmap ~/.claude/skills/token-heatmap
```

(On Windows, copy `skills\token-heatmap` into `%USERPROFILE%\.claude\skills\`.)

Restart Claude Code (or start a new session) so it picks up the new skill.

## Use

From inside the repo you want the badge in, ask Claude:

> generate my token heatmap

Claude Code will invoke the `token-heatmap` skill, which:

- Writes `token-heatmap-data.json` (your aggregated per-day usage — safe to
  commit, or gitignore it if you'd rather keep raw numbers private).
- Writes `token-heatmap.svg` (static, for READMEs) and `token-heatmap.html`
  (interactive, for portfolios).

Or run the scripts directly, no Claude session needed. Run them from the
repo you want the badge in, pointing at wherever you installed the skill
(macOS/Linux shown; on Windows use `%USERPROFILE%\.claude\skills\token-heatmap\scripts\...`):

```bash
python ~/.claude/skills/token-heatmap/scripts/collect_usage.py --out token-heatmap-data.json
python ~/.claude/skills/token-heatmap/scripts/render_svg.py --data token-heatmap-data.json --out token-heatmap.svg
python ~/.claude/skills/token-heatmap/scripts/render_html.py --data token-heatmap-data.json --out token-heatmap.html
```

## Embed it

**README/markdown** (static SVG) — same repo:

```markdown
![Claude Token Usage](./token-heatmap.svg)
```

From a different repo (e.g. a dedicated stats/profile repo), reference the
raw file:

```markdown
![Claude Token Usage](https://raw.githubusercontent.com/<you>/<repo>/<branch>/token-heatmap.svg)
```

**Portfolio site** (interactive widget — real hover tooltips, click a year
to switch it, all data embedded inline so switching is instant):

```html
<iframe src="/token-heatmap.html" width="100%" height="220" style="border:none"></iframe>
```

For a framework-based site (Next.js, Astro, etc.), that means putting the
file in your `public/` folder (or equivalent) so it's served as a static
asset. You can also inline the widget's `<body>`/`<style>`/`<script>`
directly into a page instead of using an iframe, if you prefer.

## Keeping it up to date

By default, generating the heatmap doesn't auto-commit or auto-push — you
review the diff and commit yourself.

If you want it to **update automatically every day**, run the setup script
once. It registers a local scheduled task (Windows Task Scheduler, or cron on
macOS/Linux) that collects usage, re-renders both the SVG and the HTML
widget, and commits + pushes them — skipping the commit entirely on days
with no change:

```bash
python ~/.claude/skills/token-heatmap/scripts/setup_autoupdate.py --repo-dir /path/to/your/repo --time 06:00
```

This pushes to your git remote unattended, daily, until you remove it. Two
things to check first:

- `git push` already works non-interactively from this machine for that repo
  (cached credentials or an SSH agent with no passphrase prompt) — otherwise
  the scheduled run just fails silently every day.
- You're comfortable with an unattended process pushing commits on a
  schedule. Remove it any time with `--uninstall` (same command, plus that
  flag), or delete the generated wrapper script
  (`.token-heatmap-autoupdate.sh`/`.bat` in your repo) and its scheduled
  task/cron entry directly.

See [skills/token-heatmap/SKILL.md](./skills/token-heatmap/SKILL.md) for the
full details and safety notes.

## How the numbers work

Each day's token count sums `input + output + cache_creation + cache_read`
tokens across every assistant turn logged that day — i.e. total tokens
processed, not just what you typed or read. Cache reads dominate on long
sessions, which is why daily totals can look large; that's real usage/API
activity, not a bug.

## Project layout

```
skills/token-heatmap/
  SKILL.md                      - the installable skill definition
  scripts/collect_usage.py      - aggregates local logs -> usage JSON
  scripts/render_svg.py         - renders usage JSON -> static SVG heatmap
  scripts/render_html.py        - renders usage JSON -> interactive HTML widget
  scripts/setup_autoupdate.py   - registers/removes the daily auto-update task
  examples/                     - synthetic sample data + rendered examples
```

## Roadmap

- [x] Phase 1 — Claude Code, local logs, static SVG
- [ ] Phase 2 — other agents (Codex, Copilot, ...)
- [ ] Phase 3 — optional hosted badge for always-live embeds without local scheduling

## Contributing

Issues and PRs welcome — this is early and Phase 1-scoped on purpose, so
"add agent X" or "add metric Y" suggestions are useful even before there's
code behind them.

## License

[MIT](./LICENSE)
