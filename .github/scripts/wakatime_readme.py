#!/usr/bin/env python3
"""Render public WakaTime stats into the waka section of the profile README.

Reads only the public stats endpoint. WakaTime restricts API keys to editor
plugins, so no secret is used here: whichever range the account exposes
publicly is the range this renders.
"""

import json
import os
import re
import sys
import urllib.request

USER_ID = os.environ.get("WAKATIME_USER_ID", "")
READY = ("last_7_days", "last_30_days", "last_year", "all_time")
LABELS = {
    "last_7_days": "This Week",
    "last_30_days": "Last 30 Days",
    "last_year": "Last Year",
    "all_time": "All Time",
}
BAR_WIDTH = 24
MAX_LANGS = 5


def fetch(rng):
    url = f"https://wakatime.com/api/v1/users/{USER_ID}/stats/{rng}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for _ in range(2):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status == 200:
                    return json.load(resp)["data"]
        except Exception:
            continue
    return None


def render(data, rng):
    total = data.get("human_readable_total_including_other_language") or "-"
    langs = data.get("languages") or []
    rows = []
    for lang in langs[:MAX_LANGS]:
        name = lang.get("name", "?")
        text = lang.get("text", "-")
        pct = float(lang.get("percent") or 0)
        filled = max(0, min(BAR_WIDTH, int(round(pct / 100 * BAR_WIDTH))))
        bar = "█" * filled + "░" * (BAR_WIDTH - filled)
        rows.append(f"{name:<12}{text:<15}{bar}  {pct:5.2f} %")

    out = [f"**{LABELS.get(rng, rng)}** · {total} total", ""]
    if rows:
        out.append("```txt")
        out.extend(rows)
        out.append("```")
    else:
        out.append("_No language data is public right now._")
    return "\n".join(out)


def main():
    if not USER_ID:
        print("WAKATIME_USER_ID is not set", file=sys.stderr)
        return 1

    data = None
    used = ""
    for rng in READY:
        data = fetch(rng)
        if data:
            used = rng
            break

    if not data:
        print("No public stats range is reachable for this account", file=sys.stderr)
        return 1

    block = render(data, used)
    path = "README.md"
    with open(path, encoding="utf-8") as fh:
        src = fh.read()

    pattern = r"(<!--START_SECTION:waka-->)(.*?)(<!--END_SECTION:waka-->)"
    if not re.search(pattern, src, flags=re.S):
        print("waka markers not found in README.md", file=sys.stderr)
        return 1

    updated = re.sub(
        pattern,
        lambda m: m.group(1) + "\n" + block + "\n" + m.group(3),
        src,
        count=1,
        flags=re.S,
    )

    if updated == src:
        print(f"unchanged ({used})")
        return 0

    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(updated)
    print(f"updated ({used})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
