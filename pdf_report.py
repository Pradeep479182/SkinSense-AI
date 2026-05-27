"""
pdf_report.py — Generates a beautiful PDF skin analysis report
Uses ReportLab for layout.
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image as RLImage
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from PIL import Image as PILImage
import io, os
from datetime import datetime

# ── Colour palette (matches the dark UI in spirit) ────────────
GOLD   = colors.HexColor("#C8A96E")
DARK   = colors.HexColor("#0F0F0F")
CARD   = colors.HexColor("#1A1A1A")
MID    = colors.HexColor("#2A2A2A")
LIGHT  = colors.HexColor("#F5F0E8")
MUTED  = colors.HexColor("#9A9488")
GREEN  = colors.HexColor("#4CAF7D")
RED    = colors.HexColor("#E05C5C")
WHITE  = colors.white

W, H = A4   # 595.28 × 841.89 pts


def _style(name, **kw):
    base = getSampleStyleSheet()["Normal"]
    return ParagraphStyle(name, parent=base, **kw)


def generate_pdf(data: dict, image_path: str | None, output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=14*mm, bottomMargin=14*mm,
    )

    story = []

    # ── Cover header ──────────────────────────────────────────
    def _header(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(DARK)
        canvas.rect(0, H - 52*mm, W, 52*mm, fill=1, stroke=0)
        canvas.setFont("Helvetica-Bold", 22)
        canvas.setFillColor(GOLD)
        canvas.drawCentredString(W/2, H - 22*mm, "✦  SKINSENSE AI")
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawCentredString(W/2, H - 30*mm, "PERSONALISED SKIN ANALYSIS REPORT")
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString(W/2, H - 38*mm,
            f"Generated on {datetime.now().strftime('%d %B %Y at %H:%M')}")
        canvas.restoreState()

    def _footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawCentredString(W/2, 8*mm,
            "SkinSense AI  •  For informational purposes only  •  Consult a dermatologist for medical advice")
        canvas.restoreState()

    def _on_page(canvas, doc):
        _header(canvas, doc)
        _footer(canvas, doc)

    story.append(Spacer(1, 48*mm))   # clear the header

    # ── Photo + Score side by side ────────────────────────────
    img_cell = ""
    if image_path and os.path.exists(image_path):
        pil = PILImage.open(image_path).convert("RGB")
        pil.thumbnail((120, 120))
        buf = io.BytesIO()
        pil.save(buf, format="JPEG")
        buf.seek(0)
        rl_img = RLImage(buf, width=36*mm, height=36*mm)
        img_cell = rl_img

    score = data.get("overall_score", "—")
    skin_type = data.get("skin_type", "—")
    detail = data.get("skin_type_detail", "")

    top_table = Table(
        [[img_cell,
          Paragraph(f'<font color="#C8A96E" size="36"><b>{score}</b></font>/10', _style("sc", alignment=TA_CENTER)),
          Paragraph(f'<font color="#F5F0E8" size="16"><b>{skin_type}</b></font><br/>'
                    f'<font color="#9A9488" size="9">{detail}</font>',
                    _style("st", alignment=TA_LEFT, leading=16))
        ]],
        colWidths=[42*mm, 40*mm, None],
        rowHeights=[40*mm]
    )
    top_table.setStyle(TableStyle([
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN",       (0,0), (0,0),  "CENTER"),
        ("ALIGN",       (1,0), (1,0),  "CENTER"),
        ("BACKGROUND",  (0,0), (-1,-1), CARD),
        ("ROUNDEDCORNERS", (0,0), (-1,-1), [8]),
        ("TOPPADDING",  (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
        ("LEFTPADDING", (0,0), (-1,-1), 12),
        ("RIGHTPADDING",(0,0), (-1,-1), 12),
    ]))
    story.append(top_table)
    story.append(Spacer(1, 6*mm))

    # ── Section helper ────────────────────────────────────────
    def section_title(text, color=GOLD):
        story.append(Spacer(1, 4*mm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=MID))
        story.append(Spacer(1, 2*mm))
        story.append(Paragraph(
            f'<font color="{color.hexval() if hasattr(color,"hexval") else "#C8A96E"}" size="8"><b>{text}</b></font>',
            _style("sh", spaceAfter=4, letterSpacing=2)))

    def kv_table(rows, col_w=None):
        col_w = col_w or [60*mm, None]
        t = Table(rows, colWidths=col_w)
        t.setStyle(TableStyle([
            ("FONTNAME",    (0,0), (0,-1), "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,-1), 9),
            ("TEXTCOLOR",   (0,0), (0,-1), MUTED),
            ("TEXTCOLOR",   (1,0), (1,-1), LIGHT),
            ("VALIGN",      (0,0), (-1,-1), "TOP"),
            ("TOPPADDING",  (0,0), (-1,-1), 3),
            ("BOTTOMPADDING",(0,0),(-1,-1), 3),
        ]))
        return t

    # ── Zones + Undertone ─────────────────────────────────────
    section_title("SKIN ZONES & UNDERTONE")
    zones = data.get("zones", {})
    rows = [
        ["T-Zone", zones.get("t_zone", "—")],
        ["Cheeks",  zones.get("cheeks", "—")],
        ["Chin",    zones.get("chin", "—")],
        ["Undertone", data.get("undertone", "—")],
        ["Undertone Shades", data.get("undertone_shades", "—")],
        ["Skin Barrier",     data.get("skin_barrier", "—")],
    ]
    story.append(kv_table(rows))

    # ── Metrics ───────────────────────────────────────────────
    section_title("SKIN METRICS")
    m = data.get("metrics", {})
    metrics_rows = [[k.capitalize(), v] for k, v in m.items()]
    story.append(kv_table(metrics_rows))

    # ── Concerns ──────────────────────────────────────────────
    section_title("VISIBLE CONCERNS")
    concerns = data.get("concerns", [])
    if concerns:
        c_rows = [[c.get("name",""), c.get("severity","")] for c in concerns]
        t = Table(c_rows, colWidths=[None, 40*mm])
        t.setStyle(TableStyle([
            ("FONTSIZE",  (0,0),(-1,-1), 9),
            ("TEXTCOLOR", (0,0),(0,-1), LIGHT),
            ("TEXTCOLOR", (1,0),(1,-1), GOLD),
            ("FONTNAME",  (1,0),(1,-1), "Helvetica-Bold"),
            ("TOPPADDING",(0,0),(-1,-1), 2),
        ]))
        story.append(t)

    # ── Routine ───────────────────────────────────────────────
    section_title("RECOMMENDED ROUTINE")
    routine = data.get("recommended_routine", {})
    step_map = [
        ("Cleanser",    "cleanser"),
        ("Toner",       "toner"),
        ("AM Serum",    "serum_am"),
        ("PM Serum",    "serum_pm"),
        ("Moisturiser", "moisturizer"),
        ("Sunscreen",   "sunscreen"),
    ]
    r_rows = []
    for label, key in step_map:
        item = routine.get(key, {})
        r_rows.append([label, item.get("product","—"), item.get("note","—")])
    rt = Table(r_rows, colWidths=[36*mm, 70*mm, None])
    rt.setStyle(TableStyle([
        ("FONTSIZE",     (0,0),(-1,-1), 9),
        ("FONTNAME",     (0,0),(0,-1), "Helvetica-Bold"),
        ("TEXTCOLOR",    (0,0),(0,-1), GOLD),
        ("TEXTCOLOR",    (1,0),(1,-1), LIGHT),
        ("TEXTCOLOR",    (2,0),(2,-1), MUTED),
        ("TOPPADDING",   (0,0),(-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
    ]))
    story.append(rt)

    # ── Ingredients ───────────────────────────────────────────
    section_title("INGREDIENTS")
    best   = data.get("best_ingredients", [])
    avoid  = data.get("avoid_ingredients", [])
    max_r  = max(len(best), len(avoid))
    best  += [""] * (max_r - len(best))
    avoid += [""] * (max_r - len(avoid))
    ing_rows = [["✓  " + b if b else "", "✕  " + a if a else ""] for b, a in zip(best, avoid)]
    ing_rows.insert(0, ["Best Ingredients", "Avoid / Limit"])
    it = Table(ing_rows, colWidths=[None, None])
    it.setStyle(TableStyle([
        ("FONTNAME",  (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",  (0,0),(-1,-1), 9),
        ("TEXTCOLOR", (0,0),(0,0), GREEN),
        ("TEXTCOLOR", (1,0),(1,0), RED),
        ("TEXTCOLOR", (0,1),(0,-1), LIGHT),
        ("TEXTCOLOR", (1,1),(1,-1), LIGHT),
        ("LINEBELOW", (0,0),(-1,0), 0.5, MID),
        ("TOPPADDING",(0,0),(-1,-1), 2),
    ]))
    story.append(it)

    # ── Lifestyle tips ────────────────────────────────────────
    section_title("LIFESTYLE TIPS")
    for tip in data.get("lifestyle_tips", []):
        story.append(Paragraph(
            f'<font color="#9A9488">◦  </font><font color="#F5F0E8">{tip}</font>',
            _style("tip", fontSize=9, leading=14, spaceAfter=3)))

    # ── Disclaimer ────────────────────────────────────────────
    story.append(Spacer(1, 8*mm))
    story.append(Paragraph(
        '<font color="#555555" size="7">This report is generated by AI and is for informational purposes only. '
        'Please consult a qualified dermatologist for medical advice.</font>',
        _style("disc", alignment=TA_CENTER)))

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    print(f"[PDF] Saved → {output_path}")