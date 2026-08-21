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
from dock_feedback import get_feedback_counts, log_feedback
from dock_heuristics import flow_greedy_assignment, sequential_assignment, two_opt_improvement
from dock_pdf_export import generate_assignment_plan_pdf
from dock_presets import apply_preset, bounds, init_session_state_defaults, load_permalink_settings, randomize_seed, sync_query_params
from dock_ui_panel import render_assignment_panel
from dock_visualization import FLOW_LINE_CAPTION, HOT_LANE_CAPTION, LABEL_DENSITY_CAPTION, THIRD_WIDTH_PX, build_hall_figure

st.set_page_config(page_title="Tor-Zuordnung Umschlaghalle – Sebastian Hanisch", layout="wide")

st.title("🏭 Tor-Zuordnung für die Umschlaghalle")
st.markdown(
    """
Interaktive Demo zur Zuordnung von Relationen (Quelle/Ziel-Kombinationen, z. B. Cross-Dock-
Partner oder Zielgebiete) zu den Toren einer Umschlaghalle. Drei selbst implementierte
Verfahren – eine **Zuordnung nach Ankunftsreihenfolge** (unabhängig vom Umschlagvolumen, wie es
ohne gezielte Planung häufig entsteht), eine **fluss-optimierte Konstruktion** (umschlagstarke
Relationen bekommen kurze Wege zueinander) und eine **2-opt-Verbesserung** darauf (kann das
Konstruktionsergebnis nur verbessern, nie verschlechtern) – werden direkt verglichen. Zielgröße
ist die flussgewichtete Transportdistanz innerhalb der Halle: weniger Weg bedeutet weniger
Staplerzeit und mehr Durchsatz pro Schicht. Das zugrunde liegende **Dock Door Assignment
Problem** ist ein Spezialfall des quadratischen Zuordnungsproblems (QAP) und in der
Logistik-Literatur gut dokumentiert – Hintergrund dazu im Expander "Wie funktioniert diese
Demo?" unten.
"""
)

st.caption("🎯 Schnellstart – ein Beispielszenario laden:")
preset_col1, preset_col2, preset_col3 = st.columns(3)
with preset_col1:
    st.button(
        "🏬 Kleine Halle", width="stretch",
        on_click=apply_preset, args=({
            "n_doors_slider": 8, "hall_width_slider": 50.0, "hall_depth_slider": 20.0,
            "flow_concentration_slider": 0.3, "n_hot_lanes_slider": 1, "seed_input": 6,
        },),
        help="Wenige Tore, Umschlagvolumen eher gleichverteilt über die Relationen.",
    )
with preset_col2:
    st.button(
        "⭐ Hauptpartner-Halle", width="stretch",
        on_click=apply_preset, args=({
            "n_doors_slider": 20, "hall_width_slider": 120.0, "hall_depth_slider": 35.0,
            "flow_concentration_slider": 0.85, "n_hot_lanes_slider": 1, "seed_input": 12,
        },),
        help="Ein dominanter Cross-Dock-Partner mit deutlich höherem Umschlagvolumen als alle anderen Relationen.",
    )
