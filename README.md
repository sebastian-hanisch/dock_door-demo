# Tor-Zuordnung für die Umschlaghalle – Streamlit-Demo

Interaktive Demo zur Zuordnung von Relationen (Quelle/Ziel-Kombinationen, z. B. Cross-Dock-
Partner oder Zielgebiete) zu den Toren einer Umschlaghalle. Vierte Demo im Portfolio für die
Website "Sebastian Hanisch – Operations Research und Machine Learning", nach Tourenplanung
(VRP), 3D-Packungsoptimierung und Liniennetz-Design (ÖPNV) - zurück im dokumentierten
Kernfeld Fracht-/Logistik.

## Das Problem: Dock Door Assignment

Jede Relation muss genau einem Tor zugeordnet werden, mit dem Ziel, die flussgewichtete
Transportdistanz innerhalb der Halle zu minimieren - das klassische **Dock Door Assignment
Problem**, ein Spezialfall des quadratischen Zuordnungsproblems (QAP): n Objekte (Relationen)
auf n Standorte (Tore) verteilen, so dass die Summe aus Fluss × Distanz über alle Paare
minimal wird. In der Fachliteratur gut dokumentiert und praxisrelevant (Umschlagzeit direkt
proportional zur internen Transportstrecke).

## Dateistruktur

Modular wie bei den anderen Demos:

| Datei | Inhalt |
|---|---|
| `app.py` | Streamlit-Hauptablauf (Primäransicht, Sidebar, Detail-Expander) |
| `dock_constants.py` | Konstanten |
| `dock_data.py` | Torpositionen (zwei gegenüberliegende Reihen) + Flussmatrix-Generierung |
| `dock_heuristics.py` | Sequentielle und fluss-optimierte Tor-Zuordnung |
| `dock_evaluation.py` | Bewertung: flussgewichtete Gesamt-/Durchschnittsdistanz |
| `dock_visualization.py` | 2D-Hallengrundriss (Plotly) |
| `dock_pdf_export.py` | PDF-Zuordnungsplan-Erzeugung |
| `dock_feedback.py` | Feedback-Logging |
| `dock_ui_panel.py` | Wiederverwendbares UI-Panel je Heuristik |
| `dock_presets.py` | Beispielszenarien, Permalink-Logik (`SETTING_SPECS`) |

## Funktionsumfang

- **Flussmatrix statt fixer Relationsliste:** Zwischen jedem Relationspaar wird ein
  symmetrisches Umschlagvolumen (Bewegungen/Tag) generiert, konfigurierbar über eine
  "Konzentration auf Vorzugsrelationen" (0 = gleichverteilt, 1 = stark auf wenige
  umschlagstarke Relationen konzentriert - z. B. ein Großkunde/Cross-Dock-Partner).
- **Zwei eigene Heuristiken:**
  - *Nach Ankunftsreihenfolge* (Baseline): Relation i erhält Tor i, unabhängig vom
    Umschlagvolumen - repräsentiert eine ungeplante, historisch gewachsene Zuteilung.
  - *Fluss-optimierte Zuordnung*: bearbeitet Relationspaare in absteigender Flussstärke,
    platziert das stärkste unplatzierte Paar auf das nächstgelegene freie Torpaar und
    erweitert jede weitere Relation auf das freie Tor mit der geringsten flussgewichteten
    Distanz zu **allen** bereits platzierten Relationen, mit denen sie Fluss hat (nicht nur
    zum aktuellen Paarpartner - siehe Korrektur unten).
- **Distanz statt Kosten als Kennzahl:** Anders als bei der Tourenplanung-Demo (€/h/CO₂)
  zählt hier die flussgewichtete Durchschnittsdistanz je Bewegung. Bewusst **keine**
  künstliche €-Umrechnung, da die tatsächliche Kostenwirkung stark vom Betrieb abhängt
  (Personal, Schichtmodell, Flurförderzeug-Typ) - kürzere Wege bedeuten aber in jedem Betrieb
  weniger Staplerzeit und mehr Durchsatz.
- **Primäransicht "Ihre optimierte Tor-Zuordnung"** von Anfang an: zeigt die bessere der
  beiden Methoden direkt, kein Algorithmus-Name in der Überschrift. Vollständiger
  Methodenvergleich liegt im Expander "Wie wir das erreichen".
- **Drei Ein-Klick-Beispielszenarien:** Kleine Halle, Hauptpartner-Halle, Mehrere
  Cross-Dock-Partner.
- **Permalink, Feedback-Mechanismus, PDF-Export:** wie bei den anderen Demos, inklusive
  `SETTING_SPECS`-Muster und NaN/Infinity-Schutz von Anfang an.

## Ein Konstruktionsfehler beim Bauen gefunden - vor Auslieferung durch Benchmarking behoben

Die erste Version der fluss-optimierten Heuristik erweiterte eine bereits begonnene
Zuordnung stets nur anhand der Distanz zum **einen** Relationspartner aus dem gerade
bearbeiteten Paar - nicht anhand der Distanz zu allen bereits platzierten Relationen, mit
denen die neue Relation ebenfalls Fluss hat. Ergebnis bei einer Stichprobenprüfung über 40
Zufallsinstanzen (16 Tore, Standardkonfiguration): im Schnitt zwar **8,6 % kürzere** Wege als
die naive Baseline, aber in einer Instanz (u. a. beim ursprünglich verwendeten Default-Seed
42) schnitt die "optimierte" Methode messbar **schlechter** ab als die Baseline (-0,8 %) -
ein "schlauerer" Ansatz, der lokal optimierte, aber die Gesamtsituation einer Relation nicht
berücksichtigte.

