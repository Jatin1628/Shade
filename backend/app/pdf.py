"""Render a saved report to PDF. Built from the Firestore SNAPSHOT, so an old
report re-downloads with the numbers it had on its date (no file storage needed).
Uses 'Rs' not the rupee sign: standard PDF fonts have no rupee glyph."""
from io import BytesIO
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

GREEN = colors.HexColor("#1B6B4C")


def inr(x: float) -> str:
    x = float(x)
    if x >= 1e7:
        return f"Rs {x / 1e7:.2f} crore"
    if x >= 1e5:
        return f"Rs {x / 1e5:.2f} lakh"
    return f"Rs {x:,.0f}"


def _table(rows, widths):
    t = Table(rows, colWidths=widths)
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#F2F2F4")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D8D8DE")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def render_report_pdf(rep: dict) -> bytes:
    snap, plan = rep["snapshot"], rep["actionPlan"]
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], textColor=GREEN, fontSize=20, alignment=0)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=GREEN, fontSize=12.5)
    body = ParagraphStyle("b", parent=ss["BodyText"], fontSize=9.5, leading=13)
    small = ParagraphStyle("s", parent=body, fontSize=8, textColor=colors.HexColor("#5A5A6E"))

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm,
                            title=f"Ward {rep['ward']} report", author="Shade")
    W = [70 * mm, 100 * mm]
    s = [Paragraph("Shade: Urban Heat and Tree Priority Report", h1),
         Paragraph(f"<b>Ward {rep['ward']} - {escape(str(rep.get('wardName', '')))}</b> "
                   f"({escape(str(rep['city']).title())}) &nbsp;|&nbsp; generated "
                   f"{escape(str(rep.get('createdAt', ''))[:10])}", body),
         Spacer(1, 6), Paragraph("Diagnosis", h2)]
    s.append(_table([
        ["Priority rank (1 = most urgent)", f"{snap['rank']} of 41"],
        ["Priority score (0-1)", f"{snap['priority']:.2f}"],
        ["Surface temperature (built-up areas)", f"{snap['lst']:.1f} C"],
        ["Tree canopy", f"{snap['canopyPct']:.1f} %"],
        ["Vulnerability (0-1)", f"{snap['vulnerability']:.2f}  [{escape(str(snap.get('vulnerabilitySource', '')))}]"],
    ], W))
    s += [Spacer(1, 8), Paragraph("Action plan (estimate)", h2)]
    s.append(_table([
        ["Target canopy", f"{plan['target_canopy_pct']} %  (gap {plan['gap_pp']} points)"],
        ["Canopy area needed", f"{plan['canopy_area_needed_ha']:,.0f} hectares"],
        ["Trees needed", f"{plan['trees_needed']:,}  (at {plan['crown_area_m2_assumed']:g} m2 canopy per tree)"],
        ["Cost range", f"{inr(plan['cost_inr_low'])} to {inr(plan['cost_inr_high'])}"],
        ["Cooling at target canopy", f"about {plan['cooling_c_at_target_canopy']} C"],
        ["CO2 (young trees)", f"about {plan['co2_tonnes_per_year_young_trees']:,} tonnes / year"],
    ], W))
    s += [Spacer(1, 8), Paragraph("Sources and limits", h2),
          Paragraph(escape(plan["note"]), body), Spacer(1, 4)]
    for k, v in plan["sources"].items():
        s.append(Paragraph(f"<b>{escape(k)}:</b> {escape(v)}", small))
    s += [Spacer(1, 6),
          Paragraph("Land surface temperature is Landsat data (about 11 am, Mar-May 2026), "
                    "not air temperature. Results are associations for planning, not causal proof.", small)]
    doc.build(s)
    return buf.getvalue()
