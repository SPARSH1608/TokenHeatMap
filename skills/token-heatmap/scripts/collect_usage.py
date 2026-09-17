#!/usr/bin/env python3
"""
Aggregate per-day Claude Code token usage from local session transcripts.

Claude Code writes one JSONL file per session under ~/.claude/projects/<project>/,
where every assistant turn is logged as a line with:
  { "type": "assistant", "timestamp": "...", "message": { "id": "...", "usage": {...} } }

A single logical turn can appear multiple times in the file (once per streamed
content block), each copy carrying the same message id -- we dedupe by id and
keep the last occurrence, which holds the final usage snapshot for that turn.
"""
import argparse
import glob
import json
import os
from collections import defaultdict

DEFAULT_LOGS_DIR = os.path.expanduser("~/.claude/projects")


def iter_assistant_turns(logs_dir):
    pattern = os.path.join(logs_dir, "**", "*.jsonl")
    for path in glob.glob(pattern, recursive=True):
        seen = {}
        order = []
        try:
            with open(path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if entry.get("type") != "assistant":
                        continue
                    message = entry.get("message") or {}
                    usage = message.get("usage")
                    msg_id = message.get("id")
                    timestamp = entry.get("timestamp")
                    if not usage or not msg_id or not timestamp:
                        continue
                    if msg_id not in seen:
                        order.append(msg_id)
                    seen[msg_id] = (timestamp, usage, message.get("model"))
        except OSError:
            continue
        for msg_id in order:
            timestamp, usage, model = seen[msg_id]
            yield timestamp, usage, model


def turn_tokens(usage):
    return (
        (usage.get("input_tokens") or 0)
        + (usage.get("output_tokens") or 0)
        + (usage.get("cache_creation_input_tokens") or 0)
        + (usage.get("cache_read_input_tokens") or 0)
    )


def collect(logs_dir):
    days = defaultdict(lambda: {"tokens": 0, "messages": 0, "models": defaultdict(int)})
    for timestamp, usage, model in iter_assistant_turns(logs_dir):
        date = timestamp[:10]  # YYYY-MM-DD (UTC, as logged)
        day = days[date]
        day["tokens"] += turn_tokens(usage)
        day["messages"] += 1
        if model:
            day["models"][model] += 1
    return days


def merge(existing, fresh):
    """Fresh counts win for any date present in the current logs; dates only
    present in `existing` (e.g. log files since rotated away) are kept as-is."""
    merged = dict(existing)
    for date, day in fresh.items():
        merged[date] = day
    return merged


def to_serializable(days):
    out = {}
    for date, day in sorted(days.items()):
        out[date] = {
            "tokens": day["tokens"],
            "messages": day["messages"],
            "models": dict(day["models"]),
        }
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--logs-dir",
        default=DEFAULT_LOGS_DIR,
        help="Directory to scan for Claude Code session logs (default: %(default)s)",
    )
    parser.add_argument(
        "--out",
        default="token-heatmap-data.json",
        help="Path to write/update the aggregated usage JSON (default: %(default)s)",
    )
    parser.add_argument(
        "--no-merge",
        action="store_true",
        help="Overwrite --out entirely instead of merging with its existing contents",
    )
    args = parser.parse_args()

    fresh = to_serializable(collect(args.logs_dir))

    existing = {}
    if not args.no_merge and os.path.exists(args.out):
        with open(args.out, "r", encoding="utf-8") as fh:
            try:
                existing = json.load(fh)
            except json.JSONDecodeError:
                existing = {}

    result = merge(existing, fresh) if not args.no_merge else fresh

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, sort_keys=True)

    total_tokens = sum(d["tokens"] for d in result.values())
    print(f"Wrote {len(result)} day(s), {total_tokens:,} total tokens -> {args.out}")


if __name__ == "__main__":
    main()
