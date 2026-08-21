"""
Tor-Zuordnung für die Umschlaghalle (Cross-Dock) – interaktive Demo
Sebastian Hanisch - Operations Research und Machine Learning

Vierte Demo im Portfolio, nach Tourenplanung (VRP), 3D-Packungsoptimierung
und Liniennetz-Design (ÖPNV). Zurück im Kernfeld Fracht-/Logistik (vgl.
Wechselbrücken-Hofmanagement): jede Relation (Quelle/Ziel-Kombination) muss
genau einem Tor zugeordnet werden, mit dem Ziel, die flussgewichtete
Transportdistanz innerhalb der Halle zu minimieren - das klassische Dock
Door Assignment Problem, ein Spezialfall des quadratischen
Zuordnungsproblems (QAP).

Selbe Methodik wie bei den anderen drei Demos: Konstruktionsheuristik +
Bewertung + Vergleich, Ergebnis zuerst ("Ihre optimierte Tor-Zuordnung"),
Methodenvergleich sekundär im Expander.

Lauffähig mit: streamlit run app.py
"""

import pandas as pd
import streamlit as st

from dock_data import generate_doors_and_flow
from dock_evaluation import evaluate_assignment, lane_flow_totals
from dock_feedback import log_feedback
from dock_heuristics import flow_greedy_assignment, sequential_assignment
from dock_pdf_export import generate_assignment_plan_pdf
from dock_presets import apply_preset, bounds, init_session_state_defaults, load_permalink_settings, randomize_seed, sync_query_params
from dock_ui_panel import render_assignment_panel
from dock_visualization import HOT_LANE_CAPTION, LABEL_DENSITY_CAPTION, build_hall_figure

st.set_page_config(page_title="Tor-Zuordnung Umschlaghalle – Sebastian Hanisch", layout="wide")

st.title("🏭 Tor-Zuordnung für die Umschlaghalle")
st.markdown(
    """
Interaktive Demo zur Zuordnung von Relationen (Quelle/Ziel-Kombinationen, z. B. Cross-Dock-
Partner oder Zielgebiete) zu den Toren einer Umschlaghalle. Zwei selbst implementierte Ansätze
– eine **Zuordnung nach Ankunftsreihenfolge** (unabhängig vom Umschlagvolumen, wie es ohne
gezielte Planung häufig entsteht) und eine **fluss-optimierte Zuordnung** (umschlagstarke
Relationen bekommen kurze Wege zueinander) – werden direkt verglichen. Zielgröße ist die
flussgewichtete Transportdistanz innerhalb der Halle: weniger Weg bedeutet weniger Staplerzeit
und mehr Durchsatz pro Schicht. Das zugrunde liegende **Dock Door Assignment Problem** ist ein
Spezialfall des quadratischen Zuordnungsproblems (QAP) und in der Logistik-Literatur gut
dokumentiert – Hintergrund dazu im Expander "Wie funktioniert diese Demo?" unten.
"""
)

st.caption("🎯 Schnellstart – ein Beispielszenario laden:")
preset_col1, preset_col2, preset_col3 = st.columns(3)
with preset_col1:
    st.button(
        "🏬 Kleine Halle", width="stretch",
        on_click=apply_preset, args=(8, 50.0, 20.0, 0.3, 1, 6),
        help="Wenige Tore, Umschlagvolumen eher gleichverteilt über die Relationen.",
    )
with preset_col2:
    st.button(
        "⭐ Hauptpartner-Halle", width="stretch",
        on_click=apply_preset, args=(20, 120.0, 35.0, 0.85, 1, 12),
        help="Ein dominanter Cross-Dock-Partner mit deutlich höherem Umschlagvolumen als alle anderen Relationen.",
    )
with preset_col3:
    st.button(
        "🔀 Mehrere Cross-Dock-Partner", width="stretch",
        on_click=apply_preset, args=(28, 160.0, 40.0, 0.6, 4, 10),
        help="Größere Halle mit mehreren umschlagstarken Relationen statt nur einer.",
    )

