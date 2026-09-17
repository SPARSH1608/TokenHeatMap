#!/usr/bin/env python3
"""
Render a GitHub-contributions-style SVG heatmap from token-heatmap-data.json.

Single-hue sequential encoding (light -> dark = low -> high activity), with a
separate dark-mode color set applied via @media (prefers-color-scheme: dark)
and a [data-theme="dark"] override, so the SVG adapts when viewed on GitHub
or embedded directly (raw <img>/<svg> embeds render the markup, not a flat
raster, so the media query is honored by the viewer's browser).
"""
import argparse
import datetime
import json

CELL = 11
GAP = 3
STEP = CELL + GAP
LEFT_PAD = 28
TOP_PAD = 40
BOTTOM_PAD = 28
RIGHT_PAD = 45
WEEKS = 53

# Sequential Claude-coral ramp (brand hue, light -> dark = low -> high activity).
LEVEL_COLORS_LIGHT = ["#ece6dc", "#f3d0b8", "#eba883", "#d97757", "#a8442a"]
LEVEL_COLORS_DARK = ["#3a332c", "#6b4530", "#a85c3c", "#d97757", "#f2a67e"]

SURFACE_LIGHT = "#fcfcfb"
SURFACE_DARK = "#1a1a19"
TEXT_PRIMARY_LIGHT = "#0b0b0b"
TEXT_PRIMARY_DARK = "#ffffff"
TEXT_MUTED = "#898781"

MONTH_NAMES = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def humanize(n):
    n = float(n)
    for unit, div in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(n) >= div:
            return f"{n / div:.1f}{unit}"
    return f"{int(n)}"


def load_data(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def build_grid(data, weeks=WEEKS):
    today = datetime.date.today()
    # End the grid on the most recent Saturday so the last column is a full week.
    end = today + datetime.timedelta(days=(5 - today.weekday()) % 7)
    start = end - datetime.timedelta(days=weeks * 7 - 1)
    days = []
    cur = start
    while cur <= end:
        key = cur.isoformat()
        tokens = data.get(key, {}).get("tokens", 0)
        days.append((cur, tokens))
        cur += datetime.timedelta(days=1)
    # Group into weeks of 7 (Sun..Sat), matching GitHub's layout.
    grid = [days[i:i + 7] for i in range(0, len(days), 7)]
    return grid


def bucket_levels(grid):
    values = sorted(t for week in grid for _, t in week if t > 0)
    if not values:
        return lambda t: 0
    q1 = values[int(len(values) * 0.25)]
    q2 = values[int(len(values) * 0.50)]
    q3 = values[int(len(values) * 0.75)]

    def level(t):
        if t <= 0:
            return 0
        if t <= q1:
            return 1
        if t <= q2:
            return 2
        if t <= q3:
            return 3
        return 4

    return level


def render(data, weeks=WEEKS, title="Claude Token Usage"):
    grid = build_grid(data, weeks)
    level_of = bucket_levels(grid)

    total_tokens = sum(t for week in grid for _, t in week)
    active_days = sum(1 for week in grid for _, t in week if t > 0)

    width = LEFT_PAD + len(grid) * STEP + RIGHT_PAD
    height = TOP_PAD + 7 * STEP + BOTTOM_PAD

    cells = []
    month_labels = []
    last_month = None
    for wi, week in enumerate(grid):
        x = LEFT_PAD + wi * STEP
        for di, (date, tokens) in enumerate(week):
            y = TOP_PAD + di * STEP
            if date.day <= 7 and date.month != last_month:
                month_labels.append((x, MONTH_NAMES[date.month - 1]))
                last_month = date.month
            level = level_of(tokens)
            cells.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" ry="2" '
                f'class="level-{level}"><title>{date.isoformat()}: {tokens:,} tokens</title></rect>'
            )

    month_svg = "".join(
        f'<text x="{x}" y="{TOP_PAD - 12}" class="muted">{name}</text>'
        for x, name in month_labels
    )

    legend_x = width - RIGHT_PAD - (5 * STEP) - 40
    legend_y = height - 16
    legend_swatches = "".join(
        f'<rect x="{legend_x + 26 + i * STEP}" y="{legend_y - CELL + 3}" '
        f'width="{CELL}" height="{CELL}" rx="2" ry="2" class="level-{i}"></rect>'
        for i in range(5)
    )

    total_label = f"{humanize(total_tokens)} tokens processed · {active_days} active days / {weeks} weeks"

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"
     viewBox="0 0 {width} {height}" font-family="system-ui, -apple-system, 'Segoe UI', sans-serif">
  <style>
    .surface {{ fill: {SURFACE_LIGHT}; }}
    .title {{ fill: {TEXT_PRIMARY_LIGHT}; font-size: 13px; font-weight: 600; }}
    .muted {{ fill: {TEXT_MUTED}; font-size: 10px; }}
    .level-0 {{ fill: {LEVEL_COLORS_LIGHT[0]}; }}
    .level-1 {{ fill: {LEVEL_COLORS_LIGHT[1]}; }}
    .level-2 {{ fill: {LEVEL_COLORS_LIGHT[2]}; }}
    .level-3 {{ fill: {LEVEL_COLORS_LIGHT[3]}; }}
    .level-4 {{ fill: {LEVEL_COLORS_LIGHT[4]}; }}
    @media (prefers-color-scheme: dark) {{
      .surface {{ fill: {SURFACE_DARK}; }}
      .title {{ fill: {TEXT_PRIMARY_DARK}; }}
      .level-0 {{ fill: {LEVEL_COLORS_DARK[0]}; }}
      .level-1 {{ fill: {LEVEL_COLORS_DARK[1]}; }}
      .level-2 {{ fill: {LEVEL_COLORS_DARK[2]}; }}
      .level-3 {{ fill: {LEVEL_COLORS_DARK[3]}; }}
      .level-4 {{ fill: {LEVEL_COLORS_DARK[4]}; }}
    }}
  </style>
  <rect x="0" y="0" width="{width}" height="{height}" class="surface"></rect>
  <text x="{LEFT_PAD}" y="18" class="title">{title}</text>
  <text x="{LEFT_PAD}" y="{height - 10}" class="muted">{total_label}</text>
  {month_svg}
  {''.join(cells)}
  <text x="{legend_x}" y="{legend_y}" class="muted">Less</text>
  {legend_swatches}
  <text x="{legend_x + 26 + 5 * STEP + 4}" y="{legend_y}" class="muted">More</text>
</svg>'''
    return svg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="token-heatmap-data.json", help="Usage JSON produced by collect_usage.py")
    parser.add_argument("--out", default="token-heatmap.svg", help="Path to write the rendered SVG")
    parser.add_argument("--weeks", type=int, default=WEEKS, help="Number of weeks to render (default: %(default)s)")
    parser.add_argument("--title", default="Claude Token Usage", help="Title text shown on the heatmap")
    args = parser.parse_args()

    data = load_data(args.data)
    svg = render(data, weeks=args.weeks, title=args.title)

    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(svg)

    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
