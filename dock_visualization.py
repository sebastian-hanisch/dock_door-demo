"""
2D-Hallengrundriss mit Plotly: Tore als Punkte auf den beiden gegenüber-
liegenden Wänden, Flussverbindungen zwischen zugeordneten Relationen als
Linien (Dicke/Deckkraft nach Umschlagvolumen), Tore an Vorzugsrelationen rot
hervorgehoben.

Die Torbeschriftung sitzt als eigene Annotation direkt über bzw. unter jedem
Tor (je nachdem, auf welcher der beiden Hallenwände es liegt), einheitlich im
selben Abstand für alle Tore - kein Zickzack, kein seitlicher Versatz.
Überschneidungen zwischen benachbarten Toren derselben Wand werden
stattdessen allein über die Beschriftungslänge geregelt: bei viel Platz volle
Beschriftung "Tor X (RY)", bei engem Abstand nur noch die Tornummer, bei sehr
engem Abstand gar kein Text mehr auf der Grafik - die vollständige
Information bleibt in jedem Fall über Hover verfügbar.
"""

import plotly.graph_objects as go

from dock_constants import FLOW_COLOR

MAX_FLOWS_DRAWN = 40

# Die y-Achse ist per scaleanchor fest im 1:1-Maßstab an die x-Achse gekoppelt
# (kein Verzerren des Grundrisses) - vorher war die Canvas-Höhe unabhängig
# davon immer 480px fest, was bei extremen Längen-/Tiefe-Verhältnissen zu viel
# Leerraum (breite, flache Halle) oder einem winzig wirkenden Grundriss
# (schmale, tiefe Halle) führte. Jetzt wird die Höhe aus dem tatsächlichen
# Länge/Tiefe-Verhältnis der aktuellen Parameter abgeleitet, mit einer
# angenommenen Canvas-Breite (unterschiedlich für volle Breite vs. die
# nebeneinander stehenden Spalten im Methodenvergleich, je nach Anzahl der
# verglichenen Methoden) und innerhalb sinnvoller Grenzen gekappt.
FULL_WIDTH_PX = 800
THIRD_WIDTH_PX = 250
MIN_HEIGHT_PX = 260
MAX_HEIGHT_PX = 700

# Schwellenwerte für die verfügbaren Pixel je Tor auf der am dichtesten
# besetzten Wand (Canvas-Breite / Toren je Reihe), ab denen die Beschriftung
# verkürzt bzw. ganz ausgeblendet wird. Bewusst in Pixeln statt in Metern
# Torabstand: die Beschriftungsschrift hat eine feste Pixelgröße, ein
# gefundener Fehler bewertete die Crowding-Gefahr vorher rein anhand des
# realen Torabstands in Metern, unabhängig von der tatsächlichen Canvas-
# Breite (volle Breite vs. die schmaleren Spalten im Methodenvergleich) -
# dieselbe Toranzahl konnte dadurch in einer schmalen Spalte trotzdem als
# "full" statt "compact"/"hidden" eingestuft werden und überlappte dort.
LABEL_SPACING_COMPACT_PX = 90.0
LABEL_SPACING_HIDDEN_PX = 40.0

# Senkrechter Abstand der Beschriftung vom Tor in Pixeln, einheitlich für
# alle Tore.
LABEL_OFFSET_PX = 14

# Erklärtext-Bausteine für Captions unter der Grafik - hier statt an jeder
# Aufrufstelle einzeln formuliert, damit z. B. MAX_FLOWS_DRAWN nicht als
# separat gepflegte Zahl im Fließtext veraltet, wenn sich die Konstante
# ändert (an drei Stellen verwendet: primäre Ansicht, Detail-Panel je
# Heuristik, Methodenvergleich).
HOT_LANE_CAPTION = "🔴 Rot markierte Tore bedienen eine der umschlagstärksten Relationen."
FLOW_LINE_CAPTION = (
    f"Linienbreite/-deckkraft nach Umschlagvolumen (stärkste Verbindungen zuerst gezeichnet, "
    f"max. {MAX_FLOWS_DRAWN} dargestellt)."
)
LABEL_DENSITY_CAPTION = (
    "Bei vielen Toren wird die Beschriftung automatisch verkürzt bzw. ausgeblendet - "
    "vollständige Tor-/Relationsnummer immer per Mouseover abrufbar."
)


def _label_plan(positions, width_hint_px=FULL_WIDTH_PX):
    """Bestimmt die Kürzungsstufe der Beschriftung ("full"/"compact"/
    "hidden", einheitlich für die ganze Grafik) anhand der verfügbaren Pixel
    je Tor auf der am dichtesten besetzten Wand (width_hint_px / Toren je
    Reihe) - unabhängig von hall_width, das für die tatsächliche
    Bildschirm-Crowding nichts hergibt (eine physisch breite Halle in einer
    schmalen Spalte ist genauso eng wie eine schmale Halle dort)."""
    n = len(positions)
    if n == 0:
        return "hidden"

    y_vals = positions[:, 1]
    y_min = float(y_vals.min())
    row_a_count = int((y_vals <= y_min + 1e-6).sum())
    row_b_count = n - row_a_count
    spacing_px = width_hint_px / max(row_a_count, row_b_count, 1)

    if spacing_px < LABEL_SPACING_HIDDEN_PX:
        return "hidden"
    elif spacing_px < LABEL_SPACING_COMPACT_PX:
        return "compact"
    return "full"


