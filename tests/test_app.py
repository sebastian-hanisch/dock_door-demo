"""
Automatisierte Tests für die Tor-Zuordnungs-Demo (Umschlaghalle/Cross-Dock).

Zwei Ebenen, wie bei den anderen Demos:
1. UI-Tests über streamlit.testing.v1.AppTest.
2. Unit-Tests der reinen Logik-Funktionen (normale Imports, da die Logik in
   eigenen Modulen ohne Streamlit-UI-Code liegt).

Ausführen mit: pytest tests/ -v
"""

import os
import sys

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

APP_DIR = os.path.join(os.path.dirname(__file__), "..")
APP_PATH = os.path.join(APP_DIR, "app.py")
TIMEOUT = 90

sys.path.insert(0, os.path.abspath(APP_DIR))


def fresh_app():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=TIMEOUT)
    return at


def assert_ok(at):
    assert not at.exception, f"Unerwartete Exception(s): {[e.message for e in at.exception]}"


# ==========================================================================
# 1. UI-Tests (AppTest)
# ==========================================================================

def test_default_load():
    at = fresh_app()
    assert_ok(at)


def test_math_formulation_expander_present_and_renders():
    at = fresh_app()
    assert_ok(at)
    expander_labels = [e.label for e in at.expander]
    assert any("Mathematische Formulierung" in label for label in expander_labels)


def test_primary_view_shows_two_metrics():
    at = fresh_app()
    assert_ok(at)
    labels = [m.label for m in at.metric[:2]]
    assert labels == ["Ø Distanz je Bewegung", "Gewichtete Gesamtdistanz"]


def test_primary_view_no_algorithm_name_in_headline():
    at = fresh_app()
    assert_ok(at)
    headlines = [str(m.value) for m in at.markdown if "Ihre optimierte Tor-Zuordnung" in str(m.value)]
    assert headlines
    for name in ["Ankunftsreihenfolge", "Fluss-optimiert"]:
        assert name not in headlines[0]


def test_primary_view_method_attribution_in_caption():
    at = fresh_app()
    assert_ok(at)
    captions = [str(c.value) for c in at.caption]
    assert any("drei eigenen Methoden" in c for c in captions)


@pytest.mark.parametrize("label", ["Kleine Halle", "Hauptpartner-Halle", "Mehrere Cross-Dock-Partner"])
def test_presets_apply_without_crash(label):
    at = fresh_app()
    btn = [b for b in at.button if label in b.label][0]
    btn.click().run(timeout=TIMEOUT)
    assert_ok(at)


def test_regenerate_button():
    at = fresh_app()
    seed_before = at.sidebar.number_input(key="seed_input").value
    at.sidebar.button[0].click().run(timeout=TIMEOUT)
    assert_ok(at)
    seed_after = at.sidebar.number_input(key="seed_input").value
    assert seed_after != seed_before, "Seed hat sich durch den Klick nicht geändert"


@pytest.mark.parametrize("slider_idx,value", [(0, 40), (0, 4), (1, 300.0), (2, 10.0)])
def test_slider_extremes(slider_idx, value):
    at = fresh_app()
    at.sidebar.slider[slider_idx].set_value(value).run(timeout=TIMEOUT)
    assert_ok(at)


def test_worst_case_settings_no_crash():
    at = fresh_app()
    at.sidebar.slider[0].set_value(40).run(timeout=TIMEOUT)
    at.sidebar.slider[1].set_value(300.0).run(timeout=TIMEOUT)
    at.sidebar.slider[2].set_value(100.0).run(timeout=TIMEOUT)
    at.sidebar.slider[3].set_value(1.0).run(timeout=TIMEOUT)
    at.sidebar.slider[4].set_value(6).run(timeout=TIMEOUT)
    assert_ok(at)


def test_pdf_download_buttons_present():
    at = fresh_app()
    assert_ok(at)
    labels = [d.label for d in at.download_button]
    assert len(labels) == 4  # Primäransicht + Ankunftsreihenfolge + Fluss-optimiert + 2-opt-verbessert
    assert all("PDF" in l for l in labels)


