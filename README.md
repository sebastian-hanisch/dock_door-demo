# 🏭 Tor-Zuordnung (Dock Door Assignment / Cross-Dock)

Interaktive Demo zur Zuordnung von Relationen (Quelle/Ziel-Kombinationen, z. B. Cross-Dock-Partner oder Zielgebiete) zu den Toren einer Umschlaghalle.

**[→ Demo live ausprobieren](https://sebastianhanisch-dockdoor-demo.streamlit.app/)**

## Worum geht's?

Jede Relation muss genau einem Tor zugeordnet werden, mit dem Ziel, die flussgewichtete Transportdistanz innerhalb der Halle zu minimieren — das klassische Dock Door Assignment Problem, ein Spezialfall des quadratischen Zuordnungsproblems (QAP).

## Methodik

- Drei selbst implementierte Verfahren im Vergleich: **Zuordnung nach Ankunftsreihenfolge** (ungeplant, wie ohne gezielte Planung häufig entsteht), eine **fluss-optimierte Konstruktion** (umschlagstarke Relationen bekommen kurze Wege) und eine **2-opt-Verbesserung** darauf
- Grundrissdarstellung mit automatisch skalierender Torbeschriftung, PDF-Export, Permalink

## Lokal ausführen

```bash
pip install -r requirements-dev.txt
streamlit run app.py
```

Tests: `pytest tests/ -v`

---

Teil des [Operations-Research-Demo-Portfolios](https://sebastianhanisch.net/demos.html) von [Sebastian Hanisch](https://sebastianhanisch.net) — Operations Research und Machine Learning. Interesse an einer maßgeschneiderten Lösung? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html).
