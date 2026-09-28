"""Renders a simulation Result as a looping, self-contained animated SVG."""

from .simulate import ROUNDS

W, H = 720, 400
PAD_X, TOP, BOTTOM = 36, 30, 330
INTRO = 1.5  # seconds on the starting positions
SLOW, FAST, SLOW_ROUNDS = 0.5, 0.16, 10  # early rounds play slowly so the mixing is visible
HOLD = 4.0  # seconds to linger on the final state
_T = [INTRO + min(k, SLOW_ROUNDS) * SLOW + max(0, k - SLOW_ROUNDS) * FAST for k in range(ROUNDS + 1)]
TOTAL = _T[-1] + HOLD

LOW, MID, HIGH = (56, 189, 248), (167, 139, 250), (251, 191, 36)
TRAITOR = "#e5534b"
EDGE = "#8b949e"


def _colour(v):
    a, b, t = (LOW, MID, v * 2) if v < 0.5 else (MID, HIGH, v * 2 - 1)
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def _pct(frame):
    """Keyframe percentage for a (possibly fractional) round number."""
    k = min(int(frame), ROUNDS - 1)
    t = _T[k] + (frame - k) * (_T[k + 1] - _T[k])
    return round(t / TOTAL * 100, 2)


def _xy(p):
    return (
        round(PAD_X + p[0] * (W - 2 * PAD_X), 1),
        round(TOP + p[1] * (BOTTOM - TOP), 1),
    )


def render(res):
    css, body = [], []
    exposed = {b: res.isolated_at(b) for b in res.byzantine}

    for k, (a, b) in enumerate(res.edges):
        cuts = [t for (i, j), t in res.cut_at.items() if {i, j} == {a, b}]
        (x1, y1), (x2, y2) = _xy(res.pos[a]), _xy(res.pos[b])
        if cuts:
            t = min(cuts)
            css.append(
                f"@keyframes e{k}{{0%,{_pct(t - 0.5)}%{{stroke:{EDGE};stroke-opacity:.35}}"
                f"{_pct(t)}%{{stroke:{TRAITOR};stroke-opacity:.9}}"
                f"{_pct(min(t + 6, ROUNDS))}%,100%{{stroke:{TRAITOR};stroke-opacity:.07}}}}"
                f".e{k}{{animation:e{k} {TOTAL:.2f}s linear infinite}}"
            )
            attrs = f'class="e{k}" stroke="{TRAITOR}" stroke-opacity=".07"'
        else:
            attrs = f'stroke="{EDGE}" stroke-opacity=".35"'
        body.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" {attrs} stroke-width="1.4"/>')

    for i, p in enumerate(res.pos):
        x, y = _xy(p)
        frames = [_colour(h[i]) for h in res.history]
        t_exp = exposed.get(i)
        if t_exp is not None:
            frames[t_exp:] = [TRAITOR] * (len(frames) - t_exp)
        stops = f"0%{{fill:{frames[0]}}}" + "".join(f"{_pct(t)}%{{fill:{c}}}" for t, c in enumerate(frames))
        css.append(
            f"@keyframes n{i}{{{stops}100%{{fill:{frames[-1]}}}}}"
            f".n{i}{{animation:n{i} {TOTAL:.2f}s linear infinite}}"
        )
        body.append(f'<circle class="n{i}" cx="{x}" cy="{y}" r="9" fill="{frames[-1]}"/>')
        if t_exp is not None:
            css.append(
                f"@keyframes r{i}{{0%,{_pct(t_exp - 0.5)}%{{opacity:0}}{_pct(t_exp)}%,100%{{opacity:1}}}}"
                f".r{i}{{animation:r{i} {TOTAL:.2f}s linear infinite}}"
            )
            body.append(
                f'<circle class="r{i}" cx="{x}" cy="{y}" r="14" fill="none" '
                f'stroke="{TRAITOR}" stroke-width="2" stroke-dasharray="4 3"/>'
            )

    bar_w = W - 2 * PAD_X
    css.append(
        f"@keyframes bar{{0%,{_pct(0)}%{{transform:scaleX(0)}}{_pct(ROUNDS)}%,100%{{transform:scaleX(1)}}}}"
        f".bar{{transform-box:fill-box;transform-origin:left;animation:bar {TOTAL:.2f}s linear infinite}}"
    )
    legend_y = H - 26
    legend = (
        f'<circle cx="{PAD_X + 6}" cy="{legend_y - 4}" r="6" fill="{_colour(0.5)}"/>'
        f'<text x="{PAD_X + 18}" y="{legend_y}">loyal, colour = plan</text>'
        f'<circle cx="{PAD_X + 190}" cy="{legend_y - 4}" r="6" fill="{TRAITOR}"/>'
        f'<circle cx="{PAD_X + 190}" cy="{legend_y - 4}" r="10" fill="none" stroke="{TRAITOR}" stroke-dasharray="3 2"/>'
        f'<text x="{PAD_X + 208}" y="{legend_y}">traitor, unmasked</text>'
        f'<line x1="{PAD_X + 350}" y1="{legend_y - 4}" x2="{PAD_X + 376}" y2="{legend_y - 4}" stroke="{TRAITOR}" stroke-width="2"/>'
        f'<text x="{PAD_X + 384}" y="{legend_y}">link cut</text>'
        f'<text x="{W - PAD_X}" y="{legend_y}" text-anchor="end">{ROUNDS} gossip rounds</text>'
    )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        f'role="img" aria-label="Byzantine generals gossip simulation for {res.seed_label}">'
        f"<style>{''.join(css)}"
        "text{font:12px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;fill:#8b949e}</style>"
        f'<rect width="{W}" height="{H}" rx="14" fill="#0d1117" stroke="#30363d"/>'
        f"{''.join(body)}"
        f'<rect x="{PAD_X}" y="{H - 58}" width="{bar_w}" height="3" rx="1.5" fill="#21262d"/>'
        f'<rect class="bar" x="{PAD_X}" y="{H - 58}" width="{bar_w}" height="3" rx="1.5" fill="{_colour(0.5)}"/>'
        f"{legend}</svg>\n"
    )