def test_feedback_buttons_work():
    at = fresh_app()
    up = [b for b in at.button if b.key == "feedback_up_btn"][0]
    up.click().run(timeout=TIMEOUT)
    assert_ok(at)
    assert any("Danke" in str(s.value) for s in at.success)


def test_comparison_tab_has_all_three_methods():
    at = fresh_app()
    assert_ok(at)
    comparison_dfs = [d for d in at.dataframe if "Methode" in d.value.columns]
    assert comparison_dfs
    methods = comparison_dfs[0].value["Methode"].tolist()
    assert "Nach Ankunftsreihenfolge" in methods
    assert "Fluss-optimiert" in methods
    assert "2-opt-verbessert" in methods


def test_permalink_writes_and_restores():
    at = fresh_app()
    assert_ok(at)
    qp = dict(at.query_params)
    for key in ["n_doors", "width", "depth", "flow_conc", "n_hot", "seed"]:
        assert key in qp

    at2 = AppTest.from_file(APP_PATH)
    at2.query_params["n_doors"] = "22"
    at2.run(timeout=TIMEOUT)
    assert_ok(at2)
    assert at2.sidebar.slider[0].value == 22


@pytest.mark.parametrize("param,value", [
    ("n_doors", "9999"), ("n_doors", "-5"), ("width", "9999999"),
    ("flow_conc", "nan"), ("flow_conc", "inf"), ("flow_conc", "-inf"),
    ("seed", "-42"), ("n_hot", "not_a_number"), ("depth", "9999999"),
])
def test_permalink_handles_bad_values_without_crash(param, value):
    at = AppTest.from_file(APP_PATH)
    at.query_params[param] = value
    at.run(timeout=TIMEOUT)
    assert_ok(at)


def test_slider_bounds_match_setting_specs():
    import dock_presets

    at = fresh_app()
    assert_ok(at)
    by_key = {s.key: s for s in at.sidebar.slider if s.key}
    checked = 0
    for state_key, spec in dock_presets.SETTING_SPECS.items():
        if spec.lo is None or state_key not in by_key:
            continue
        slider = by_key[state_key]
        assert slider.min == pytest.approx(spec.lo)
        assert slider.max == pytest.approx(spec.hi)
        checked += 1
    assert checked == 5, f"Nur {checked} von 5 erwarteten Slidern geprüft - Test greift vermutlich nicht vollständig"


def test_setting_specs_defaults_are_within_bounds():
    import dock_presets

    for state_key, spec in dock_presets.SETTING_SPECS.items():
        if spec.lo is not None:
            assert spec.lo <= spec.default <= spec.hi, f"{state_key}: Default außerhalb [{spec.lo},{spec.hi}]"


def test_permalink_url_params_are_unique():
    import dock_presets

    params = [spec.url_param for spec in dock_presets.SETTING_SPECS.values()]
    assert len(params) == len(set(params))


# ==========================================================================
# 2. Unit-Tests der reinen Funktionen
# ==========================================================================

from dock_data import generate_doors_and_flow
from dock_evaluation import evaluate_assignment, lane_flow_totals
from dock_heuristics import _pairwise_distances, _swap_delta, flow_greedy_assignment, sequential_assignment, two_opt_improvement


def test_generate_doors_and_flow_shapes_and_symmetry():
    positions, flow, hots = generate_doors_and_flow(15, seed=1)
    assert positions.shape == (15, 2)
    assert flow.shape == (15, 15)
    assert np.allclose(flow, flow.T)
    assert np.allclose(np.diag(flow), 0)


def test_generate_doors_and_flow_two_opposite_rows():
    """Tore müssen auf zwei unterschiedlichen y-Werten liegen (zwei
    gegenüberliegende Hallenwände), nicht auf einer Linie."""
    positions, flow, hots = generate_doors_and_flow(10, seed=1, hall_depth=30.0)
    y_values = set(positions[:, 1].round(3))
    assert y_values == {0.0, 30.0}