st.caption(
    "🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, "
    "um ein Szenario zu teilen."
)

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    n_doors = st.slider(
        "Anzahl Tore", *bounds("n_doors_slider"), key="n_doors_slider",
        help="Gesamtzahl der Tore, gleichmäßig auf zwei gegenüberliegende Hallenwände verteilt "
        "(z. B. Wareneingang/Warenausgang). Genauso viele Relationen wie Tore werden erzeugt - "
        "jede Relation braucht am Ende genau eines.",
    )
    hall_width = st.slider(
        "Hallenlänge (m)", *bounds("hall_width_slider"), step=5.0, key="hall_width_slider",
        help="Ausdehnung der Halle entlang der beiden Torreihen. Bestimmt, wie weit zwei Tore "
        "auf derselben Wand maximal auseinanderliegen können.",
    )
    hall_depth = st.slider(
        "Hallentiefe (m)", *bounds("hall_depth_slider"), step=5.0, key="hall_depth_slider",
        help="Abstand zwischen den beiden gegenüberliegenden Torreihen. Fließt zusammen mit der "
        "Hallenlänge in die Luftlinien-Distanz zwischen zwei Toren ein - je tiefer die Halle, "
        "desto teurer eine Zuordnung, die umschlagstarke Relationen auf gegenüberliegende Wände "
        "verteilt.",
    )

    st.markdown("**Umschlagmuster**")
    flow_concentration = st.slider(
        "Konzentration auf Vorzugsrelationen", *bounds("flow_concentration_slider"), step=0.05,
        key="flow_concentration_slider",
        help="0 = Umschlagvolumen gleichverteilt über alle Relationspaare, 1 = stark auf wenige "
        "umschlagstarke Relationen konzentriert (z. B. ein Großkunde). Je höher der Wert, desto "
        "größer ist in der Regel auch der Vorteil der fluss-optimierten Zuordnung gegenüber der "
        "Baseline, da sich wenige dominante Relationspaare gezielt kurzhalten lassen.",
    )
    n_hot_lanes = st.slider(
        "Anzahl Vorzugsrelationen", *bounds("n_hot_lanes_slider"), key="n_hot_lanes_slider",
        help="Wie viele Relationen von der Konzentration oben betroffen sind. 1 = ein einzelner "
        "dominanter Partner, höhere Werte = mehrere umschlagstarke Relationen gleichzeitig statt "
        "nur einer.",
    )
    seed = st.number_input(
        "Zufalls-Seed", step=1, key="seed_input",
        help="Steuert die Zufallsgenerierung von Torpositionen und Flussmatrix. Gleicher Seed + "
        "gleiche Einstellungen ergeben immer exakt dasselbe Szenario - reproduzierbar und über "
        "die Adresszeile teilbar.",
    )

    st.button(
        "🎲 Neues Szenario generieren", width="stretch", on_click=randomize_seed,
        help="Würfelt einen neuen Zufalls-Seed und erzeugt damit ein komplett neues Szenario - "
        "praktisch, ohne selbst eine neue Seed-Zahl eintippen zu müssen.",
    )

sync_query_params(n_doors, hall_width, hall_depth, flow_concentration, n_hot_lanes, seed)

if "force_regen" not in st.session_state:
    st.session_state.force_regen = False

gen_key = (n_doors, hall_width, hall_depth, flow_concentration, n_hot_lanes, int(seed))
needs_init = (
    "gen_key_cache" not in st.session_state or st.session_state.force_regen
    or st.session_state.get("gen_key_cache") != gen_key
)
if needs_init:
    positions, flow, hot_idxs = generate_doors_and_flow(
        n_doors, int(seed), hall_width=hall_width, hall_depth=hall_depth,
        flow_concentration=flow_concentration, n_hot_lanes=n_hot_lanes,
    )
    st.session_state.positions = positions
    st.session_state.flow = flow
    st.session_state.hot_idxs = hot_idxs
    st.session_state.gen_key_cache = gen_key
    st.session_state.force_regen = False

positions = st.session_state.positions
flow = st.session_state.flow
hot_idxs = st.session_state.hot_idxs
lane_ids = list(range(1, n_doors + 1))

with st.expander("📦 Relationen (nicht editierbar – Umschlagvolumen ist an die Generierung gekoppelt)"):
    totals = lane_flow_totals(flow)
    lanes_df = pd.DataFrame({
        "Relation": lane_ids,
        "Umschlagvolumen (Bew./Tag)": totals.round(0),
        "Vorzugsrelation": ["⭐" if i in hot_idxs else "" for i in range(n_doors)],
    })
    st.dataframe(lanes_df, width="stretch", hide_index=True)

assignment_sequential = sequential_assignment(positions, flow)
assignment_greedy = flow_greedy_assignment(positions, flow)

stats_sequential = evaluate_assignment(assignment_sequential, positions, flow)
stats_greedy = evaluate_assignment(assignment_greedy, positions, flow)

# Beste der beiden Methoden fuer die Primaeransicht: geringere durchschnittliche
# flussgewichtete Distanz je Bewegung gewinnt.
candidates = [
    {"key": "sequential", "label": "Nach Ankunftsreihenfolge", "assignment": assignment_sequential, **stats_sequential},
    {"key": "greedy", "label": "Fluss-optimiert", "assignment": assignment_greedy, **stats_greedy},
]
best = min(candidates, key=lambda c: c["avg_distance_per_move"])
baseline = next(c for c in candidates if c["key"] != best["key"])

st.markdown("## 🎯 Ihre optimierte Tor-Zuordnung")

