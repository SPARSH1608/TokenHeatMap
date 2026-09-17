#!/usr/bin/env python3
"""
Render a self-contained, interactive HTML heatmap widget from
token-heatmap-data.json: real hover tooltips and a GitHub-style year
selector, for embedding on a portfolio site (via <iframe> or inline).

This is NOT for GitHub READMEs - a markdown ![]() image always renders as a
flat <img>, which never runs hover/focus interactivity no matter what the
SVG contains. Use render_svg.py's static .svg for README embeds; use this
.html file wherever the page's own HTML/JS can run (iframe, inline embed, or
opened directly).

All usage data is embedded inline as JSON, so switching years re-renders
instantly client-side with no network round trip.
"""
import argparse
import json

# Same sequential Claude-coral ramp as render_svg.py, light -> dark = low -> high
# activity in both modes (see that file for the color rationale).
LEVEL_COLORS_LIGHT = ["#ece6dc", "#f3d0b8", "#eba883", "#d97757", "#a8442a"]
LEVEL_COLORS_DARK = ["#d8cbb8", "#e8b98a", "#d97757", "#a8442a", "#6b2f1a"]

SURFACE_LIGHT = "#fcfcfb"
SURFACE_DARK = "#1a1a19"

TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Claude Token Usage</title>
<style>
  :root {
    color-scheme: light dark;
    --surface: __SURFACE_LIGHT__;
    --text-primary: #0b0b0b;
    --text-secondary: #52514e;
    --text-muted: #898781;
    --border: rgba(11,11,11,0.10);
    --tooltip-bg: #0b0b0b;
    --tooltip-fg: #ffffff;
    --level-0: __L0_LIGHT__; --level-1: __L1_LIGHT__; --level-2: __L2_LIGHT__;
    --level-3: __L3_LIGHT__; --level-4: __L4_LIGHT__;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --surface: __SURFACE_DARK__;
      --text-primary: #ffffff;
      --text-secondary: #c3c2b7;
      --border: rgba(255,255,255,0.10);
      --tooltip-bg: #ffffff;
      --tooltip-fg: #0b0b0b;
      --level-0: __L0_DARK__; --level-1: __L1_DARK__; --level-2: __L2_DARK__;
      --level-3: __L3_DARK__; --level-4: __L4_DARK__;
    }
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 16px;
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    background: var(--surface); color: var(--text-primary);
  }
  .widget { max-width: 900px; }
  .headline { font-size: 16px; font-weight: 600; margin: 0 0 2px; }
  .subline { font-size: 12px; color: var(--text-secondary); margin: 0 0 14px; }
  .years {
    display: flex; gap: 6px; margin-bottom: 14px; flex-wrap: wrap;
  }
  .year-btn {
    font: inherit; font-size: 12px; padding: 5px 10px; border-radius: 6px;
    border: 1px solid var(--border); background: transparent; color: var(--text-secondary);
    cursor: pointer;
  }
  .year-btn:hover { background: color-mix(in srgb, var(--text-primary) 6%, transparent); }
  .year-btn[aria-pressed="true"] {
    background: var(--text-primary); color: var(--surface); border-color: var(--text-primary);
    font-weight: 600;
  }
  .grid-scroll { overflow-x: auto; }
  svg { display: block; }
  .cell {
    stroke: transparent; stroke-width: 2px; cursor: pointer;
    transition: stroke 0.1s ease;
  }
  .cell:hover, .cell:focus { stroke: var(--text-primary); outline: none; }
  .month-label, .legend-label { fill: var(--text-muted); font-size: 10px; }
  .legend-swatch { rx: 2px; }
  .footer { display: flex; align-items: center; gap: 6px; margin-top: 10px; justify-content: flex-end; }
  .tooltip {
    position: fixed; pointer-events: none; z-index: 10;
    background: var(--tooltip-bg); color: var(--tooltip-fg);
    font-size: 12px; padding: 6px 9px; border-radius: 6px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    opacity: 0; transform: translate(-50%, -100%); transition: opacity 0.08s ease;
    white-space: nowrap;
  }
  .tooltip.visible { opacity: 1; }
  .tooltip .value { font-weight: 700; }
  .tooltip .date { color: var(--text-secondary); font-size: 11px; margin-top: 1px; }