**Fix:** Die Erweiterungsentscheidung minimiert jetzt die flussgewichtete Summe der Distanzen
zu **allen** bereits platzierten Relationen, mit denen die neue Relation Fluss hat, statt nur
zum einzelnen Paarpartner (`flow_greedy_assignment` in `dock_heuristics.py`). Nach dem Fix:
im Schnitt weiterhin rund 8-9 % kürzere Wege, negative Ausreißer deutlich seltener (1 von 40
Stichprobeninstanzen). Dass ein Konstruktionsheuristik-Ansatz nicht in **jeder** Einzelinstanz
garantiert besser abschneidet als eine naive Baseline, ist beim quadratischen
Zuordnungsproblem literaturbekannt (keine Optimalitätsgarantie) - anders als etwa beim
Sternnetz der Liniennetz-Design-Demo, das strukturell immer 0 % unerreichbar liefert.
Getestet in `test_flow_greedy_beats_sequential_on_average` (Durchschnitt über 5 Seeds) und
`test_flow_greedy_places_strongest_pair_at_closest_doors` (handkonstruierter Fall mit
eindeutig bestem Ergebnis).

**Nebeneffekt beim selben Fund:** Der Erfolgstext in der Primäransicht benannte zuvor
hartkodiert immer "fluss-optimierte Tor-Zuordnung" als Gewinner, unabhängig davon, welche der
beiden Methoden für das jeweilige Szenario tatsächlich besser abschnitt (`best['label']` wird
jetzt korrekt eingesetzt statt eines festen Textes) - beim Testen mit dem ursprünglichen
Default-Seed 42 sichtbar geworden, weil dort die Baseline gewann.

## Torgeometrie: zwei gegenüberliegende Reihen

Anders als bei der ursprünglichen Formulierung des Dock-Door-Assignment-Problems (Tore in
einer Linie) bildet diese Demo eine I-förmige Halle nach: Tore gleichmäßig auf zwei
gegenüberliegenden Wänden verteilt (z. B. Wareneingang/Warenausgang), wie es bei vielen
realen Umschlaghallen der Fall ist. Das ändert nichts an der Optimierungslogik (Distanz
zwischen zwei Torpositionen, egal auf welcher Wand), macht den Hallengrundriss aber
realistischer und visuell nachvollziehbarer als eine reine Linienaufstellung.

## Bewusst nicht enthalten (Scope-Entscheidung)

- Keine Torkompatibilität (z. B. bestimmte Tore nur für bestimmte Fahrzeug-/Ladungstypen
  geeignet) - jedes Tor kann jede Relation bedienen.
- Keine Zeitfenster-/Verspätungsplanung (reines Zuordnungsproblem, keine Zeitkomponente -
  das wäre ein eigenständiges Truck-Appointment-Scheduling-Problem, siehe Anpassungsideen).
- Kein drittes/viertes Verfahren (z. B. Local-Search-Verbesserung nach der Konstruktion,
  Simulated Annealing) - zwei Methoden mit echtem Charakterunterschied reichen für die
  Kernaussage.
- Relationen nicht editierbar (Fluss ist an die Generierung gekoppelt), analog zur
  Liniennetz-Design-Demo.

## 1. Lokal ausführen

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

## 2. Tests ausführen

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

64 Tests, laufen automatisch bei jedem Push/PR über GitHub Actions.

## 3. Kostenlos online stellen (Streamlit Community Cloud)

1. Diesen Ordner in ein GitHub-Repository hochladen.
2. Auf [share.streamlit.io](https://share.streamlit.io) anmelden.
3. "New app" → Repository und `app.py` als Hauptdatei → Deploy.

## 4. Anpassungsideen für später

- **Cross-Dock-Routing als natürliche Erweiterung:** Diese Demo löst die Tor-Zuordnung bei
  bereits bekannter, aggregierter Flussmatrix. Ein direkt darauf aufbauendes Folgeproblem ist
  das Cross-Dock-Routing - für jede einzelne Sendung entscheiden, über welches Eingangs- und
  Ausgangstor sie läuft (Konsolidierung mehrerer kleiner Sendungen zu vollen Ladungen). Die
  Tor-Positionen und die Distanzberechnung aus `dock_data.py`/`dock_evaluation.py` wären
  direkt wiederverwendbar; neu wäre eine Sendungsebene unterhalb der Relationsebene und eine
  Konsolidierungslogik (viele Sendungen -> wenige Ausgangstouren). Eher eine fünfte Demo mit
  gemeinsamer Datenbasis als eine Erweiterung dieser hier - andere Kombinatorik (Zuordnung
  vs. Fluss-/Bündelungsproblem).
- Truck-Appointment-Scheduling (Zeitfenster für Ankunft/Abfahrt) als eigenständiges,
  zeitreihenbasiertes Teilproblem - ergänzt die reine Tor-Zuordnung um die Dimension "wann".
- Torkompatibilität (nicht jedes Tor für jede Fahrzeuggröße/Ladungsart geeignet) als
  Nebenbedingung in der Heuristik.
- Test an einem echten Mobilgerät.
