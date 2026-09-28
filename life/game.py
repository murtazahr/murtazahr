"""Conway's Game of Life on a wrap-around grid, run until it dies, freezes or loops."""

from dataclasses import dataclass

MAX_GENERATIONS = 150


@dataclass
class Run:
    rows: int
    cols: int
    generations: list  # generations[g] = frozenset of live (row, col) cells
    outcome: str  # "extinct" | "still" | "loop" | "alive"
    ended_at: int  # generation where the outcome was reached
    period: int = 0  # loop length, when outcome == "loop"


def step(live, rows, cols):
    counts = {}
    for r, c in live:
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr or dc:
                    cell = ((r + dr) % rows, (c + dc) % cols)
                    counts[cell] = counts.get(cell, 0) + 1
    return frozenset(
        cell for cell, n in counts.items() if n == 3 or (n == 2 and cell in live)
    )


def play(seed, rows, cols):
    gens = [frozenset(seed)]
    seen = {gens[0]: 0}
    while len(gens) <= MAX_GENERATIONS:
        nxt = step(gens[-1], rows, cols)
        g = len(gens)
        gens.append(nxt)
        if not nxt:
            return Run(rows, cols, gens, "extinct", g)
        if nxt in seen:
            period = g - seen[nxt]
            if period == 1:
                return Run(rows, cols, gens[:-1], "still", g - 1)
            return Run(rows, cols, gens, "loop", seen[nxt], period)
        seen[nxt] = g
    return Run(rows, cols, gens, "alive", MAX_GENERATIONS)