reduction_pct = 0.0
if baseline["avg_distance_per_move"] > 0:
    reduction_pct = (baseline["avg_distance_per_move"] - best["avg_distance_per_move"]) / baseline["avg_distance_per_move"] * 100

m1, m2 = st.columns(2)
m1.metric(
    "Ø Distanz je Bewegung", f"{best['avg_distance_per_move']:.1f} m",
    delta=f"{-reduction_pct:+.1f}% ggü. Alternative", delta_color="inverse",
)
m2.metric("Gewichtete Gesamtdistanz", f"{best['total_weighted_distance']:.0f} m·Bew./Tag")

if reduction_pct > 1.0:
    st.success(
        f"💡 Mit '{best['label']}' verkürzt sich der durchschnittliche Weg je "
        f"Bewegung um **{reduction_pct:.1f}%** gegenüber '{baseline['label']}' – "
        f"weniger Staplerzeit und mehr Durchsatz bei gleicher Hallengröße."
    )

fig_best = build_hall_figure(positions, best["assignment"], flow, hall_width, hall_depth, hot_idxs)
st.plotly_chart(fig_best, width="stretch", key="primary_best_plot")
st.caption(f"{HOT_LANE_CAPTION} {LABEL_DENSITY_CAPTION}")

pdf_bytes_best = generate_assignment_plan_pdf("Optimierte Zuordnung", best["assignment"], positions, flow)
st.download_button(
    "📄 Tor-Zuordnungsplan als PDF herunterladen", data=pdf_bytes_best,
    file_name="tor_zuordnungsplan_optimiert.pdf", mime="application/pdf", key="primary_pdf_download",
)

st.caption("Ermittelt mit der besseren von zwei eigenen Methoden für dieses Szenario. Details unten.")

st.markdown("---")

with st.expander("🔧 Wie wir das erreichen – vollständiger Methodenvergleich", expanded=False):
    tabs = st.tabs(["🔢 Nach Ankunftsreihenfolge", "📈 Fluss-optimiert", "📊 Vergleich"])

    with tabs[0]:
        st.caption("Relation i erhält Tor i, unabhängig vom Umschlagvolumen - repräsentiert eine ungeplante, historisch gewachsene Zuteilung.")
        summary_sequential = render_assignment_panel("sequential", "Nach Ankunftsreihenfolge", assignment_sequential, positions, flow, hall_width, hall_depth, hot_idxs)

    with tabs[1]:
        st.caption("Platziert umschlagstarke Relationspaare zuerst auf die jeweils nächstgelegenen freien Tore (siehe README für die Details).")
        summary_greedy = render_assignment_panel("greedy", "Fluss-optimiert", assignment_greedy, positions, flow, hall_width, hall_depth, hot_idxs)

    with tabs[2]:
        st.markdown("### Methodenvergleich")

        comp_rows = []
        for c in [summary_sequential, summary_greedy]:
            comp_rows.append({
                "Methode": c["label"],
                "Ø Distanz je Bewegung": f"{c['avg_distance_per_move']:.1f} m",
                "Gewichtete Gesamtdistanz": f"{c['total_weighted_distance']:.0f} m·Bew./Tag",
                "Gesamtvolumen": f"{c['total_flow']:.0f} Bew./Tag",
            })
        st.dataframe(pd.DataFrame(comp_rows), width="stretch", hide_index=True)
        st.caption(
            "Beide Methoden werden mit derselben Bewertungsfunktion gegen dieselbe Flussmatrix "
            "verglichen - fair vergleichbar, auch wenn die Konstruktionsstrategien sehr unterschiedlich sind."
        )

        vis_col1, vis_col2 = st.columns(2)
        with vis_col1:
            st.markdown(f"**{summary_sequential['label']}**")
            fig_compare_sequential = build_hall_figure(positions, assignment_sequential, flow, hall_width, hall_depth, hot_idxs)
            st.plotly_chart(fig_compare_sequential, width="stretch", key="compare_sequential_plot")
        with vis_col2:
            st.markdown(f"**{summary_greedy['label']}**")
            fig_compare_greedy = build_hall_figure(positions, assignment_greedy, flow, hall_width, hall_depth, hot_idxs)
            st.plotly_chart(fig_compare_greedy, width="stretch", key="compare_greedy_plot")
        st.caption(
            "Gleiche Tor-Positionen und Flussmatrix in beiden Grundrissen - nur die Zuordnung von "
            f"Relationen zu Toren unterscheidet sich. {HOT_LANE_CAPTION}"
        )