def test_generate_doors_and_flow_concentration_effect():
    """Höhere flow_concentration sollte einen größeren Anteil des Flusses auf
    die Vorzugsrelationen konzentrieren."""
    _, flow_low, hots_low = generate_doors_and_flow(20, seed=1, flow_concentration=0.0, n_hot_lanes=2)
    _, flow_high, hots_high = generate_doors_and_flow(20, seed=1, flow_concentration=0.9, n_hot_lanes=2)

    def hot_share(flow, hots):
        total = flow.sum()
        hot_total = flow[hots, :].sum() + flow[:, hots].sum() - flow[hots][:, hots].sum()
        return hot_total / total if total > 0 else 0

    assert hot_share(flow_high, hots_high) > hot_share(flow_low, hots_low)


def test_generate_doors_and_flow_n_hot_exceeds_n_doors_handled():
    positions, flow, hots = generate_doors_and_flow(3, seed=1, n_hot_lanes=10)
    assert len(hots) <= 3


def test_generate_doors_and_flow_zero_doors_no_crash():
    positions, flow, hots = generate_doors_and_flow(0, seed=1)
    assert positions.shape == (0, 2)
    assert flow.shape == (0, 0)


# --- Bewertungslogik: handkonstruierte Fälle mit bekanntem Ergebnis ---

def test_evaluate_assignment_hand_constructed():
    """assignment[door] = lane. Tore auf einer Linie bei x=0,10,20,30."""
    positions = np.array([[0.0, 0.0], [10.0, 0.0], [20.0, 0.0], [30.0, 0.0]])
    flow = np.zeros((4, 4))
    flow[0][1] = flow[1][0] = 5   # Relation 0<->1
    flow[0][2] = flow[2][0] = 2   # Relation 0<->2
    assignment = np.array([0, 1, 2, 3])  # identisch: Relation i -> Tor i

    result = evaluate_assignment(assignment, positions, flow)
    # dist(0,1)=10, dist(0,2)=20 -> 5*10 + 2*20 = 90
    assert result["total_weighted_distance"] == pytest.approx(90.0)
    assert result["total_flow"] == pytest.approx(7.0)
    assert result["avg_distance_per_move"] == pytest.approx(90.0 / 7.0)


def test_evaluate_assignment_respects_permutation_not_identity():
    """Bei vertauschter Zuordnung muss die tatsächliche Torposition der
    Relation verwendet werden, nicht der Relationsindex."""
    positions = np.array([[0.0, 0.0], [100.0, 0.0]])
    flow = np.zeros((2, 2))
    flow[0][1] = flow[1][0] = 3
    assignment = np.array([1, 0])  # Tor 0 -> Relation 1, Tor 1 -> Relation 0

    result = evaluate_assignment(assignment, positions, flow)
    assert result["total_weighted_distance"] == pytest.approx(3 * 100.0)


def test_evaluate_assignment_zero_flow_no_crash():
    positions = np.zeros((3, 2))
    result = evaluate_assignment(np.array([0, 1, 2]), positions, np.zeros((3, 3)))
    assert result["total_flow"] == 0
    assert result["avg_distance_per_move"] == 0


def test_evaluate_assignment_empty_no_crash():
    result = evaluate_assignment(np.array([]), np.zeros((0, 2)), np.zeros((0, 0)))
    assert result["total_weighted_distance"] == 0


def test_lane_flow_totals():
    flow = np.array([[0, 3, 5], [3, 0, 2], [5, 2, 0]])
    totals = lane_flow_totals(flow)
    assert list(totals) == [8, 5, 7]


# --- Heuristiken: strukturelle Korrektheit ---

def _validate_permutation(assignment, n):
    assert len(assignment) == n
    assert sorted(int(a) for a in assignment) == list(range(n))


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
@pytest.mark.parametrize("heuristic", [sequential_assignment, flow_greedy_assignment])
def test_heuristics_produce_valid_permutations(heuristic, seed):
    positions, flow, hots = generate_doors_and_flow(20, seed=seed, flow_concentration=0.6, n_hot_lanes=2)
    assignment = heuristic(positions, flow)
    _validate_permutation(assignment, 20)


def test_heuristics_handle_zero_doors():
    positions, flow, hots = generate_doors_and_flow(0, seed=1)
    assert len(sequential_assignment(positions, flow)) == 0
    assert len(flow_greedy_assignment(positions, flow)) == 0


def test_heuristics_handle_single_door():
    positions, flow, hots = generate_doors_and_flow(1, seed=1)
    assert list(sequential_assignment(positions, flow)) == [0]
    assert list(flow_greedy_assignment(positions, flow)) == [0]


def test_flow_greedy_places_strongest_pair_at_closest_doors():
    """Kerneigenschaft der Fluss-Heuristik, an einem handkonstruierten Fall
    mit eindeutig bestem Ergebnis geprüft: Tore 0 und 1 liegen am nächsten
    beieinander (Distanz 1), Tor 2 ist weit entfernt. Die mit Abstand
    stärkste Relationsbeziehung muss auf das nahe Torpaar fallen."""
    positions = np.array([[0.0, 0.0], [1.0, 0.0], [1000.0, 0.0], [1001.0, 0.0]])
    flow = np.zeros((4, 4))
    flow[0][1] = flow[1][0] = 100  # staerkste Relation
    flow[2][3] = flow[3][2] = 1
    flow[0][2] = flow[2][0] = 1

    assignment = flow_greedy_assignment(positions, flow)
    door_of_lane = {lane: door for door, lane in enumerate(assignment)}
    doors_of_strong_pair = {door_of_lane[0], door_of_lane[1]}
    assert doors_of_strong_pair == {0, 1}


def test_flow_greedy_beats_sequential_on_average(seed_range=range(1, 6)):
    """Qualitäts-Sanity-Check: über mehrere Instanzen sollte die
    fluss-optimierte Zuordnung im Schnitt eine geringere durchschnittliche
    Distanz je Bewegung liefern als die Zuordnung nach Ankunftsreihenfolge -
    das ist ihr eigentlicher Daseinszweck."""
    deltas = []
    for seed in seed_range:
        positions, flow, hots = generate_doors_and_flow(20, seed=seed, flow_concentration=0.6, n_hot_lanes=2)
        seq = sequential_assignment(positions, flow)
        greedy = flow_greedy_assignment(positions, flow)
        avg_seq = evaluate_assignment(seq, positions, flow)["avg_distance_per_move"]
        avg_greedy = evaluate_assignment(greedy, positions, flow)["avg_distance_per_move"]
        deltas.append(avg_seq - avg_greedy)
    assert sum(deltas) / len(deltas) > 0.0


def test_flow_greedy_all_zero_flow_falls_back_to_valid_permutation():
    positions, flow, hots = generate_doors_and_flow(10, seed=1, flow_concentration=0.0)
    flow = np.zeros_like(flow)
    assignment = flow_greedy_assignment(positions, flow)
    _validate_permutation(assignment, 10)


# --- 2-opt-Verbesserung ---

def test_swap_delta_matches_full_recomputation():
    """Kernkorrektheitstest der inkrementellen Delta-Formel: für viele
    zufällige Instanzen und Tauschkandidaten muss die vorhergesagte
    Kostenänderung exakt mit einer vollständigen Neuberechnung vor/nach dem
    Tausch übereinstimmen. Ein Vorzeichen- oder Indexfehler in dieser Formel
    würde sonst nur bei bestimmten Konstellationen auffallen."""
    rng = np.random.default_rng(0)
    for trial in range(50):
        n = int(rng.integers(2, 10))
        positions, flow, hots = generate_doors_and_flow(n, seed=trial, flow_concentration=0.5, n_hot_lanes=2)
        assignment = rng.permutation(n)
        door_dist = _pairwise_distances(positions)
        a, b = sorted(int(x) for x in rng.choice(n, size=2, replace=False))

        cost_before = evaluate_assignment(assignment, positions, flow)["total_weighted_distance"]
        predicted_delta = _swap_delta(assignment, flow, door_dist, a, b)

        swapped = assignment.copy()
        swapped[a], swapped[b] = swapped[b], swapped[a]
        cost_after = evaluate_assignment(swapped, positions, flow)["total_weighted_distance"]

        assert predicted_delta == pytest.approx(cost_after - cost_before, abs=1e-6)


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_two_opt_produces_valid_permutation(seed):
    positions, flow, hots = generate_doors_and_flow(20, seed=seed, flow_concentration=0.6, n_hot_lanes=2)
    start = flow_greedy_assignment(positions, flow)
    improved = two_opt_improvement(positions, flow, start)
    _validate_permutation(improved, 20)


@pytest.mark.parametrize("seed", range(1, 11))
def test_two_opt_never_worsens_the_start(seed):
    """Die zentrale Garantie der 2-opt-Verbesserung (anders als bei den
    Konstruktionsheuristiken, die im Schnitt, aber nicht garantiert besser
    sind): da nur nachweislich verbessernde Tausche ausgeführt werden, darf
    das Ergebnis nie schlechter sein als der Startpunkt."""
    positions, flow, hots = generate_doors_and_flow(20, seed=seed, flow_concentration=0.6, n_hot_lanes=2)
    start = flow_greedy_assignment(positions, flow)
    improved = two_opt_improvement(positions, flow, start)
    cost_start = evaluate_assignment(start, positions, flow)["total_weighted_distance"]
    cost_improved = evaluate_assignment(improved, positions, flow)["total_weighted_distance"]
    assert cost_improved <= cost_start + 1e-6


def test_two_opt_actually_improves_a_hand_constructed_case():
    """Handkonstruierter Fall mit einer eindeutig verbessernden Vertauschung:
    Relation 0 und 1 haben starken Fluss, sitzen aber (bewusst suboptimal)
    an weit entfernten Toren; 2-opt muss das erkennen und tauschen. Tor 0/1
    liegen näher beieinander (Distanz 1) als Tor 2/3 (Distanz 10), damit das
    beste Torpaar für die starke Relation eindeutig ist (keine symmetrische
    Alternative mit gleichen Kosten)."""
    positions = np.array([[0.0, 0.0], [1.0, 0.0], [1000.0, 0.0], [1010.0, 0.0]])
    flow = np.zeros((4, 4))
    flow[0][1] = flow[1][0] = 100
    start = np.array([0, 2, 3, 1])  # Relation 0 an Tor 0, Relation 1 an Tor 3 - weit auseinander

    improved = two_opt_improvement(positions, flow, start)
    door_of_lane = {lane: door for door, lane in enumerate(improved)}
    assert {door_of_lane[0], door_of_lane[1]} == {0, 1}

    cost_start = evaluate_assignment(start, positions, flow)["total_weighted_distance"]
    cost_improved = evaluate_assignment(improved, positions, flow)["total_weighted_distance"]
    assert cost_improved < cost_start


def test_two_opt_is_idempotent_at_a_local_optimum():
    """Ein bereits lokal optimales Ergebnis darf durch einen erneuten Lauf
    nicht mehr verändert werden - sonst wäre die Abbruchbedingung fehlerhaft."""
    positions, flow, hots = generate_doors_and_flow(15, seed=3, flow_concentration=0.6, n_hot_lanes=2)
    once = two_opt_improvement(positions, flow, flow_greedy_assignment(positions, flow))
    twice = two_opt_improvement(positions, flow, once)
    assert list(once) == list(twice)


