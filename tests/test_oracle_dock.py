"""Unabhängiges Orakel für die Tor-Zuordnung: Vollenumeration aller Permutationen (n <= 6) mit einer eigenen, von evaluate_assignment unabhängigen Kostenformel
(Summe über alle geordneten Paare, halbiert). Geprüft: Bewertung, Optimalitätsschranke der Heuristiken, 2-opt nie schlechter und tauschoptimal (volle Neubewertung statt Delta)."""

import itertools
import math

import numpy as np

from dock_data import generate_doors_and_flow
from dock_evaluation import evaluate_assignment
from dock_heuristics import flow_greedy_assignment, sequential_assignment, two_opt_improvement


def _cost(assignment, positions, flow):
    door = {lane: d for d, lane in enumerate(assignment)}
    n = len(assignment)
    return sum(flow[i][j] * math.dist(positions[door[i]], positions[door[j]]) for i in range(n) for j in range(n) if i != j) / 2


def test_evaluation_heuristics_and_two_opt_against_full_enumeration():
    rng = np.random.default_rng(0)
    for it in range(30):
        n = int(rng.integers(2, 7))
        positions, flow, _ = generate_doors_and_flow(n, it, float(rng.choice([20.0, 100.0])), float(rng.choice([5.0, 30.0])), float(rng.choice([0.0, 0.5, 1.0])), int(rng.integers(0, 4)))
        best = min(_cost(p, positions, flow) for p in itertools.permutations(range(n)))
        greedy = np.asarray(flow_greedy_assignment(positions, flow))
        improved = np.asarray(two_opt_improvement(positions, flow, greedy))
        for a in (sequential_assignment(positions, flow), greedy, improved):
            assert sorted(np.asarray(a).tolist()) == list(range(n))
            c = _cost(a, positions, flow)
            ev = evaluate_assignment(a, positions, flow)
            assert abs(ev["total_weighted_distance"] - c) < 1e-6 * max(1.0, c) and c >= best - 1e-6
            assert abs(ev["total_flow"] - flow[np.triu_indices(n, 1)].sum()) < 1e-9
        assert _cost(improved, positions, flow) <= _cost(greedy, positions, flow) + 1e-6
        for a, b in itertools.combinations(range(n), 2):
            s = improved.copy()
            s[a], s[b] = s[b], s[a]
            assert _cost(s, positions, flow) >= _cost(improved, positions, flow) - 1e-7             # lokales Optimum bezüglich jedes Tauschs
