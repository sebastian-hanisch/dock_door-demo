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
| `dock_heuristics.py` | Sequentielle, fluss-optimierte und 2-opt-verbesserte Tor-Zuordnung |
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
- **Drei eigene Verfahren:**
  - *Nach Ankunftsreihenfolge* (Baseline): Relation i erhält Tor i, unabhängig vom
    Umschlagvolumen - repräsentiert eine ungeplante, historisch gewachsene Zuteilung.
  - *Fluss-optimierte Zuordnung* (Konstruktion): bearbeitet Relationspaare in absteigender
    Flussstärke, platziert das stärkste unplatzierte Paar auf das nächstgelegene freie
    Torpaar und erweitert jede weitere Relation auf das freie Tor mit der geringsten
    flussgewichteten Distanz zu **allen** bereits platzierten Relationen, mit denen sie
    Fluss hat (nicht nur zum aktuellen Paarpartner - siehe Korrektur unten).
  - *2-opt-verbessert* (lokale Suche): startet bei der fluss-optimierten Zuordnung und
    tauscht wiederholt die Relationen zweier Tore, wenn das die Gesamtdistanz senkt, bis
    kein verbessernder Tausch mehr existiert - kann sein Startergebnis dadurch nie
    verschlechtern, siehe Abschnitt unten.
- **Distanz statt Kosten als Kennzahl:** Anders als bei der Tourenplanung-Demo (€/h/CO₂)
  zählt hier die flussgewichtete Durchschnittsdistanz je Bewegung. Bewusst **keine**
  künstliche €-Umrechnung, da die tatsächliche Kostenwirkung stark vom Betrieb abhängt
  (Personal, Schichtmodell, Flurförderzeug-Typ) - kürzere Wege bedeuten aber in jedem Betrieb
  weniger Staplerzeit und mehr Durchsatz.
- **Primäransicht "Ihre optimierte Tor-Zuordnung"** von Anfang an: zeigt die beste der
  drei Methoden direkt, kein Algorithmus-Name in der Überschrift. Vollständiger
  Methodenvergleich liegt im Expander "Wie wir das erreichen".
- **Drei Ein-Klick-Beispielszenarien:** Kleine Halle, Hauptpartner-Halle, Mehrere
  Cross-Dock-Partner.
- **Permalink, Feedback-Mechanismus, PDF-Export:** wie bei den anderen Demos, inklusive
  `SETTING_SPECS`-Muster und NaN/Infinity-Schutz von Anfang an.
- **Mathematische Formulierung als eigener Expander:** formale QAP-Definition (Permutations-
  und binäre Programmform), Herleitung der NP-Schwere über die Kopplung zweier
  Zuordnungsvariablen im selben Term, mit direktem Bezug auf die entsprechenden Funktionen im
  Code.

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

## 2-opt-Verbesserung als drittes Verfahren

Auf Nutzerwunsch ergänzt: eine lokale Suche (Pairwise Exchange, umgangssprachlich "2-opt"),
die auf der fluss-optimierten Zuordnung aufsetzt und wiederholt zwei Tore probeweise tauscht -
wird die flussgewichtete Gesamtdistanz dadurch kleiner, bleibt der Tausch bestehen. Je
Durchlauf wird der beste gefundene Tausch ausgeführt (Steepest Descent), bis keiner mehr
verbessert (ein lokales Optimum).

