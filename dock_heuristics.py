"""
Zwei selbst implementierte Heuristiken für das Tor-Zuordnungsproblem (Dock
Door Assignment): jede Relation (Quelle/Ziel-Kombination) muss genau einem
Tor zugeordnet werden, mit dem Ziel, die flussgewichtete Transportdistanz
innerhalb der Halle zu minimieren.

- sequential_assignment: weist Relationen den Toren schlicht in Reihenfolge
  zu (Relation 0 -> Tor 0, Relation 1 -> Tor 1, ...) - repräsentiert eine
  historisch gewachsene bzw. rein nach Ankunftsreihenfolge vergebene
  Zuteilung, ohne Rücksicht auf das tatsächliche Umschlagvolumen. Dient als
  Baseline.

- flow_greedy_assignment: platziert zuerst das umschlagstärkste Relationspaar
  auf das nächstgelegene freie Torpaar, danach jede weitere Relation greedy
  auf das freie Tor mit der geringsten Distanz zu ihrem bereits platzierten
  Flusspartner - ein klassisches Konstruktionsprinzip für das quadratische
  Zuordnungsproblem (QAP), dem das Tor-Zuordnungsproblem entspricht:
  umschlagstarke Relationen bekommen kurze Wege zueinander.

Beide geben ein Array der Länge n_doors zurück: assignment[d] = Index der
Relation, die Tor d zugeordnet ist (eine Permutation von 0..n_doors-1).
"""

import numpy as np


def _pairwise_distances(positions):
    diff = positions[:, None, :] - positions[None, :, :]
    return np.sqrt((diff ** 2).sum(axis=2))


def sequential_assignment(positions, flow):
    """Baseline: Relation i erhält Tor i, unabhängig vom Fluss."""
    n = len(positions)
    return np.arange(n)


def flow_greedy_assignment(positions, flow):
    """Fluss-getriebene Zuordnung: bearbeitet Relationspaare in absteigender
    Flussstärke, platziert noch unplatzierte Paare auf das nächstgelegene
    freie Torpaar und erweitert von bereits platzierten Relationen aus auf
    das jeweils nächstgelegene freie Tor."""
    n = len(positions)
    if n == 0:
        return np.array([], dtype=int)

    door_dist = _pairwise_distances(positions)

    lane_to_door = {}
    free_doors = set(range(n))

    pairs = [(flow[i][j], i, j) for i in range(n) for j in range(i + 1, n) if flow[i][j] > 0]
    pairs.sort(key=lambda t: t[0], reverse=True)

    for _, i, j in pairs:
        i_placed = i in lane_to_door
        j_placed = j in lane_to_door
        if i_placed and j_placed:
            continue

        if not i_placed and not j_placed:
            if len(free_doors) < 2:
                continue
            best = min(
                ((door_dist[d1][d2], d1, d2) for d1 in free_doors for d2 in free_doors if d1 < d2),
                default=None,
            )
            if best is None:
                continue
            _, d1, d2 = best
            lane_to_door[i], lane_to_door[j] = d1, d2
            free_doors -= {d1, d2}
        else:
            new_lane = j if i_placed else i
            if not free_doors:
                continue
            # Bestes freies Tor nach flussgewichteter Distanz zu ALLEN bereits
            # platzierten Relationen, mit denen new_lane Fluss hat - nicht nur
            # zum aktuellen Paarpartner. Ohne diese Korrektur (gefunden beim
            # Benchmarking gegen die Baseline) optimiert die Erweiterung nur
            # lokal für ein einzelnes Paar und kann dabei eine bereits
            # platzierte, noch stärkere Flussbeziehung derselben Relation
            # ignorieren - die Zuordnung schnitt dadurch im Default-Szenario
            # sogar schlechter ab als die naive sequentielle Baseline.
            best_door = min(
                free_doors,
                key=lambda d: sum(
                    flow[new_lane][l] * door_dist[d][ld] for l, ld in lane_to_door.items()
                ),
            )
            lane_to_door[new_lane] = best_door
            free_doors.discard(best_door)

    remaining_lanes = [l for l in range(n) if l not in lane_to_door]
    for lane, door in zip(remaining_lanes, sorted(free_doors)):
        lane_to_door[lane] = door

    assignment = np.zeros(n, dtype=int)
    for lane, door in lane_to_door.items():
        assignment[door] = lane
    return assignment
