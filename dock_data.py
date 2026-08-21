"""
Erzeugt Torpositionen (zwei gegenüberliegende Reihen, wie bei einer typischen
I-förmigen Umschlaghalle: Wareneingang auf der einen, Warenausgang auf der
anderen Seite) sowie eine Flussmatrix zwischen den Relationen (Bewegungen/Tag
pro Relationspaar). Der Fluss ist symmetrisch (flow[i][j] == flow[j][i] -
repräsentiert das aggregierte Tagesumschlagvolumen zwischen zwei Relationen,
unabhängig von der Richtung der einzelnen Bewegung) und kann mehr oder
weniger stark auf einzelne "Vorzugsrelationen" konzentriert sein (z. B. ein
umschlagstarker Cross-Dock-Partner statt gleichverteiltem Fluss über alle
Relationen).
"""

import numpy as np


def generate_doors_and_flow(n_doors, seed, hall_width=100.0, hall_depth=30.0,
                             flow_concentration=0.5, n_hot_lanes=2):
    """Erzeugt n_doors Torpositionen (gleichmäßig auf zwei gegenüberliegenden
    Hallenwänden verteilt) und eine symmetrische Flussmatrix zwischen den
    n_doors Relationen. Jede Relation braucht am Ende genau ein Tor - diese
    Zuordnung berechnen die Heuristiken.

    flow_concentration: 0.0 = Fluss gleichverteilt über alle Relationspaare,
    höhere Werte (bis 1.0) = ein wachsender Anteil des Flusses konzentriert
    sich auf n_hot_lanes besonders umschlagstarke Relationen.

    Gibt (positions, flow, hot_lane_idxs) zurück. positions[d] = (x, y) für
    Tor d. flow[i][i] ist immer 0.
    """
    rng = np.random.default_rng(seed)

    n_row_a = (n_doors + 1) // 2
    n_row_b = n_doors - n_row_a
    xs_a = np.linspace(5, max(5, hall_width - 5), n_row_a) if n_row_a > 0 else np.array([])
    xs_b = np.linspace(5, max(5, hall_width - 5), n_row_b) if n_row_b > 0 else np.array([])

    positions = np.zeros((n_doors, 2))
    positions[:n_row_a, 0] = xs_a
    positions[:n_row_a, 1] = 0.0
    positions[n_row_a:, 0] = xs_b
    positions[n_row_a:, 1] = hall_depth

    base = rng.uniform(1, 10, size=(n_doors, n_doors))
    base = (base + base.T) / 2  # symmetrisch machen

    hot_idxs = np.array([], dtype=int)
    if n_doors > 0 and flow_concentration > 0:
        n_hot_eff = max(1, min(n_hot_lanes, n_doors))
        hot_idxs = rng.choice(n_doors, size=n_hot_eff, replace=False)

    # Boost gilt je Relationspaar (i, j) genau einmal, sobald mindestens eine
    # der beiden Relationen eine Vorzugsrelation ist - nicht additiv/multi-
    # plikativ für Paare, in denen BEIDE Relationen Vorzugsrelationen sind
    # (ein früherer Fehler multiplizierte in diesem Fall zweimal mit boost,
    # da die Schleife über hot_idxs sowohl Zeile als auch Spalte jedes
    # Treffers separat skalierte - bei zwei Vorzugsrelationen ergab das
    # boost² statt boost, siehe README).
    hot_mask = np.zeros(n_doors, dtype=bool)
    hot_mask[hot_idxs] = True
    boost = 1.0 + flow_concentration * 6.0
    multiplier = np.where(hot_mask[:, None] | hot_mask[None, :], boost, 1.0)

    flow = base * multiplier
    np.fill_diagonal(flow, 0.0)
    flow = flow.round(0)
    return positions, flow, hot_idxs
