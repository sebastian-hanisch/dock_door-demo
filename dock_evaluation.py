"""
Bewertet eine Tor-Zuordnung gegen eine Flussmatrix: berechnet die
flussgewichtete Gesamtdistanz und die durchschnittliche Distanz je Bewegung -
die für ein Cross-Dock tatsächlich relevante Kennzahl. Bewusst keine
künstliche €-Umrechnung (anders als bei der Tourenplanung-Demo): kürzere
Wege bedeuten weniger Staplerzeit und höheren Hallendurchsatz, die konkrete
Kostenwirkung hängt stark vom Betrieb ab (Lohnkosten, Schichtmodell,
Flurförderzeug-Typ) und würde hier nur eine Scheingenauigkeit vortäuschen.
"""

import numpy as np


def evaluate_assignment(assignment, positions, flow):
    """Gibt ein Dict zurück: total_weighted_distance (Meter, gewichtet mit
    Bewegungen/Tag, summiert über alle Relationspaare), avg_distance_per_move
    (flussgewichteter Durchschnitt) und total_flow."""
    n = len(assignment)
    if n == 0:
        return {"total_weighted_distance": 0.0, "avg_distance_per_move": 0.0, "total_flow": 0.0}

    door_of_lane = np.zeros(n, dtype=int)
    for door, lane in enumerate(assignment):
        door_of_lane[lane] = door

    total_weighted_distance = 0.0
    total_flow = 0.0
    for i in range(n):
        for j in range(i + 1, n):
            f = float(flow[i][j])
            if f <= 0:
                continue
            di, dj = door_of_lane[i], door_of_lane[j]
            dist = float(np.linalg.norm(positions[di] - positions[dj]))
            total_weighted_distance += f * dist
            total_flow += f

    avg = total_weighted_distance / total_flow if total_flow > 0 else 0.0
    return {
        "total_weighted_distance": total_weighted_distance,
        "avg_distance_per_move": avg,
        "total_flow": total_flow,
    }


def lane_flow_totals(flow):
    """Gesamtes Umschlagvolumen je Relation (Zeilensumme) - ergänzende
    Kennzahl für die Relationsliste."""
    return flow.sum(axis=1)