with st.expander("Wie funktioniert diese Demo?"):
    st.markdown(
        """
**Die Problemstellung:** Jede Relation (Quelle/Ziel-Kombination) muss genau einem Tor
zugeordnet werden, mit dem Ziel, die flussgewichtete Transportdistanz innerhalb der Halle zu
minimieren - das **Dock Door Assignment Problem**, 1976 von Tsui & Chang formal aufgestellt.
Es ist ein Spezialfall des **quadratischen Zuordnungsproblems** (QAP): n Objekte auf n
Standorte verteilen, so dass die Summe aus Fluss × Distanz über alle Paare minimal wird.
Sahni & Gonzalez zeigten im selben Jahr, dass QAP nicht nur NP-schwer ist, sondern - anders
als z. B. das Traveling-Salesman-Problem - auch nicht mit einer garantierten Gütegrenze
effizient approximierbar ist: exakte Lösung ist praktisch nur bis rund 30 Toren machbar,
danach bleiben nur Heuristiken wie die hier gezeigten.

**Warum das praktisch relevant ist:** Torzuordnung wurde vor allem durch **Cross-Docking**
zum Thema - Ware wird direkt vom Eingangs- zum Ausgangs-LKW umgeschlagen, ohne nennenswerte
Zwischenlagerung (von Walmart in den 1980er-Jahren als Supply-Chain-Strategie popularisiert).
Das senkt Lagerkosten drastisch, verschiebt den Engpass aber auf die interne Umschlagdistanz
und -zeit zwischen den Toren - genau die Größe, die diese Demo optimiert.

**Flussmatrix:** Zwischen jedem Relationspaar wird ein (symmetrisches) Umschlagvolumen
(Bewegungen/Tag) generiert. Über den Regler "Konzentration auf Vorzugsrelationen" lässt sich
einstellen, wie stark sich der Umschlag auf wenige besonders umschlagstarke Relationen
konzentriert (z. B. ein Großkunde) statt gleichmäßig verteilt zu sein.

**Nach Ankunftsreihenfolge (Baseline):** Relation i erhält schlicht Tor i - repräsentiert eine
Zuteilung ohne gezielte Planung, wie sie in der Praxis oft historisch entsteht.

**Fluss-optimierte Zuordnung:** Bearbeitet Relationspaare in absteigender Reihenfolge ihres
Umschlagvolumens. Das stärkste noch unplatzierte Paar bekommt das nächstgelegene freie Torpaar,
jede weitere Relation wird greedy auf das freie Tor mit der geringsten flussgewichteten Distanz
zu **allen** bereits platzierten Relationen gesetzt, mit denen sie Fluss hat (nicht nur zum
gerade bearbeiteten Paarpartner) - ein klassisches Konstruktionsprinzip für das QAP.

**Distanz statt Kosten:** Anders als bei der Tourenplanung-Demo (€/h/CO₂) zählt hier die
flussgewichtete Durchschnittsdistanz je Bewegung - bewusst ohne künstliche €-Umrechnung, da die
tatsächliche Kostenwirkung stark vom Betrieb abhängt (Personal, Schichtmodell,
Flurförderzeug-Typ). Kürzere Wege bedeuten in jedem Betrieb weniger Staplerzeit und mehr
Durchsatz.

**Keine Optimalitätsgarantie:** Weil QAP - wie oben beschrieben - nicht garantiert effizient
approximierbar ist, kann die fluss-optimierte Heuristik in einzelnen Szenarien sogar
schlechter abschneiden als die naive Baseline. Im Durchschnitt über viele Zufallsinstanzen
liegt sie deutlich vorn (siehe README), aber anders als etwa beim Sternnetz der
Liniennetz-Design-Demo gibt es hier keine strukturelle Garantie für jeden Einzelfall.

**In echten Projekten** kämen meist weitere Nebenbedingungen dazu (Torkompatibilität für
bestimmte Fahrzeugtypen, Zeitfenster je Relation, mehrere Umschlaghallen-Formen statt der hier
angenommenen zwei gegenüberliegenden Reihen) - das Grundprinzip aus Konstruktion und Bewertung
bleibt aber dasselbe.
"""
    )

st.markdown("---")

st.markdown("#### War diese Demo hilfreich für Sie?")
if st.session_state.get("feedback_given"):
    vote_text = "👍 positiv" if st.session_state["feedback_given"] == "up" else "👎 negativ"
    st.success(f"Danke für Ihr Feedback ({vote_text})! 🙏")
else:
    fb_col1, fb_col2 = st.columns(2)
    with fb_col1:
        if st.button("👍 Ja", key="feedback_up_btn", width="stretch"):
            log_feedback("up")
            st.session_state["feedback_given"] = "up"
            st.rerun()
    with fb_col2:
        if st.button("👎 Nein", key="feedback_down_btn", width="stretch"):
            log_feedback("down")
            st.session_state["feedback_given"] = "down"
            st.rerun()

st.caption(
    "Diese Demo ist Teil des Portfolios von Sebastian Hanisch – Operations Research "
    "und Machine Learning. Interesse an einer maßgeschneiderten Lösung für Ihr "
    "Unternehmen? [Kontakt aufnehmen](#)"
)
