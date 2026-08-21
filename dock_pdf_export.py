"""
Erzeugt einen Tor-Zuordnungsplan als downloadbares PDF (in-memory) -
Kennzahlen + Tor-für-Tor-Zuordnungsliste.
"""

import time

from dock_evaluation import evaluate_assignment


def generate_assignment_plan_pdf(label, assignment, positions, flow):
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    stats = evaluate_assignment(assignment, positions, flow)
    n = len(assignment)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"Tor-Zuordnungsplan - {label}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Erstellt: {time.strftime('%d.%m.%Y %H:%M')} Uhr", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Kennzahlen", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Gewichtete Gesamtdistanz: {stats['total_weighted_distance']:.0f} m x Bewegungen/Tag", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"Durchschnittliche Distanz je Bewegung: {stats['avg_distance_per_move']:.1f} m", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"Anzahl Tore: {n}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Tor-Zuordnung", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    for door in range(n):
        pdf.cell(0, 6, f"Tor {door + 1}  ->  Relation {assignment[door] + 1}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    return bytes(pdf.output())