</style>
</head>
<body>
<div class="widget">
  <p class="headline" id="headline"></p>
  <p class="subline" id="subline"></p>
  <div class="years" id="years" role="tablist" aria-label="Select year"></div>
  <div class="grid-scroll"><svg id="chart" xmlns="http://www.w3.org/2000/svg"></svg></div>
  <div class="footer">
    <span class="legend-label">Less</span>
    <svg width="80" height="12"><g id="legend"></g></svg>
    <span class="legend-label">More</span>
  </div>
</div>
<div class="tooltip" id="tooltip" role="status" aria-live="polite">
  <div class="value" id="tooltip-value"></div>
  <div class="date" id="tooltip-date"></div>
</div>
<script>
const USAGE = __USAGE_JSON__;
const CELL = 11, GAP = 3, STEP = CELL + GAP;
const LEFT_PAD = 8, TOP_PAD = 20, RIGHT_PAD = 8;
const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

function humanize(n) {
  n = Number(n);
  if (Math.abs(n) >= 1e9) return (n / 1e9).toFixed(1) + "B";
  if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(1) + "M";
  if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(1) + "K";
  return String(Math.round(n));
}

function isoDate(d) {
  return d.toISOString().slice(0, 10);
}

function buildTrailingDays(endDate, weeks) {
  const end = new Date(endDate);
  end.setDate(end.getDate() + ((6 - end.getDay() + 7) % 7)); // roll forward to Saturday
  const days = [];
  const start = new Date(end);
  start.setDate(start.getDate() - (weeks * 7 - 1));
  for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
    days.push(new Date(d));
  }
  return days;
}

function buildCalendarYearDays(year) {
  const jan1 = new Date(Date.UTC(year, 0, 1));
  const dec31 = new Date(Date.UTC(year, 11, 31));
  const start = new Date(jan1);
  start.setDate(start.getDate() - start.getDay()); // back to Sunday
  const end = new Date(dec31);
  end.setDate(end.getDate() + (6 - end.getDay())); // forward to Saturday
  const days = [];
  for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
    days.push(new Date(d));
  }
  return days;
}

// Global quartile thresholds across ALL history, so a color means the same
// activity level no matter which year is selected.
function computeLevelFn() {
  const values = Object.values(USAGE).map(d => d.tokens).filter(t => t > 0).sort((a, b) => a - b);
  if (!values.length) return () => 0;
  const q = p => values[Math.min(values.length - 1, Math.floor(values.length * p))];
  const q1 = q(0.25), q2 = q(0.5), q3 = q(0.75);
  return t => {
    if (t <= 0) return 0;
    if (t <= q1) return 1;
    if (t <= q2) return 2;
    if (t <= q3) return 3;
    return 4;
  };
}
const levelOf = computeLevelFn();

function weeksFromDays(days) {
  const weeks = [];
  for (let i = 0; i < days.length; i += 7) weeks.push(days.slice(i, i + 7));
  return weeks;
}

