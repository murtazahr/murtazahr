"""Run today's simulation, write the SVG, and refresh the README exhibit.

Usage: python -m quorum [YYYY-MM-DD]
"""

import datetime as dt
import re
import sys
from pathlib import Path

from .render import render
from .simulate import ATTACKS, run

ROOT = Path(__file__).resolve().parent.parent
SVG = ROOT / "assets" / "quorum.svg"
README = ROOT / "README.md"
MARKERS = re.compile(r"(<!-- QUORUM:START -->).*?(<!-- QUORUM:END -->)", re.S)


def _plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def headline(res):
    f = len(res.byzantine)
    caught = sum(res.isolated(b) for b in res.byzantine)
    escaped = f - caught
    friendly = res.false_cuts()
    left_behind = res.stragglers()
    if left_behind * 4 > len(res.honest):
        return "The army split — no single plan"
    if left_behind:
        return f"The army agreed, but {_plural(left_behind, 'loyal general')} got left behind"
    if escaped == 0 and friendly == 0:
        return "Every traitor unmasked, no friendly fire"
    if escaped == 0:
        return "Every traitor unmasked"
    if escaped == f:
        return "The traitors went unnoticed"
    return f"{_plural(escaped, 'traitor')} blended in"


def exhibit(res, day):
    f = len(res.byzantine)
    caught = sum(res.isolated(b) for b in res.byzantine)
    last = max((res.isolated_at(b) or 0) for b in res.byzantine)
    unmasked = f"**{caught}/{f}**" + (f" by round {last}" if caught else "")
    return f"""<div align="center">

<img src="assets/quorum.svg?v={day:%Y%m%d}" alt="Today's Byzantine generals simulation" width="720">

### {headline(res)}

{_plural(len(res.honest), 'loyal general')} · {_plural(f, 'hidden traitor')} · tactic: **{res.attack}** — {ATTACKS[res.attack]}

Traitors unmasked {unmasked} · loyal links cut by mistake **{res.false_cuts()}** · final disagreement **{res.spread():.3f}** · distance from the honest average **{res.error():.3f}**

<sub>simulated {day:%Y-%m-%d} · seeded by the date, so every day is a new battlefield</sub>

</div>"""


def main():
    day = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else dt.date.today()
    res = run(day.isoformat())
    SVG.parent.mkdir(exist_ok=True)
    SVG.write_text(render(res))
    text = README.read_text()
    if not MARKERS.search(text):
        sys.exit("README is missing the QUORUM markers")
    README.write_text(MARKERS.sub(lambda m: f"{m[1]}\n{exhibit(res, day)}\n{m[2]}", text))
    print(f"{day}: {headline(res)}")


if __name__ == "__main__":
    main()
