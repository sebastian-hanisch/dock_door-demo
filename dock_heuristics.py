"""
Selbst implementierte Verfahren für das Tor-Zuordnungsproblem (Dock Door
Assignment): jede Relation (Quelle/Ziel-Kombination) muss genau einem Tor
zugeordnet werden, mit dem Ziel, die flussgewichtete Transportdistanz
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

- two_opt_improvement: lokale Verbesserung (Pairwise-Exchange) einer
  bestehenden Zuordnung, typischerweise auf das Ergebnis von
  flow_greedy_assignment angewendet - der in der QAP-Praxis übliche zweite
  Schritt nach der Konstruktion (Konstruktion + Verbesserung statt
  Konstruktion allein). Bleibt im ersten gefundenen lokalen Optimum stecken.

Drei Erweiterungen der 2-opt-Nachbarschaft wurden geprüft und wieder
verworfen (Details und Zahlen im README): Iterated Local Search (2-opt +
zufälliges "Schütteln" + Neustarts), eine 3-opt-Nachbarschaft (zyklische
Dreiertausche) und Taillards Robust-Tabu-Search (dieselbe Tausch-
Nachbarschaft wie 2-opt, aber auch verschlechternde Tausche erlaubt, um
lokale Optima zu verlassen). Alle drei brachten in Benchmarks nur
~0,1-1,1 % zusätzliche Verbesserung gegenüber reinem 2-opt (selbst nach
Parameter-Tuning ein klares Plateau), bei 40 Toren oft nahe 0 % - bei
gleichzeitig deutlich höherer Laufzeit. Drei unabhängige Techniken, davon
eine der stärksten QAP-Metaheuristiken der Literatur, die alle an derselben
Grenze scheitern, ist ein starkes Indiz: die 2-opt-Lösung ausgehend von der
Fluss-Konstruktion liegt für diese Art Instanzen bereits nah an einem
starken, vermutlich oft globalen Optimum.

Alle drei geben ein Array der Länge n_doors zurück: assignment[d] = Index
der Relation, die Tor d zugeordnet ist (eine Permutation von 0..n_doors-1).
"""

import numpy as np

from dock_constants import EPS


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


def _swap_delta(assignment, flow, door_dist, a, b):
    """Kostenänderung, wenn die Relationen an Tor a und Tor b getauscht
    würden - ohne den Tausch tatsächlich auszuführen und ohne die
    Gesamtdistanz neu zu berechnen (O(n) statt O(n^2), die inkrementelle
    Standardformel für Paartausch beim QAP, siehe z. B. Taillards
    Robust-Taboo-Search-Arbeit). Negativ = Tausch würde verbessern."""
    lane_a, lane_b = assignment[a], assignment[b]
    delta = 0.0
    for k in range(len(assignment)):
        if k == a or k == b:
            continue
        lane_k = assignment[k]
        delta += (flow[lane_b][lane_k] - flow[lane_a][lane_k]) * (door_dist[a][k] - door_dist[b][k])
    return delta


def two_opt_improvement(positions, flow, assignment, max_passes=200):
    """Lokale Verbesserung (Pairwise-Exchange/"2-opt" fürs QAP) einer
    bestehenden Zuordnung: vertauscht wiederholt die Relationen zweier Tore,
    wenn das die flussgewichtete Gesamtdistanz senkt - je Durchlauf wird das
    beste gefundene Tauschpaar ausgeführt (Steepest Descent), bis kein
    verbessernder Tausch mehr existiert (lokales Optimum) oder max_passes
    erreicht ist (Sicherheitsgrenze gegen Gleitkomma-Zyklen, in der Praxis
    konvergiert es deutlich früher).

    Anders als die Konstruktionsheuristiken kann dieses Verfahren sein
    Startergebnis nie verschlechtern - jeder ausgeführte Tausch senkt die
    Gesamtdistanz garantiert, siehe test_two_opt_never_worsens_the_start."""
    n = len(assignment)
    assignment = np.array(assignment, dtype=int, copy=True)
    if n < 2:
        return assignment

    door_dist = _pairwise_distances(positions)

    for _ in range(max_passes):
        best_delta, best_pair = -EPS, None
        for a in range(n):
            for b in range(a + 1, n):
                delta = _swap_delta(assignment, flow, door_dist, a, b)
                if delta < best_delta:
                    best_delta, best_pair = delta, (a, b)
        if best_pair is None:
            break
        a, b = best_pair
        assignment[a], assignment[b] = assignment[b], assignment[a]

    return assignment