const svgNS = "http://www.w3.org/2000/svg";
function el(tag, attrs) {
  const e = document.createElementNS(svgNS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  return e;
}

const tooltip = document.getElementById("tooltip");
const tooltipValue = document.getElementById("tooltip-value");
const tooltipDate = document.getElementById("tooltip-date");

function showTooltip(evt, tokens, dateStr) {
  tooltipValue.textContent = humanize(tokens) + " tokens";
  tooltipDate.textContent = dateStr;
  tooltip.classList.add("visible");
  positionTooltip(evt);
}
function positionTooltip(evt) {
  const rect = evt.target.getBoundingClientRect();
  tooltip.style.left = (rect.left + rect.width / 2) + "px";
  tooltip.style.top = (rect.top - 6) + "px";
}
function hideTooltip() {
  tooltip.classList.remove("visible");
}

function render(selection) {
  const svg = document.getElementById("chart");
  svg.innerHTML = "";
  const days = selection.current
    ? buildTrailingDays(new Date(), 53)
    : buildCalendarYearDays(selection.year);
  const weeks = weeksFromDays(days);

  const width = LEFT_PAD + weeks.length * STEP + RIGHT_PAD;
  const height = TOP_PAD + 7 * STEP;
  svg.setAttribute("width", width);
  svg.setAttribute("height", height);
  svg.setAttribute("viewBox", "0 0 " + width + " " + height);

  let total = 0, active = 0;
  let lastMonth = null;
  weeks.forEach((week, wi) => {
    const x = LEFT_PAD + wi * STEP;
    week.forEach((date, di) => {
      const y = TOP_PAD + di * STEP;
      const key = isoDate(date);
      const entry = USAGE[key];
      const tokens = entry ? entry.tokens : 0;
      if (tokens > 0) { total += tokens; active += 1; }
      if (date.getUTCDate() <= 7 && date.getUTCMonth() !== lastMonth) {
        lastMonth = date.getUTCMonth();
        const label = el("text", { x: x, y: TOP_PAD - 8, class: "month-label" });
        label.textContent = MONTHS[lastMonth];
        svg.appendChild(label);
      }
      const level = levelOf(tokens);
      const rect = el("rect", {
        x: x, y: y, width: CELL, height: CELL, rx: 2, ry: 2,
        class: "cell", fill: "var(--level-" + level + ")",
        tabindex: "0", role: "img", "aria-label": key + ": " + tokens.toLocaleString() + " tokens",
      });
      rect.addEventListener("pointerenter", e => showTooltip(e, tokens, key));
      rect.addEventListener("pointermove", positionTooltip);
      rect.addEventListener("pointerleave", hideTooltip);
      rect.addEventListener("focus", e => showTooltip(e, tokens, key));
      rect.addEventListener("blur", hideTooltip);
      svg.appendChild(rect);
    });
  });

  document.getElementById("headline").textContent = humanize(total) + " tokens processed";
  document.getElementById("subline").textContent =
    (selection.current ? "in the last year" : "in " + selection.year) +
    " \\u00b7 " + active + " active days";

  const legend = document.getElementById("legend");
  legend.innerHTML = "";
  for (let i = 0; i < 5; i++) {
    legend.appendChild(el("rect", {
      x: i * 15, y: 0, width: CELL, height: CELL, rx: 2, ry: 2,
      fill: "var(--level-" + i + ")",
    }));
  }
}

function buildYearButtons() {
  const dates = Object.keys(USAGE);
  const currentYear = new Date().getFullYear();
  let minYear = currentYear;
  dates.forEach(d => { minYear = Math.min(minYear, parseInt(d.slice(0, 4), 10)); });

  const years = document.getElementById("years");
  const options = [{ label: String(currentYear), current: true }];
  for (let y = currentYear - 1; y >= minYear; y--) {
    options.push({ label: String(y), year: y, current: false });
  }

  function select(opt, btn) {
    [...years.children].forEach(b => b.setAttribute("aria-pressed", "false"));
    btn.setAttribute("aria-pressed", "true");
    render(opt);
  }

  options.forEach((opt, i) => {
    const btn = document.createElement("button");
    btn.className = "year-btn";
    btn.type = "button";
    btn.textContent = opt.label;
    btn.setAttribute("role", "tab");
    btn.setAttribute("aria-pressed", i === 0 ? "true" : "false");
    btn.addEventListener("click", () => select(opt, btn));
    years.appendChild(btn);
    if (i === 0) render(opt);
  });
}

buildYearButtons();
</script>
</body>
</html>
"""


def render_html(data, title="Claude Token Usage"):
    html = TEMPLATE
    html = html.replace("__USAGE_JSON__", json.dumps(data))
    html = html.replace("__SURFACE_LIGHT__", SURFACE_LIGHT)
    html = html.replace("__SURFACE_DARK__", SURFACE_DARK)
    for i in range(5):
        html = html.replace(f"__L{i}_LIGHT__", LEVEL_COLORS_LIGHT[i])
        html = html.replace(f"__L{i}_DARK__", LEVEL_COLORS_DARK[i])
    return html


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="token-heatmap-data.json")
    parser.add_argument("--out", default="token-heatmap.html")
    args = parser.parse_args()

    with open(args.data, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    html = render_html(data)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
