"""Turn the past year's contribution graph into a Game of Life and update the README.

Usage: python -m life                    (needs GITHUB_TOKEN and GITHUB_USER)
       python -m life --calendar x.json  (a saved GraphQL response, for local testing)
"""

import datetime as dt
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

from .game import MAX_GENERATIONS, play
from .render import render

ROOT = Path(__file__).resolve().parent.parent
SVG = ROOT / "assets" / "life.svg"
README = ROOT / "README.md"
MARKERS = re.compile(r"(<!-- LIFE:START -->).*?(<!-- LIFE:END -->)", re.S)
LEVELS = {"FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
QUERY = """query($login: String!) { user(login: $login) { contributionsCollection {
  contributionCalendar { weeks { contributionDays { date weekday contributionLevel } } } } } }"""


def fetch(login, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def _plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def caption(run):
    g = run.ended_at
    if run.outcome == "extinct":
        return f"💀 My commits went extinct after {_plural(g, 'generation')}."
    if run.outcome == "still":
        return f"🪨 My commits froze into a still life after {_plural(g, 'generation')}."
    if run.outcome == "loop":
        return f"🔁 My commits got stuck in a {run.period}-step loop at generation {g}."
    return f"🌱 My commits were still going after {MAX_GENERATIONS} generations."


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--calendar":
        data = json.loads(Path(sys.argv[2]).read_text())
    else:
        data = fetch(os.environ["GITHUB_USER"], os.environ["GITHUB_TOKEN"])
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]

    levels = {}
    for col, week in enumerate(weeks):
        for day in week["contributionDays"]:
            if day["contributionLevel"] in LEVELS:
                levels[(day["weekday"], col)] = LEVELS[day["contributionLevel"]]
    first = dt.date.fromisoformat(weeks[0]["contributionDays"][0]["date"])
    first -= dt.timedelta(days=weeks[0]["contributionDays"][0]["weekday"])

    run = play(levels, 7, len(weeks))
    SVG.parent.mkdir(exist_ok=True)
    SVG.write_text(render(run, levels, first))

    today = dt.datetime.now(dt.timezone.utc).date()
    block = f"""<div align="center">

<img src="assets/life.svg?v={today:%Y%m%d}" alt="My contribution graph playing Conway's Game of Life">

**{caption(run)}**

<sub>{_plural(len(levels), 'active day')} in the last year became the starting cells · updated {today:%d %b %Y}</sub>

</div>"""
    text = README.read_text()
    if not MARKERS.search(text):
        sys.exit("README is missing the LIFE markers")
    README.write_text(MARKERS.sub(lambda m: f"{m[1]}\n{block}\n{m[2]}", text))
    print(caption(run))


if __name__ == "__main__":
    main()
