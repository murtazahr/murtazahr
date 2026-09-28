"""A small Byzantine-generals simulation: gossip consensus with hidden traitors.

Honest peers each hold a value in [0, 1] and repeatedly average with their
neighbours. Hidden Byzantine peers send crafted values instead. Every honest
peer screens what it receives against the median of its neighbourhood, keeps a
strike count per neighbour, and permanently cuts a neighbour that is flagged
several rounds in a row. Honest outliers drift back towards the crowd and stop
being flagged; liars keep getting flagged.
"""

import hashlib
import math
import random
import statistics
from dataclasses import dataclass, field

N_PEERS = 28
ROUNDS = 50
RADIUS = 0.36

STRIKES_TO_CUT = 5
WARMUP = 8  # rounds in which outliers are ignored but not yet held against anyone
MAD_SCALE = 3 * 1.4826
MIN_TOLERANCE = 0.06
AGREEMENT = 0.05  # loyal peers within this of the loyal median count as agreeing

ATTACKS = {
    "poison": "sends a fixed extreme value, every round",
    "noise": "sends a fresh random value to each target, every round",
    "drift": "sends the target's own value plus a small bias, hoping to slip under the radar",
}


@dataclass
class Result:
    seed_label: str
    attack: str
    pos: list
    edges: list
    byzantine: set
    history: list  # history[t][i] = value peer i shows at round t
    cut_at: dict = field(default_factory=dict)  # (i, j) -> round i stopped listening to j
    target: float = 0.0

    @property
    def honest(self):
        return [i for i in range(len(self.pos)) if i not in self.byzantine]

    def neighbours(self, i):
        return [b if a == i else a for a, b in self.edges if i in (a, b)]

    def isolated(self, b, at=None):
        """A Byzantine peer is isolated once every honest neighbour has cut it."""
        at = ROUNDS if at is None else at
        return all(
            (h, b) in self.cut_at and self.cut_at[(h, b)] <= at
            for h in self.neighbours(b)
            if h not in self.byzantine
        )

    def isolated_at(self, b):
        hs = [h for h in self.neighbours(b) if h not in self.byzantine]
        if not hs or not self.isolated(b):
            return None
        return max(self.cut_at[(h, b)] for h in hs)

    def false_cuts(self):
        return sum(1 for (i, j) in self.cut_at if j not in self.byzantine)

    def spread(self):
        final = [self.history[-1][i] for i in self.honest]
        return max(final) - min(final)

    def stragglers(self):
        """Loyal peers whose final value is off from the loyal median."""
        final = [self.history[-1][i] for i in self.honest]
        med = statistics.median(final)
        return sum(abs(v - med) > AGREEMENT for v in final)

    def error(self):
        final = [self.history[-1][i] for i in self.honest]
        return abs(statistics.fmean(final) - self.target)


def _rng(label):
    return random.Random(int(hashlib.sha256(label.encode()).hexdigest(), 16))


def _connected(adj, nodes):
    nodes = set(nodes)
    start = next(iter(nodes))
    seen, stack = {start}, [start]
    while stack:
        for n in (adj[stack.pop()] & nodes) - seen:
            seen.add(n)
            stack.append(n)
    return seen == nodes


def _graph(rng):
    """Random geometric graph; resampled until it is connected."""
    while True:
        pos = [(rng.random(), rng.random()) for _ in range(N_PEERS)]
        edges = [
            (i, j)
            for i in range(N_PEERS)
            for j in range(i + 1, N_PEERS)
            if math.dist(pos[i], pos[j]) <= RADIUS
        ]
        adj = {i: set() for i in range(N_PEERS)}
        for a, b in edges:
            adj[a].add(b)
            adj[b].add(a)
        if _connected(adj, range(N_PEERS)):
            return pos, edges, adj


def run(seed_label):
    rng = _rng(seed_label)
    pos, edges, adj = _graph(rng)
    attack = rng.choice(sorted(ATTACKS))
    n_byz = rng.randint(3, 6)
    # Byzantine peers are placed so that fewer than a third of any honest peer's
    # neighbourhood is Byzantine (the classic n > 3f bound for Byzantine
    # agreement), and so that honest peers can still reach each other without
    # relaying through a traitor.
    byzantine = set()
    for cand in rng.sample(range(N_PEERS), N_PEERS):
        if len(byzantine) == n_byz:
            break
        trial = byzantine | {cand}
        if all(
            len(adj[h] & trial) * 3 < len(adj[h]) + 1
            for h in range(N_PEERS)
            if h not in trial
        ) and _connected(adj, set(range(N_PEERS)) - trial):
            byzantine = trial

    values = [rng.uniform(0.1, 0.9) for _ in range(N_PEERS)]
    honest = [i for i in range(N_PEERS) if i not in byzantine]
    target = statistics.fmean(values[i] for i in honest)
    poison = {b: rng.choice([0.0, 1.0]) for b in byzantine}
    bias = {b: rng.choice([-1, 1]) * 0.07 for b in byzantine}

    def message(b, to):
        x = values[to]
        if attack == "poison":
            return poison[b]
        if attack == "noise":
            return rng.random()
        return min(1.0, max(0.0, x + bias[b]))

    strikes = {(i, j): 0 for i in honest for j in adj[i]}
    cut_at = {}
    shown = lambda: [
        values[i] if i not in byzantine else statistics.fmean(message(i, n) for n in adj[i])
        for i in range(N_PEERS)
    ]
    history = [shown()]

    for t in range(1, ROUNDS + 1):
        new = values[:]
        for i in honest:
            inbox = {
                j: (message(j, i) if j in byzantine else values[j])
                for j in adj[i]
                if (i, j) not in cut_at
            }
            pool = [values[i], *inbox.values()]
            med = statistics.median(pool)
            mad = statistics.median(abs(v - med) for v in pool)
            tol = max(MAD_SCALE * mad, MIN_TOLERANCE)
            accepted = [values[i]]
            for j, v in inbox.items():
                if abs(v - med) > tol:
                    strikes[(i, j)] += t > WARMUP
                    if strikes[(i, j)] >= STRIKES_TO_CUT:
                        cut_at[(i, j)] = t
                else:
                    strikes[(i, j)] = 0
                    accepted.append(v)
            new[i] = statistics.fmean(accepted)
        values = new
        history.append(shown())

    return Result(seed_label, attack, pos, edges, byzantine, history, cut_at, target)