def _figure_height(hall_width, hall_depth, width_hint_px):
    """Leitet eine zur Halle passende Canvas-Höhe ab, statt einer für alle
    Längen-/Tiefe-Kombinationen fest gleichen Höhe: bei gegebener angenommener
    Breite width_hint_px (voll oder halb, je nach Einbettung) ergibt sich die
    Höhe aus dem tatsächlichen Seitenverhältnis von Länge zu Tiefe (inklusive
    des +20 Randes, den die Achsenbereiche unten dazugeben), gekappt auf ein
    lesbares Minimum/Maximum."""
    x_range = hall_width + 20
    y_range = hall_depth + 20
    height = width_hint_px * (y_range / x_range)
    return max(MIN_HEIGHT_PX, min(MAX_HEIGHT_PX, height))


def build_hall_figure(positions, assignment, flow, hall_width, hall_depth, hot_lane_idxs=None, width_hint_px=FULL_WIDTH_PX):
    fig = go.Figure()
    n = len(positions)

    fig.add_shape(
        type="rect", x0=-5, y0=-5, x1=hall_width + 5, y1=hall_depth + 5,
        line=dict(color="#9ca3af", width=1), fillcolor="rgba(0,0,0,0)",
    )

    # Unsichtbare Eckpunkte statt eines fest vorgegebenen Achsenbereichs:
    # Shapes (siehe oben) fließen nicht zuverlässig in Plotlys automatische
    # Bereichsberechnung ein, Trace-Punkte schon. Damit deckt sich die
    # Rahmung beim ersten Rendern exakt mit dem, was der "Autoscale"-Knopf in
    # der Toolbar sowieso berechnet (der kennt die tatsächliche Canvas-Breite
    # im Browser, ein vorher fest hinterlegter Achsenbereich konnte davon
    # abweichen und wirkte dann - wie vom Nutzer beobachtet - schlechter
    # gerahmt als ein Klick auf "Autoscale").
    fig.add_trace(
        go.Scatter(
            x=[-10, hall_width + 10], y=[-10, hall_depth + 10],
            mode="markers", marker=dict(opacity=0), hoverinfo="skip", showlegend=False,
        )
    )

    if n > 0:
        door_of_lane = [0] * n
        for door, lane in enumerate(assignment):
            door_of_lane[lane] = door

        flows = [(float(flow[i][j]), i, j) for i in range(n) for j in range(i + 1, n) if flow[i][j] > 0]
        flows.sort(key=lambda t: t[0], reverse=True)
        flows = flows[:MAX_FLOWS_DRAWN]
        max_f = flows[0][0] if flows else 1.0
        for f, i, j in flows:
            di, dj = door_of_lane[i], door_of_lane[j]
            width = 1 + 6 * (f / max_f)
            opacity = 0.15 + 0.55 * (f / max_f)
            fig.add_trace(
                go.Scatter(
                    x=[positions[di][0], positions[dj][0]],
                    y=[positions[di][1], positions[dj][1]],
                    mode="lines", line=dict(color=FLOW_COLOR, width=width),
                    opacity=opacity, hoverinfo="skip", showlegend=False,
                )
            )

    hot_lanes = set(int(h) for h in hot_lane_idxs) if hot_lane_idxs is not None else set()
    marker_colors = ["#dc2626" if int(assignment[d]) in hot_lanes else "#374151" for d in range(n)]
    hover_texts = [f"Tor {d + 1}<br>Relation {assignment[d] + 1}" for d in range(n)]

    fig.add_trace(
        go.Scatter(
            x=positions[:, 0] if n else [], y=positions[:, 1] if n else [],
            mode="markers",
            marker=dict(size=12, color=marker_colors, line=dict(width=1, color="white")),
            hovertext=hover_texts, hoverinfo="text", name="Tore", showlegend=False,
        )
    )

    if n > 0:
        y_min = float(positions[:, 1].min())
        level = _label_plan(positions, width_hint_px)
        if level != "hidden":
            font_size = 10 if level == "compact" else 12
            for d in range(n):
                text = str(d + 1) if level == "compact" else f"Tor {d + 1} (R{assignment[d] + 1})"
                outward = -1 if positions[d][1] <= y_min + 1e-6 else 1
                fig.add_annotation(
                    x=positions[d][0], y=positions[d][1], text=text,
                    showarrow=False, yshift=outward * LABEL_OFFSET_PX,
                    font=dict(size=font_size), align="center",
                )

    fig.update_layout(
        xaxis=dict(autorange=True, title="Hallenlänge (m)", zeroline=False),
        yaxis=dict(autorange=True, title="Hallentiefe (m)", zeroline=False, scaleanchor="x"),
        height=_figure_height(hall_width, hall_depth, width_hint_px), margin=dict(l=10, r=10, t=30, b=10),
    )
    # fixedrange auf beiden Achsen: verhindert Pinch-Zoom/Drag-Pan im Chart,
    # damit auf Touch-Geräten stattdessen die Seite normal gescrollt wird
    # (Hover-Tooltips bleiben davon unberührt; autorange oben ist davon
    # unabhängig und bestimmt weiterhin die initiale Rahmung).
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig
