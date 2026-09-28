"""Draws a Game of Life run as a looping SVG styled like GitHub's contribution graph."""

import datetime as dt

CELL, GAP = 10, 3
LEFT, TOP = 32, 22
INTRO = 2.5  # seconds showing the real contribution graph before Life starts
TICK = 0.18  # seconds per generation
HOLD = 3.0  # seconds on the final generation before looping

# GitHub's own graph colours: empty, then the four contribution levels.
LIGHT = ("#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39")
DARK = ("#161b22", "#0e4429", "#006d32", "#26a641", "#39d353")


def _squares(cells):
    return "".join(f"M{LEFT + c * (CELL + GAP)} {TOP + r * (CELL + GAP)}h{CELL}v{CELL}h-{CELL}z" for r, c in sorted(cells))


def render(run, levels, first_day):
    """levels: {(row, col): 1-4} for the real graph; first_day: date of cell (0, 0)."""
    n = len(run.generations)
    total = INTRO + (n - 1) * TICK + HOLD
    width = LEFT + run.cols * (CELL + GAP) + 6
    height = TOP + run.rows * (CELL + GAP) + 24

    def pct(seconds):
        return round(seconds / total * 100, 3)

    def start(g):
        return 0 if g == 0 else INTRO + (g - 1) * TICK

    def end(g):
        return total if g == n - 1 else start(g + 1)

    css = [
        f".l0{{fill:{LIGHT[0]}}}.l1{{fill:{LIGHT[1]}}}.l2{{fill:{LIGHT[2]}}}.l3{{fill:{LIGHT[3]}}}.l4{{fill:{LIGHT[4]}}}"
        "text{font:10px -apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;fill:#57606a}",
        "@media (prefers-color-scheme:dark){"
        f".l0{{fill:{DARK[0]}}}.l1{{fill:{DARK[1]}}}.l2{{fill:{DARK[2]}}}.l3{{fill:{DARK[3]}}}.l4{{fill:{DARK[4]}}}"
        "text{fill:#8b949e}}",
        "g.f{opacity:0;animation-duration:%.2fs;animation-iteration-count:infinite;animation-timing-function:steps(1,end)}" % total,
    ]
    body = [f'<path class="l0" d="{_squares((r, c) for r in range(run.rows) for c in range(run.cols))}"/>']

    # Month labels along the top and weekday labels down the side, like GitHub.
    starts, last_month = [], None
    for c in range(run.cols):
        day = first_day + dt.timedelta(weeks=c, days=6)  # the column's last day
        if day.month != last_month:
            starts.append((c, day))
            last_month = day.month
    for (c, day), nxt in zip(starts, starts[1:] + [(run.cols, None)]):
        if nxt[0] - c >= 3:  # skip a label that would collide with the next one
            body.append(f'<text x="{LEFT + c * (CELL + GAP)}" y="{TOP - 8}">{day:%b}</text>')
    for r, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        body.append(f'<text x="0" y="{TOP + r * (CELL + GAP) + CELL - 1}">{name}</text>')

    for g, live in enumerate(run.generations):
        a, b = pct(start(g)), pct(end(g))
        css.append(f"@keyframes f{g}{{0%{{opacity:0}}{a}%{{opacity:1}}{b}%{{opacity:0}}}}.f{g}{{animation-name:f{g}}}")
        if g == 0:
            paths = "".join(
                f'<path class="l{lv}" d="{_squares(c for c, v in levels.items() if v == lv)}"/>'
                for lv in (1, 2, 3, 4)
                if lv in levels.values()
            )
            label = "your year of commits"
        else:
            born = live - run.generations[g - 1]
            paths = (
                f'<path class="l4" d="{_squares(live - born)}"/>' if live - born else ""
            ) + (f'<path class="l2" d="{_squares(born)}"/>' if born else "")
            label = f"generation {g}"
        body.append(
            f'<g class="f f{g}">{paths}'
            f'<text x="{width - 6}" y="{height - 6}" text-anchor="end">{label}</text></g>'
        )

    # Without animation support, show the real graph rather than a blank grid.
    css.append("@media (prefers-reduced-motion:reduce){g.f{animation:none}.f0{opacity:1}}")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        'role="img" aria-label="My GitHub contribution graph playing Conway\'s Game of Life">'
        f"<style>{''.join(css)}</style>{''.join(body)}</svg>\n"
    )