with preset_col3:
    st.button(
        "🔀 Mehrere Cross-Dock-Partner", width="stretch",
        on_click=apply_preset, args=({
            "n_doors_slider": 28, "hall_width_slider": 160.0, "hall_depth_slider": 40.0,
            "flow_concentration_slider": 0.6, "n_hot_lanes_slider": 4, "seed_input": 10,
        },),
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
    assignment_greedy = flow_greedy_assignment(positions, flow)
    st.session_state.positions = positions
    st.session_state.flow = flow
    st.session_state.hot_idxs = hot_idxs
    # Zuordnungen, Kennzahlen und PDFs mitcachen statt bei jedem Rerun (z. B.
    # Expander auf-/zuklappen, Feedback-Button) neu zu berechnen - bei der
    # Konstruktion vernachlässigbar, bei der 2-opt-Verbesserung (bis zu
    # ~0.8s bei 40 Toren) und beim PDF-Export (4x pro Rerun ohne Cache)
    # sonst spürbar träge.
    st.session_state.assignment_sequential = sequential_assignment(positions, flow)
    st.session_state.assignment_greedy = assignment_greedy
    st.session_state.assignment_two_opt = two_opt_improvement(positions, flow, assignment_greedy)

    st.session_state.stats_sequential = evaluate_assignment(st.session_state.assignment_sequential, positions, flow)
    st.session_state.stats_greedy = evaluate_assignment(assignment_greedy, positions, flow)
    st.session_state.stats_two_opt = evaluate_assignment(st.session_state.assignment_two_opt, positions, flow)

    st.session_state.pdf_sequential = generate_assignment_plan_pdf("Nach Ankunftsreihenfolge", st.session_state.assignment_sequential, positions, flow)
    st.session_state.pdf_greedy = generate_assignment_plan_pdf("Fluss-optimiert", assignment_greedy, positions, flow)
    st.session_state.pdf_two_opt = generate_assignment_plan_pdf("2-opt-verbessert", st.session_state.assignment_two_opt, positions, flow)

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

# Eine einzige Quelle für die drei Methoden statt separater Listen für
# Kandidaten, Tabs und Methodenvergleich - ein früherer Aufbau zählte
# sequential/greedy/two_opt an drei Stellen unabhängig auf, was bei einer
# künftigen vierten Methode drei synchron zu haltende Stellen bedeutet hätte.
methods = [
    {
        "key": "sequential", "label": "Nach Ankunftsreihenfolge", "tab_label": "🔢 Nach Ankunftsreihenfolge",
        "assignment": st.session_state.assignment_sequential, "stats": st.session_state.stats_sequential,
        "pdf": st.session_state.pdf_sequential,
        "intro": "Relation i erhält Tor i, unabhängig vom Umschlagvolumen - repräsentiert eine ungeplante, historisch gewachsene Zuteilung.",
    },
    {
        "key": "greedy", "label": "Fluss-optimiert", "tab_label": "📈 Fluss-optimiert",
        "assignment": st.session_state.assignment_greedy, "stats": st.session_state.stats_greedy,
        "pdf": st.session_state.pdf_greedy,
        "intro": "Platziert umschlagstarke Relationspaare zuerst auf die jeweils nächstgelegenen freien Tore (siehe README für die Details).",
    },
    {
        "key": "two_opt", "label": "2-opt-verbessert", "tab_label": "🔁 2-opt-verbessert",
        "assignment": st.session_state.assignment_two_opt, "stats": st.session_state.stats_two_opt,
        "pdf": st.session_state.pdf_two_opt,
        "intro": (
            "Startet bei der fluss-optimierten Zuordnung und tauscht wiederholt zwei Relationen, "
            "wenn das die Gesamtdistanz senkt, bis keine Verbesserung mehr möglich ist (lokales "
            "Optimum) - anders als die Konstruktion allein kann dieser Schritt das Ergebnis nie "
            "verschlechtern, nur verbessern oder gleich lassen."
        ),
    },
]

# Beste der drei Methoden fuer die Primaeransicht: geringere durchschnittliche
# flussgewichtete Distanz je Bewegung gewinnt. Baseline fuer den Vergleich ist
# immer die naive Zuordnung nach Ankunftsreihenfolge (nicht "die jeweils
# andere Methode") - eindeutig definiert, auch jetzt mit drei Kandidaten.
candidates = [{"key": m["key"], "label": m["label"], "assignment": m["assignment"], **m["stats"]} for m in methods]
best = min(candidates, key=lambda c: c["avg_distance_per_move"])
baseline = next(c for c in candidates if c["key"] == "sequential")

st.markdown("## 🎯 Ihre optimierte Tor-Zuordnung")

reduction_pct = 0.0
if baseline["avg_distance_per_move"] > 0:
    reduction_pct = (baseline["avg_distance_per_move"] - best["avg_distance_per_move"]) / baseline["avg_distance_per_move"] * 100

m1, m2 = st.columns(2)
m1.metric(
    "Ø Distanz je Bewegung", f"{best['avg_distance_per_move']:.1f} m",
    delta=f"{-reduction_pct:+.1f}% ggü. Ankunftsreihenfolge", delta_color="inverse",
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
st.caption(f"{HOT_LANE_CAPTION} {FLOW_LINE_CAPTION} {LABEL_DENSITY_CAPTION}")

# "Optimierte Zuordnung" statt des Methodenlabels, damit der generische
# PDF-Titel unabhängig davon bleibt, welche Methode gerade gewinnt (siehe
# auch die Primäransicht oben, die den Methodennamen bewusst nicht nennt) -
# deshalb per (gen_key, best-Methode) gecacht statt die je-Methode-PDFs aus
# methods[...]['pdf'] wiederzuverwenden, die einen anderen Titel tragen.
best_pdf_cache_key = (gen_key, best["key"])
if st.session_state.get("best_pdf_cache_key") != best_pdf_cache_key:
    st.session_state.pdf_bytes_best = generate_assignment_plan_pdf("Optimierte Zuordnung", best["assignment"], positions, flow)
    st.session_state.best_pdf_cache_key = best_pdf_cache_key
pdf_bytes_best = st.session_state.pdf_bytes_best
st.download_button(
    "📄 Tor-Zuordnungsplan als PDF herunterladen", data=pdf_bytes_best,
    file_name="tor_zuordnungsplan_optimiert.pdf", mime="application/pdf", key="primary_pdf_download",
)

st.caption("Ermittelt mit der besten von drei eigenen Methoden für dieses Szenario. Details unten.")

st.markdown("---")

with st.expander("🔧 Wie wir das erreichen – vollständiger Methodenvergleich", expanded=False):
    tabs = st.tabs([m["tab_label"] for m in methods] + ["📊 Vergleich"])

    summaries = {}
    for m, tab in zip(methods, tabs[:-1]):
        with tab:
            st.caption(m["intro"])
            summaries[m["key"]] = render_assignment_panel(
                m["key"], m["label"], m["assignment"], positions, flow, hall_width, hall_depth, hot_idxs,
                m["stats"], m["pdf"],
            )

    with tabs[-1]:
        st.markdown("### Methodenvergleich")

        comp_rows = [{
            "Methode": summaries[m["key"]]["label"],
            "Ø Distanz je Bewegung": f"{summaries[m['key']]['avg_distance_per_move']:.1f} m",
            "Gewichtete Gesamtdistanz": f"{summaries[m['key']]['total_weighted_distance']:.0f} m·Bew./Tag",
            "Gesamtvolumen": f"{summaries[m['key']]['total_flow']:.0f} Bew./Tag",
        } for m in methods]
        st.dataframe(pd.DataFrame(comp_rows), width="stretch", hide_index=True)
        st.caption(
            "Alle drei Methoden werden mit derselben Bewertungsfunktion gegen dieselbe Flussmatrix "
            "verglichen - fair vergleichbar, auch wenn die Konstruktionsstrategien sehr unterschiedlich sind."
        )

        vis_cols = st.columns(len(methods))
        for col, m in zip(vis_cols, methods):
            with col:
                st.markdown(f"**{summaries[m['key']]['label']}**")
                fig_compare = build_hall_figure(
                    positions, m["assignment"], flow, hall_width, hall_depth, hot_idxs, width_hint_px=THIRD_WIDTH_PX,
                )
                st.plotly_chart(fig_compare, width="stretch", key=f"compare_{m['key']}_plot")
        st.caption(
            "Gleiche Tor-Positionen und Flussmatrix in allen drei Grundrissen - nur die Zuordnung von "
            f"Relationen zu Toren unterscheidet sich. {HOT_LANE_CAPTION} {FLOW_LINE_CAPTION}"
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

**2-opt-Verbesserung:** Startet bei der fluss-optimierten Zuordnung und prüft wiederholt alle
Paare von Toren: würde ein Tausch der beiden zugeordneten Relationen die Gesamtdistanz senken,
wird der bestmögliche gefundene Tausch ausgeführt - so lange, bis kein verbessernder Tausch
mehr existiert (ein lokales Optimum). Das ist der in der QAP-Praxis übliche zweite Schritt nach
der Konstruktion ("Pairwise Exchange"), berechnet über eine inkrementelle Kostenformel, die pro
Tauschkandidat nur die tatsächlich betroffenen Terme neu bewertet statt der gesamten Distanz.

**Distanz statt Kosten:** Anders als bei der Tourenplanung-Demo (€/h/CO₂) zählt hier die
flussgewichtete Durchschnittsdistanz je Bewegung - bewusst ohne künstliche €-Umrechnung, da die
tatsächliche Kostenwirkung stark vom Betrieb abhängt (Personal, Schichtmodell,
Flurförderzeug-Typ). Kürzere Wege bedeuten in jedem Betrieb weniger Staplerzeit und mehr
Durchsatz.

**Optimalitätsgarantie: teilweise, nicht vollständig.** Weil QAP - wie oben beschrieben - nicht
garantiert effizient approximierbar ist, kann die fluss-optimierte Konstruktion in einzelnen
Szenarien sogar schlechter abschneiden als die naive Baseline. Im Durchschnitt über viele
Zufallsinstanzen liegt sie deutlich vorn (siehe README), aber anders als etwa beim Sternnetz
der Liniennetz-Design-Demo gibt es hier keine strukturelle Garantie für jeden Einzelfall. Die
2-opt-Verbesserung hat dagegen eine echte, lokale Garantie: da nur Tausche ausgeführt werden,
die nachweislich verbessern, kann sie ihr Startergebnis nie verschlechtern - nur ein
**globales** Optimum ist damit trotzdem nicht garantiert (ein lokales Optimum muss nicht das
beste aller möglichen Zuordnungen sein).

**In echten Projekten** kämen meist weitere Nebenbedingungen dazu (Torkompatibilität für
bestimmte Fahrzeugtypen, Zeitfenster je Relation, mehrere Umschlaghallen-Formen statt der hier
angenommenen zwei gegenüberliegenden Reihen) - das Grundprinzip aus Konstruktion und Bewertung
bleibt aber dasselbe.
"""
    )

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
Formal ist das Tor-Zuordnungsproblem ein **quadratisches Zuordnungsproblem** (QAP), das
Koopmans & Beckmann 1957 ursprünglich für ein Standortproblem einführten. Gegeben:

- eine Menge von $n$ **Relationen** $R = \{1, \ldots, n\}$
- eine Menge von $n$ **Toren** $D = \{1, \ldots, n\}$
- eine symmetrische **Flussmatrix** $f_{ij} \geq 0$: Umschlagvolumen (Bewegungen/Tag)
  zwischen Relation $i$ und Relation $j$ (`flow` in `dock_data.py`)
- eine symmetrische **Distanzmatrix** $d_{kl} \geq 0$: euklidische Distanz zwischen Tor
  $k$ und Tor $l$ (`_pairwise_distances()` in `dock_heuristics.py`)

Gesucht ist eine bijektive Zuordnung (Permutation) $\pi \in S_n$, die jeder Relation
genau ein Tor zuweist und die flussgewichtete Gesamtdistanz minimiert:
"""
    )
    st.latex(r"\min_{\pi \in S_n} \; \sum_{i=1}^{n} \sum_{j=1}^{n} f_{ij} \cdot d_{\pi(i)\pi(j)}")
    st.markdown(
        r"""
Äquivalent als binäres quadratisches Programm mit Zuordnungsvariablen
$x_{ik} \in \{0, 1\}$ (= 1, wenn Relation $i$ Tor $k$ zugewiesen wird) - die in der
Literatur gebräuchlichere Form:
"""
    )
    st.latex(
        r"\min \; \sum_{i=1}^{n}\sum_{j=1}^{n}\sum_{k=1}^{n}\sum_{l=1}^{n} f_{ij}\, d_{kl}\, x_{ik}\, x_{jl}"
    )
    st.latex(
        r"\text{u. d. N.} \quad \sum_{k=1}^{n} x_{ik} = 1 \;\; \forall i, "
        r"\qquad \sum_{i=1}^{n} x_{ik} = 1 \;\; \forall k, \qquad x_{ik} \in \{0,1\}"
    )
    st.markdown(
        r"""
Die beiden Nebenbedingungen erzwingen genau das, was in der ersten (Permutations-)
Formulierung schon durch die Wahl aus $S_n$ automatisch gilt: jede Relation bekommt
genau ein Tor, jedes Tor genau eine Relation.

**Warum "quadratisch"?** Die Zielfunktion enthält das *Produkt* $x_{ik} \cdot x_{jl}$
zweier Entscheidungsvariablen, nicht wie beim einfacheren linearen Zuordnungsproblem
(LAP) einen festen Koeffizienten pro Variable. Das LAP - "welche Relation bekommt
welches Tor, wenn jede Kombination einen festen, unabhängigen Kostenwert hätte" - löst
der Ungarische Algorithmus in Polynomialzeit exakt. Beim QAP hängt die Kosten-
komponente $d_{kl}$ jeder Zuordnung aber selbst wieder von einer *zweiten*, gleichzeitig
gesuchten Zuordnung ab ($x_{jl}$) - diese Kopplung zweier Variablen im selben Term macht
das Problem NP-schwer (Sahni & Gonzalez 1976 zeigten zusätzlich: nicht einmal mit einer
garantierten Gütegrenze effizient approximierbar, sofern P ≠ NP).

**Fluss-greedy-Konstruktion:** Baut $\pi$ schrittweise auf, in absteigender Reihenfolge der
Flusswerte $f_{ij}$. Sei $P \subset R \times D$ die Menge der bereits fixierten
(Relation, Tor)-Zuordnungen zu einem Zeitpunkt während der Konstruktion und $D_{\text{frei}}$
die Menge der noch freien Tore.

*Start eines neuen Relationspaars* (beide Relationen $i,j$ noch nicht in $P$): wähle das freie
Torpaar mit der geringsten Distanz zueinander,
"""
    )
    st.latex(r"(k^*, l^*) = \arg\min_{k,l \,\in\, D_{\text{frei}},\; k \neq l} d_{kl}")
    st.markdown(
        r"""
und setze $P \leftarrow P \cup \{(i,k^*), (j,l^*)\}$.

*Erweiterung um eine Relation* $j$ (noch nicht in $P$, ihr aktueller Flusspartner schon):
wähle das freie Tor mit der geringsten flussgewichteten Distanz zu **allen** bereits
platzierten Relationen, mit denen $j$ Fluss hat - nicht nur zum aktuellen Paarpartner (siehe
README, Abschnitt "Ein Konstruktionsfehler..." für die dabei gefundene und korrigierte
Schwäche der ersten Version, die genau diese Summe auf einen einzelnen Partner verkürzte),
"""
    )
    st.latex(r"d^*(j) = \arg\min_{d \,\in\, D_{\text{frei}}} \; \sum_{(m,k) \,\in\, P} f_{jm} \cdot d_{d,k}")
    st.markdown(
        r"""
Beide Regeln zusammen ergeben nach $n$ Schritten eine vollständige Permutation $\pi$ - eine
Konstruktionsheuristik im klassischen Sinn: jede Entscheidung wird anhand des aktuellen
Zwischenstands getroffen und danach nie wieder infrage gestellt, anders als die
2-opt-Verbesserung im nächsten Abschnitt, die eine bereits fertige Permutation nachträglich
verbessert.

**Pairwise-Exchange-Nachbarschaft (2-opt):** Ausgehend von einer Permutation $\pi$ lässt sich
durch Vertauschen der Relationen an zwei Toren $a,b$ eine benachbarte Permutation $\pi'$
erzeugen. Mit $\rho = \pi^{-1}$ (welche Relation an Tor $a$ sitzt) lässt sich die
Kostenänderung $\Delta(a,b)$ dieses Tauschs inkrementell berechnen, ohne die Zielfunktion
komplett neu auszuwerten:
"""
    )
    st.latex(
        r"\Delta(a,b) = \sum_{k \neq a,b} \big(f_{\rho(b),\rho(k)} - f_{\rho(a),\rho(k)}\big)"
        r"\big(d_{a,k} - d_{b,k}\big)"
    )
    st.markdown(
        r"""
- $\Delta(a,b) < 0$: der Tausch verbessert die Zuordnung
- Aufwand $O(n)$ je Tauschkandidat statt $O(n^2)$ für eine volle Neubewertung - macht die
  Prüfung aller $\binom{n}{2}$ möglichen Tausche pro Durchlauf ($O(n^3)$ insgesamt) auch bei
  $n=40$ Toren in Bruchteilen einer Sekunde machbar
- die 2-opt-Verbesserung führt wiederholt den besten gefundenen Tausch aus (Steepest Descent),
  bis $\Delta(a,b) \geq 0$ für alle Paare gilt - ein **lokales** Optimum bezüglich dieser
  Nachbarschaftsstruktur, keine Garantie für das globale Optimum

**Bezug zum Code:** `evaluate_assignment()` in `dock_evaluation.py` berechnet exakt die
Zielfunktion von oben (als Summe über $i<j$ statt der vollen Doppelsumme, da $f_{ij}$
symmetrisch ist - ergibt denselben Wert). `flow_greedy_assignment()` in `dock_heuristics.py`
setzt die beiden Konstruktionsregeln von oben um, `_swap_delta()` berechnet
$\Delta(a,b)$ genau wie oben hergeleitet. Alle drei Verfahren konstruieren bzw. verbessern
jeweils eine zulässige Permutation $\pi$, ohne das Problem exakt zu lösen: bei $n=40$ Toren
gäbe es $40! \approx 8 \times 10^{47}$ mögliche Zuordnungen - vollständige Enumeration ist von
vornherein ausgeschlossen.
"""
    )

st.markdown("---")

st.markdown("#### War diese Demo hilfreich für Sie?")
if st.session_state.get("feedback_given"):
    vote_text = "👍 positiv" if st.session_state["feedback_given"] == "up" else "👎 negativ"
    st.success(f"Danke für Ihr Feedback ({vote_text})! 🙏")
    up_count, down_count = get_feedback_counts()
    if up_count + down_count > 0:
        st.caption(f"Bisherige Stimmen: {up_count} 👍 / {down_count} 👎")
elif st.session_state.get("feedback_error"):
    st.warning("⚠️ Ihr Feedback konnte nicht gespeichert werden. Bitte versuchen Sie es später erneut.")
else:
    fb_col1, fb_col2 = st.columns(2)
    with fb_col1:
        if st.button("👍 Ja", key="feedback_up_btn", width="stretch"):
            # Rückgabewert prüfen statt "Danke" blind anzuzeigen: log_feedback
            # fängt Schreibfehler ab (siehe dock_feedback.py, z. B. nicht-
            # persistentes Dateisystem auf Streamlit Community Cloud) und
            # gibt in dem Fall False zurück, ohne eine Exception zu werfen.
            if log_feedback("up"):
                st.session_state["feedback_given"] = "up"
            else:
                st.session_state["feedback_error"] = True
            st.rerun()
    with fb_col2:
        if st.button("👎 Nein", key="feedback_down_btn", width="stretch"):
            if log_feedback("down"):
                st.session_state["feedback_given"] = "down"
            else:
                st.session_state["feedback_error"] = True
            st.rerun()

st.caption(
    "Diese Demo ist Teil des Portfolios von Sebastian Hanisch – Operations Research "
    "und Machine Learning. Interesse an einer maßgeschneiderten Lösung für Ihr "
    "Unternehmen? [Kontakt aufnehmen](#)"
)