**Effiziente Umsetzung war hier der eigentliche Punkt.** Eine Kostenänderung naiv durch
volle Neuberechnung der Zielfunktion zu prüfen, kostet $O(n^2)$ je Tauschkandidat - bei
$O(n^2)$ Kandidaten je Durchlauf ergäbe das $O(n^4)$ je Durchlauf, bei 40 Toren spürbar
träge. Stattdessen berechnet `_swap_delta()` in `dock_heuristics.py` die Kostenänderung
inkrementell in $O(n)$ (nur die durch den Tausch tatsächlich betroffenen Terme, Herleitung
im Expander "Mathematische Formulierung" der App) - macht die Prüfung aller
$\binom{n}{2}$ Tauschkandidaten je Durchlauf zu $O(n^3)$. Gemessen bei 40 Toren: **< 1
Sekunde** pro vollständigem Lauf bis zum lokalen Optimum (0,82s im Benchmark), bei den
üblichen 16-28 Toren im Bereich von 20-140ms - interaktiv nutzbar, ohne Caching hätte aber
schon ein einziger Regler-Dreh die App spürbar verzögert. Deshalb werden alle drei
Zuordnungen jetzt (wie Torpositionen/Flussmatrix schon vorher) im Session State
zwischengespeichert und nur bei tatsächlicher Parameteränderung neu berechnet, nicht bei
jedem Rerun (z. B. Auf-/Zuklappen eines Expanders).

**Vor dem Verdrahten gegen eine volle Neuberechnung geprüft:** Für 200 zufällige
Tor-/Tauschkombinationen wurde die inkrementelle Delta-Formel gegen eine komplette
Neubewertung vor/nach dem Tausch abgeglichen (`test_swap_delta_matches_full_recomputation`)
- ein Vorzeichen- oder Indexfehler in so einer Formel fällt sonst oft erst bei bestimmten
Konstellationen auf, nicht beim ersten Test mit "sieht plausibel aus".

**Qualität:** Über 20-Tore-Instanzen liegt die 2-opt-Verbesserung im Schnitt rund 13-17 %
unter der reinen fluss-optimierten Konstruktion (zusätzlich zu deren eigenem Vorsprung
gegenüber der Baseline) - in Summe oft 15-20 % kürzere Wege als "Nach Ankunftsreihenfolge".
Anders als die Konstruktionsheuristiken hat dieses Verfahren eine echte, wenn auch nur
**lokale** Garantie: da ausschließlich nachweislich verbessernde Tausche ausgeführt werden,
kann das Ergebnis nie schlechter sein als der Startpunkt
(`test_two_opt_never_worsens_the_start`) - ein globales Optimum ist damit trotzdem nicht
garantiert.

## Beam-Search-Konstruktion geprüft: besser allein, wirkungslos nach 2-opt

Andere Angriffsrichtung als die drei Erweiterungen unten: nicht "kann man nach der 2-opt-Lösung
noch mehr herausholen", sondern "würde ein besserer Startpunkt *vor* 2-opt am Ende etwas
bringen". Umgesetzt als direkte Verallgemeinerung von `flow_greedy_assignment`: statt bei jedem
Konstruktionsschritt nur die eine beste Erweiterung zu wählen, werden die $k$ besten
Teil-Zuordnungen parallel weiterverfolgt (Beam-Breite $k$), je Schritt um bis zu $m$ Kandidaten
erweitert und wieder auf $k$ beschnitten (reduziert sich bei $k=m=1$ exakt auf
`flow_greedy_assignment` - als Sanity-Check verifiziert).

**Standalone (vor 2-opt), Beam-Breite 8, Branching-Faktor 3:** schlägt reines Greedy deutlich -
+5,7 % bei 16 Toren, **+10,7 % bei 20 Toren**, +1,8 % bei 28, +0,8 % bei 40 Toren. Und praktisch
kostenlos: 4-42ms, gegenüber 2-opts <1s vernachlässigbar.

**Nach angeschlossenem 2-opt auf beiden Startpunkten:** der Vorsprung verdampft fast vollständig
- 0,14 %, 0,05 %, bei 28 und 40 Toren im Schnitt sogar leicht **negativ** (-0,04 % bzw. -0,05 %,
Einzelwerte pendeln zwischen -0,45 % und +0,6 % ohne erkennbare Richtung) - statistisch nicht
mehr von Rauschen unterscheidbar.