def test_two_opt_beats_greedy_alone_on_average(seed_range=range(1, 6)):
    """Qualitäts-Sanity-Check analog zu test_flow_greedy_beats_sequential_on_
    average: die 2-opt-Verbesserung soll im Schnitt spürbar über die reine
    Konstruktion hinauskommen - das ist ihr eigentlicher Daseinszweck."""
    deltas = []
    for seed in seed_range:
        positions, flow, hots = generate_doors_and_flow(20, seed=seed, flow_concentration=0.6, n_hot_lanes=2)
        greedy = flow_greedy_assignment(positions, flow)
        improved = two_opt_improvement(positions, flow, greedy)
        avg_greedy = evaluate_assignment(greedy, positions, flow)["avg_distance_per_move"]
        avg_improved = evaluate_assignment(improved, positions, flow)["avg_distance_per_move"]
        deltas.append(avg_greedy - avg_improved)
    assert sum(deltas) / len(deltas) > 0.0


def test_two_opt_handles_zero_and_one_door():
    for n in (0, 1):
        positions, flow, hots = generate_doors_and_flow(n, seed=1)
        start = sequential_assignment(positions, flow)
        improved = two_opt_improvement(positions, flow, start)
        _validate_permutation(improved, n)


# --- Visualisierung: Beschriftungslogik ---
# Keine dieser Funktionen war zuvor getestet, obwohl die Beschriftung
# (_label_plan, Zickzack-Entfernung, Captions) über mehrere Anfragen hinweg
# mehrfach umgebaut wurde - hier nachgeholt, um Regressionen bei künftigen
# Anpassungen frühzeitig zu erkennen.

from dock_visualization import FLOW_LINE_CAPTION, MAX_FLOWS_DRAWN, _label_plan, build_hall_figure


def _two_row_positions(n_per_row, hall_width, hall_depth=30.0):
    xs = np.linspace(5, hall_width - 5, n_per_row)
    row_a = [[x, 0.0] for x in xs]
    row_b = [[x, hall_depth] for x in xs]
    return np.array(row_a + row_b)


def test_label_plan_empty_is_hidden():
    assert _label_plan(np.zeros((0, 2)), hall_width=100.0) == "hidden"


def test_label_plan_full_when_spacious():
    positions = _two_row_positions(n_per_row=2, hall_width=100.0)  # 50 m Torabstand je Reihe
    assert _label_plan(positions, hall_width=100.0) == "full"


def test_label_plan_compact_when_tight():
    positions = _two_row_positions(n_per_row=2, hall_width=20.0)  # 10 m Torabstand je Reihe
    assert _label_plan(positions, hall_width=20.0) == "compact"


def test_label_plan_hidden_when_very_tight():
    positions = _two_row_positions(n_per_row=2, hall_width=8.0)  # 4 m Torabstand je Reihe
    assert _label_plan(positions, hall_width=8.0) == "hidden"


def test_build_hall_figure_annotation_count_matches_label_plan():
    n = 4
    positions = _two_row_positions(n_per_row=2, hall_width=100.0)
    flow = np.zeros((n, n))
    assignment = np.arange(n)

    fig_full = build_hall_figure(positions, assignment, flow, hall_width=100.0, hall_depth=30.0)
    assert len(fig_full.layout.annotations) == n

    fig_hidden = build_hall_figure(positions, assignment, flow, hall_width=8.0, hall_depth=30.0)
    assert len(fig_hidden.layout.annotations) == 0


def test_build_hall_figure_labels_point_outward_from_hall():
    """Regressionstest: Tore an der unteren Wand (y=0) müssen ihr Label nach
    unten bekommen (negativer yshift), Tore an der oberen Wand (y=Tiefe) nach
    oben (positiver yshift) - nie ins Halleninnere hinein, wo sich die
    Flusslinien befinden."""
    positions = _two_row_positions(n_per_row=2, hall_width=100.0, hall_depth=30.0)
    n = len(positions)
    fig = build_hall_figure(positions, np.arange(n), np.zeros((n, n)), hall_width=100.0, hall_depth=30.0)

    for ann in fig.layout.annotations:
        if ann.y <= 1e-6:
            assert ann.yshift < 0
        else:
            assert ann.yshift > 0


