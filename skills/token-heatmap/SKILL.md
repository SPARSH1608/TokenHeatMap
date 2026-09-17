---
name: token-heatmap
description: Generate a GitHub-contributions-style SVG heatmap of the user's Claude Code token usage, for embedding in a README or portfolio. Use when the user asks to create, update, or embed a "token heatmap", "usage heatmap", "Claude usage stats/badge", or wants to visualize/flex their Claude Code token usage over time.
---

# Token Heatmap

Generates a GitHub-contributions-style SVG calendar heatmap of the user's
Claude Code token usage, read from their local session logs
(`~/.claude/projects/**/*.jsonl`). The output is a single self-contained SVG
file meant to be committed to a repo and embedded in a README or portfolio
page.

Phase 1 scope: Claude Code only, local logs only, one machine at a time.
Multi-agent (Codex, Copilot, ...) and hosted/dynamic badges are future phases
- do not imply either exists.

## What this does NOT do

- It does not call any network API - all data comes from local log files.
- It does not commit or push to git on its own. After generating/updating the
  SVG, tell the user what changed and let them review the diff before they
  commit, per the standing git-safety rules (never commit/push without them
  asking).
- It does not run on a schedule by itself. If the user wants the heatmap to
  stay fresh automatically, see "Keeping it fresh" below - that requires a
  local scheduled task, since the usage data lives only on their machine.

## Steps

The scripts below live in `scripts/` next to this file, wherever this skill
was installed (e.g. `~/.claude/skills/token-heatmap/scripts/` on macOS/Linux,
`%USERPROFILE%\.claude\skills\token-heatmap\scripts\` on Windows) - **not**
inside the target repo. Resolve the full path to this SKILL.md's own
directory first (call it `<skill-dir>`), then invoke scripts by that
absolute path while your working directory stays the target repo, e.g.:

```
python <skill-dir>/scripts/collect_usage.py --out token-heatmap-data.json
```

Never assume a relative path like `skills/token-heatmap/scripts/...` resolves
- it only would if the target repo happened to be this project's own source
checkout, which is not the common case for an installed skill.

1. Confirm the target repo/directory the user wants the SVG written into
   (usually the repo whose README will embed it - often the current working
   directory, but ask if ambiguous rather than assuming).

2. Collect usage data:

   ```
   python <skill-dir>/scripts/collect_usage.py --out token-heatmap-data.json
   ```

   This scans `~/.claude/projects` and writes/merges a per-day token JSON.
   Re-running it is safe and incremental - it merges into the existing file
   rather than overwriting history, since old log files can rotate away.

3. Render the SVG:

   ```
   python <skill-dir>/scripts/render_svg.py --data token-heatmap-data.json --out token-heatmap.svg
   ```

   Useful flags: `--weeks N` (default 53, i.e. ~1 year), `--title "..."` to
   customize the header text.

4. Show the user the resulting file path and a one-line summary (total
   tokens, active days) - do not open a browser or push anywhere unprompted.

5. If this is the first time in this repo, offer the embed snippet for their
   README:

   ```markdown
   ![Claude Token Usage](./token-heatmap.svg)
   ```

   If the SVG lives in a different repo than the one being embedded into
   (e.g. a dedicated "stats" repo), use the raw GitHub URL instead:

   ```markdown
   ![Claude Token Usage](https://raw.githubusercontent.com/<user>/<repo>/<branch>/token-heatmap.svg)
   ```

## Keeping it fresh

Because the source data is local-only, an automatic "always up to date on
GitHub" badge (like WakaTime's) needs *something on the user's machine* to
re-run steps 2-3 and push periodically - a GitHub Action alone cannot reach
into `~/.claude/projects`. Two options to offer the user, never set up
without asking:

- **Manual**: re-run this skill whenever they want an updated snapshot.
- **Local schedule**: a cron job (macOS/Linux) or Windows Task Scheduler task
  that runs both scripts and then `git add/commit/push` on an interval (e.g.
  daily). Only wire this up if the user explicitly asks - it involves
  unattended `git push`, which needs their informed consent up front, not a
  one-time approval.

## Notes on the token metric

Each day's `tokens` figure sums `input_tokens + output_tokens +
cache_creation_input_tokens + cache_read_input_tokens` across all assistant
turns that day - i.e. total tokens processed by the API, including cache
reads (which are billed at a reduced rate but still reflect real usage/activity).
This tends to produce large numbers dominated by cache reads on long sessions;
that is expected and is what makes the heatmap a meaningful "activity" signal,
not a bug to silently work around.