**Einordnung:** Vierte unabhängige Bestätigung desselben Musters, diesmal von der anderen
Seite: 2-opt konvergiert unterschiedliche vernünftige Startpunkte offenbar auf praktisch
dieselbe Endqualität - egal ob der Startpunkt aus schwachem oder deutlich besserem Greedy
kommt. Die eigentliche Optimierungsarbeit passiert bei dieser Instanzklasse fast vollständig in
der 2-opt-Phase, nicht in der Konstruktion davor. Code wurde nach dem Benchmark nicht
übernommen (nur dieser Befund).

## Drei geprüfte, aber verworfene Erweiterungen der 2-opt-Nachbarschaft

Auf die Frage "lässt sich die Nachbarschaft noch sinnvoll erweitern?" wurden drei
Standardtechniken implementiert, benchmarkt - und wieder verworfen, weil der Zusatznutzen den
Aufwand nicht rechtfertigt. Alle drei Implementierungen waren korrekt (Delta-/Kostenformeln
jeweils gegen volle Neuberechnung verifiziert), das Ergebnis ist trotzdem ein Minus-Befund -
hier festgehalten, weil er selbst aussagekräftig ist: die 2-opt-Lösung ausgehend von der
Fluss-Konstruktion liegt für diese Art Instanzen (2-Reihen-Halle, euklidische Distanz, das hier
verwendete Flussmuster) offenbar bereits nah an einem starken, oft vermutlich globalen Optimum.

**1. Iterated Local Search** (2-opt bis zum lokalen Optimum, Ergebnis mit ein paar zufälligen
Tauschen "schütteln", erneut 2-opt, über mehrere Neustarts das beste Ergebnis behalten): über
16-40 Tore und mehrere Perturbationsstärken getestet. Schwache Störung (2-3 Tausche) wird von
2-opt fast immer sofort wieder rückgängig gemacht (~0,1-0,2 % Gewinn, auch mit 20 Neustarts
nicht). Starke Störung (n/2 Tausche) findet zwar andere Optima, aber jeder Neustart braucht
dann fast so lange wie eine komplette Neukonvergenz - bei 40 Toren rund 9 Sekunden zusätzlich
für ~0,6 % Gewinn. Bestes gefundenes Verhältnis (mittlere Störung, 8-12 Neustarts): ~0,2-1,1 %
zusätzliche Verbesserung.

**2. 3-opt-Nachbarschaft** (zyklische Dreiertausche - drei Relationen rotieren gemeinsam auf
drei Tore, eine Bewegung, die reines 2-opt strukturell nicht erreichen kann - als
Variable-Neighborhood-Descent mit 2-opt kombiniert): bei 20 Toren im Schnitt **~0,34 %**
zusätzliche Verbesserung (10 von 20 Testinstanzen fanden überhaupt eine, Spanne 0-1,8 %). Bei
40 Toren wird das Verhältnis noch ungünstiger: **~0-0,01 %** Verbesserung bei gleichzeitig
**1,9-3,4 Sekunden** zusätzlicher Laufzeit (2-opt allein: <1s) - dort lohnt sich der Aufwand
praktisch nicht mehr.

**3. Tabu Search** (Taillards Robust-Tabu-Search - dieselbe Tausch-Nachbarschaft wie 2-opt, aber
jede Iteration wird der beste **nicht-tabu** Tausch ausgeführt, auch wenn er kurzfristig
verschlechtert, um aus einem lokalen Optimum herauszukommen; eine Tabu-Liste verhindert das
sofortige Rückgängigmachen, eine Aspirationsregel erlaubt Ausnahmen bei einer neuen
Gesamtbestleistung): die in der QAP-Literatur eigentlich stärkste Metaheuristik, hier gezielt
wegen genau dieser Reputation gewählt. Nach Tuning von Tabu-Länge (3 bis 40) und Iterationszahl
(100 bis 500) bei 20 Toren: Verbesserung **plateaut bei ~1,0-1,1 %** - weder mehr Iterationen
noch eine längere Tabu-Liste bringen darüber hinaus noch etwas, Trefferquote aber deutlich
besser als bei den ersten beiden Techniken (9-10 von 10 Instanzen verbessert statt vereinzelt).
Bei 40 Toren mit Standardparametern **0-0,14 %** Verbesserung in 2,8-2,9s, mit aufgedrehten
Parametern 5,7s für vermutlich ähnlich wenig.

**Konsequenz:** Alle drei Implementierungen wurden wieder entfernt (nicht im Code, um totes
Gewicht zu vermeiden). Dass drei unabhängige Techniken - darunter mit Tabu Search eine der in
der Literatur erfolgreichsten QAP-Metaheuristiken überhaupt - alle an derselben ~1-%-Grenze
scheitern, ist ein deutlich stärkeres Indiz als jeder einzelne Befund für sich: die
2-opt-Lösung ist für diese Instanzklasse bereits sehr nah am Optimum. Die App bleibt bei den
drei Methoden Baseline, Fluss-Greedy-Konstruktion und 2-opt-Verbesserung - das ist für diese
Problemgröße der praktische Sweet Spot.

## Exakte Lösung als Vergleichsmaßstab: machbar, aber nur für sehr kleine Instanzen

Nach vier Befunden, die alle indirekt darauf hindeuten, dass 2-opt bereits nah am Optimum liegt
(ILS, 3-opt, Tabu Search, Beam-Search-Konstruktion - siehe oben), lag die naheliegende Frage
nahe: lässt sich das direkt beweisen, statt nur zu vermuten? Zwei exakte Verfahren wurden dafür
benchmarkt, beide geben garantiert das globale Optimum zurück (keine Heuristik, kein
Approximationsrisiko):

- **Brute-Force** (alle $n!$ Permutationen durchprobieren)
- **Backtracking mit Pruning** (baut die Zuordnung Relation für Relation auf, bricht einen Zweig
  ab, sobald seine bereits fixierten Kosten das bisher beste Ergebnis erreichen oder
  übersteigen - ein beweisbar sicheres Abbruchkriterium, da alle noch fehlenden Kostenbeiträge
  $\geq 0$ sind, also nie das echte Optimum verpasst werden kann)

| Tore | Brute-Force | Backtracking | Ergebnis identisch |
|---|---|---|---|
| 7 | 0,04s | 0,02s | ✓ |
| 8 | 0,38s | 0,25s | ✓ |
| 9 | 4,24s | 1,30s | ✓ |
| 10 | 52,6s | 18,1s | ✓ |

Backtracking gewinnt durchgehend (2-3x schneller bei identischem Ergebnis), aber beide wachsen
erwartungsgemäß faktoriell - bei 11 Toren wären es bereits mehrere Minuten. Der aktuelle
Tore-Regler der App deckt 4 bis 40 Tore ab (Standard 16); exaktes Lösen ist damit nur für einen
kleinen Ausschnitt dieses Bereichs praktikabel (~9 Tore interaktiv, ~10 Tore als Opt-in mit
Wartehinweis) - für den normalen Nutzungsbereich der Demo kein Ersatz für die Heuristiken,
sondern höchstens eine zusätzliche, bedingte Anzeige bei kleinen Szenarien.

**Konsequenz:** Nicht eingebaut (kein zusätzlicher Nutzen für den Aufwand angesichts des engen
anwendbaren Bereichs), aber als Befund festgehalten, weil er die Vermutung der letzten vier
Abschnitte auf den Punkt bringt: Für die kleinen Instanzen, bei denen sich das Optimum
überhaupt beweisen lässt, dürfte 2-opt es typischerweise bereits erreichen oder ihm sehr nahe
kommen - eine direkte, statt nur indizienbasierte, Bestätigung wäre die konsequente nächste
Erweiterung, falls das Thema später doch noch vertieft werden soll (siehe Anpassungsideen).

## Visualisierung: zwei weitere Funde bei der Überarbeitung

**Beschriftung mit hartkodierter Zahl statt Konstante.** Die Caption unter dem Hallengrundriss
nannte an drei Stellen (Primäransicht, Detail-Panel je Heuristik, Methodenvergleich) leicht
unterschiedlich formulierten Text - unter anderem "max. 40 dargestellt" als fest eingetippte
Zahl, obwohl die tatsächliche Grenze über die Konstante `MAX_FLOWS_DRAWN` in
`dock_visualization.py` gesteuert wird. Bei einer künftigen Änderung der Konstante wäre der
Text stillschweigend falsch geworden. Fix: gemeinsame Caption-Bausteine
(`HOT_LANE_CAPTION`, `FLOW_LINE_CAPTION`, `LABEL_DENSITY_CAPTION`), `FLOW_LINE_CAPTION` baut
die Zahl direkt aus `MAX_FLOWS_DRAWN` zusammen. Regressionstest:
`test_flow_line_caption_references_actual_constant_not_hardcoded_number`.

**Canvas-Höhe und Achsenbereich passten sich nicht an die Hallenmaße an.** Ursprünglich war
die Canvas-Höhe unabhängig von Hallenlänge/-tiefe immer fest 480px, bei extremen
Seitenverhältnissen (z. B. 300 m × 10 m) entstand dadurch viel Leerraum. Erster Fix: Höhe wird
aus dem tatsächlichen Längen-/Tiefen-Verhältnis abgeleitet (`_figure_height()`), gekappt auf
260-700px, mit unterschiedlichem Breiten-Hint für volle Breite vs. die nebeneinander
stehenden Grundrisse im Methodenvergleich. Vom Nutzer daraufhin gemeldet: der
"Autoscale"-Knopf in der Plotly-Toolbar fand trotzdem noch eine bessere Darstellung als die
Standardansicht - der fest vorgegebene Achsenbereich (`range=[...]`) basierte auf einer
geschätzten Canvas-Breite, die von der tatsächlichen im Browser abweichen konnte. Zweiter Fix:
`range` entfernt, `autorange=True` gesetzt, dazu zwei unsichtbare Eckpunkte als Trace (Shapes
fließen nicht zuverlässig in die automatische Bereichsberechnung ein). Im Browser mit
`Plotly.relayout()` verifiziert - derselbe Aufruf, den der Autoscale-Button intern macht -:
Achsenbereich vorher/nachher identisch.

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
- Kein Metaheuristik-Verfahren (z. B. Simulated Annealing, Tabu Search) - die 2-opt-Lokal-
  suche (siehe unten) deckt den "Konstruktion + Verbesserung"-Grundgedanken bereits ab,
  ohne die zusätzlichen Parameter (Temperatur, Abkühlplan, Tabu-Länge) einer Metaheuristik
  erklären zu müssen. Ursprünglich war hier bewusst auch gegen ein drittes Verfahren
  entschieden worden ("zwei Methoden mit echtem Charakterunterschied reichen") - auf
  Nutzerwunsch revidiert, siehe Abschnitt "2-opt-Verbesserung als drittes Verfahren".
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

88 Tests, laufen automatisch bei jedem Push/PR über GitHub Actions.

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
- Exakte Lösung als bedingte Zusatzanzeige bei kleinen Szenarien (≤ 9-10 Tore, siehe
  "Exakte Lösung als Vergleichsmaßstab" oben) - würde die bisher nur indirekt gestützte
  Vermutung ("2-opt liegt nah am Optimum") für den Bereich, wo sie sich beweisen lässt, in
  eine harte Kennzahl ("X % vom nachweislichen Optimum entfernt") verwandeln.
- Test an einem echten Mobilgerät.