def test_build_hall_figure_handles_zero_and_one_door():
    for n in (0, 1):
        positions, flow, hots = generate_doors_and_flow(n, seed=1)
        assignment = sequential_assignment(positions, flow)
        fig = build_hall_figure(positions, assignment, flow, hall_width=100.0, hall_depth=30.0, hot_lane_idxs=hots)
        assert len(fig.layout.annotations) <= n


def test_figure_height_adapts_to_hall_aspect_ratio():
    """Regressionstest: die Canvas-Höhe war zuvor unabhängig vom Länge/Tiefe-
    Verhältnis der Halle immer fest 480px - eine breite, flache Halle bekommt
    jetzt eine spürbar geringere Höhe als eine schmale, tiefe."""
    from dock_visualization import _figure_height

    wide_shallow = _figure_height(hall_width=300.0, hall_depth=10.0, width_hint_px=800)
    default_ish = _figure_height(hall_width=100.0, hall_depth=30.0, width_hint_px=800)
    narrow_deep = _figure_height(hall_width=30.0, hall_depth=100.0, width_hint_px=800)
    assert wide_shallow < default_ish < narrow_deep


def test_figure_height_stays_within_bounds():
    from dock_visualization import MAX_HEIGHT_PX, MIN_HEIGHT_PX, _figure_height

    very_flat = _figure_height(hall_width=300.0, hall_depth=10.0, width_hint_px=800)
    very_tall = _figure_height(hall_width=30.0, hall_depth=100.0, width_hint_px=800)
    assert MIN_HEIGHT_PX <= very_flat <= MAX_HEIGHT_PX
    assert MIN_HEIGHT_PX <= very_tall <= MAX_HEIGHT_PX


def test_figure_height_smaller_width_hint_gives_smaller_height():
    """Die Vergleichsansicht rendert zwei Grundrisse nebeneinander (halbe
    Breite) - bei gleichem Hallen-Seitenverhältnis muss der width_hint_px-
    Parameter das direkt in eine kleinere Höhe übersetzen, sonst wäre der
    Halb-Spalten-Grundriss unnötig hoch/gestaucht."""
    from dock_visualization import HALF_WIDTH_PX, _figure_height

    full = _figure_height(hall_width=100.0, hall_depth=30.0, width_hint_px=800)
    half = _figure_height(hall_width=100.0, hall_depth=30.0, width_hint_px=HALF_WIDTH_PX)
    assert half < full


def test_flow_line_caption_references_actual_constant_not_hardcoded_number():
    """Regressionstest für einen gefundenen Bug: die Caption enthielt an
    mehreren Stellen den hartkodierten Text 'max. 40 dargestellt', obwohl die
    tatsächliche Grenze über MAX_FLOWS_DRAWN definiert ist - bei einer
    künftigen Änderung der Konstante wäre der Text stillschweigend falsch
    geworden. Jetzt aus der Konstante zusammengesetzt."""
    assert f"max. {MAX_FLOWS_DRAWN} dargestellt" in FLOW_LINE_CAPTION


# --- PDF-Export ---

def test_generate_assignment_plan_pdf_produces_valid_pdf():
    from dock_pdf_export import generate_assignment_plan_pdf

    positions, flow, hots = generate_doors_and_flow(12, seed=2)
    assignment = flow_greedy_assignment(positions, flow)
    pdf_bytes = generate_assignment_plan_pdf("Test", assignment, positions, flow)
    assert pdf_bytes[:4] == b"%PDF"
    assert len(pdf_bytes) > 500


# --- Feedback ---

def test_feedback_log_and_count_roundtrip(tmp_path):
    from dock_feedback import get_feedback_counts, log_feedback

    log_file = str(tmp_path / "feedback_test.csv")
    assert get_feedback_counts(log_file) == (0, 0)
    assert log_feedback("up", log_file) is True
    assert log_feedback("down", log_file) is True
    assert log_feedback("up", log_file) is True
    assert get_feedback_counts(log_file) == (2, 1)
