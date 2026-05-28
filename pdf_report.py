"""
Generate a one-page visual skin analysis PDF.

The public API is intentionally small because app.py calls generate_pdf(data,
image_path, output_path) directly after Gemini returns the analysis JSON.
"""
from __future__ import annotations

import io
import os
import tempfile
from datetime import datetime

from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


W, H = A4

BG = colors.HexColor("#F7F1E8")
CARD = colors.HexColor("#FFFDF8")
CARD_2 = colors.HexColor("#F4EBDD")
INK = colors.HexColor("#4B423A")
MUTED = colors.HexColor("#8A7D70")
RULE = colors.HexColor("#E3D7C8")
GOLD = colors.HexColor("#C59A49")
TERRACOTTA = colors.HexColor("#C77454")
SAGE = colors.HexColor("#6F9C83")
BLUE = colors.HexColor("#7EBCD4")
LILAC = colors.HexColor("#A993C8")
RED = colors.HexColor("#B66A61")


def generate_pdf(data: dict, image_path: str | None, output_path: str) -> None:
    """Create a warm A4 infographic report similar to the provided reference."""
    c = canvas.Canvas(output_path, pagesize=A4)
    c.setTitle("SkinSense AI Skin Analysis Report")

    face = _load_face(image_path)
    before_after = _make_before_after(face)

    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    _draw_background_texture(c)

    _draw_header(c)
    _draw_photo_panel(c, face, data)
    _draw_score_card(c, data, 15, 725, 78, 96)
    _draw_skin_type(c, data, 342, 630, 238, 116)
    _draw_concerns(c, data, 342, 520, 238, 96)
    _draw_metrics(c, data, 342, 425, 238, 82)
    _draw_undertone(c, data, 18, 265, 130, 118)
    _draw_barrier(c, data, 154, 265, 130, 118)
    _draw_before_after(c, before_after, data, 292, 265, 288, 118)
    _draw_routine(c, data, 18, 150, 562, 94)
    _draw_ingredients(c, data, 18, 58, 365, 78)
    _draw_avoid_and_tips(c, data, 392, 58, 188, 78)
    _draw_footer(c)

    c.showPage()
    c.save()
    for path in before_after:
        try:
            os.remove(path)
        except OSError:
            pass


def _load_face(image_path: str | None) -> Image.Image | None:
    if not image_path or not os.path.exists(image_path):
        return None
    return Image.open(image_path).convert("RGB")


def _make_before_after(face: Image.Image | None) -> tuple[str | None, str | None]:
    if face is None:
        return (None, None)

    before = ImageOps.exif_transpose(face).copy()
    before = ImageOps.fit(before, (320, 180), method=Image.Resampling.LANCZOS, centering=(0.5, 0.36))

    after = before.filter(ImageFilter.SMOOTH_MORE)
    after = ImageEnhance.Color(after).enhance(1.04)
    after = ImageEnhance.Brightness(after).enhance(1.03)
    after = ImageEnhance.Contrast(after).enhance(0.97)

    return (_temp_jpeg(before), _temp_jpeg(after))


def _temp_jpeg(img: Image.Image) -> str:
    f = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    with f:
        img.save(f, format="JPEG", quality=90)
    return f.name


def _draw_background_texture(c: canvas.Canvas) -> None:
    c.saveState()
    c.setStrokeColor(colors.Color(1, 1, 1, alpha=0.32))
    c.setLineWidth(0.35)
    for x in range(0, int(W), 28):
        c.line(x, 0, x + 48, H)
    c.restoreState()


def _draw_header(c: canvas.Canvas) -> None:
    c.setFillColor(INK)
    c.setFont("Times-Roman", 26)
    c.drawCentredString(432, 802, "SKIN ANALYSIS")
    c.setFont("Helvetica", 9)
    c.setFillColor(MUTED)
    c.drawCentredString(432, 786, "PERSONALISED FOR YOU")
    c.setFont("Helvetica", 7)
    c.drawCentredString(432, 773, datetime.now().strftime("%d %B %Y"))


def _draw_photo_panel(c: canvas.Canvas, face: Image.Image | None, data: dict) -> None:
    x, y, w, h = 16, 392, 310, 415
    _round_rect(c, x, y, w, h, 12, colors.HexColor("#EFE3D3"), stroke=0)
    if face:
        img = ImageOps.exif_transpose(face)
        fitted = ImageOps.fit(img, (760, 1000), method=Image.Resampling.LANCZOS, centering=(0.5, 0.32))
        _clip_image(c, fitted, x, y, w, h, radius=12)
    else:
        c.setFillColor(CARD_2)
        c.roundRect(x, y, w, h, 12, fill=1, stroke=0)
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 11)
        c.drawCentredString(x + w / 2, y + h / 2, "Face photo")

    c.saveState()
    c.setStrokeColor(colors.Color(1, 1, 1, alpha=0.72))
    c.setLineWidth(0.7)
    c.setDash(2, 3)
    c.ellipse(x + 94, y + 236, x + 235, y + 330, stroke=1, fill=0)
    c.setDash()
    _zone_line(c, x + 220, y + 310, 334, y + 310, "T-ZONE")
    _zone_line(c, x + 208, y + 247, 334, y + 247, "CHEEKS")
    _zone_line(c, x + 205, y + 190, 334, y + 190, "CHIN")
    c.restoreState()


def _draw_score_card(c: canvas.Canvas, data: dict, x: float, y: float, w: float, h: float) -> None:
    _round_rect(c, x, y, w, h, 10, colors.Color(1, 1, 1, alpha=0.83), RULE)
    score = _score(data.get("overall_score", 7.0))
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(x + w / 2, y + h - 20, "OVERALL")
    c.drawCentredString(x + w / 2, y + h - 31, "SKIN SCORE")
    c.setFont("Times-Roman", 28)
    c.drawCentredString(x + w / 2 - 5, y + 39, f"{score:.1f}")
    c.setFont("Helvetica", 8)
    c.drawString(x + w / 2 + 21, y + 39, "/10")
    stars = max(1, min(5, round(score / 2)))
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(GOLD)
    c.drawCentredString(x + w / 2, y + 18, "*" * stars + "." * (5 - stars))


def _draw_skin_type(c: canvas.Canvas, data: dict, x: float, y: float, w: float, h: float) -> None:
    _card_title(c, x, y, w, h, "SKIN TYPE")
    c.setFillColor(INK)
    c.setFont("Times-Bold", 17)
    c.drawCentredString(x + w / 2, y + h - 45, str(data.get("skin_type", "Combination")).upper())
    c.setFillColor(colors.HexColor("#F7F1E8"))
    c.roundRect(x + w / 2 - 48, y + h - 65, 96, 16, 8, fill=1, stroke=0)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 7)
    _center_ellipsized(c, str(data.get("skin_type_detail", "Balanced Overall")), x + w / 2, y + h - 60, 88)

    zones = data.get("zones", {})
    items = [
        ("T", "T-Zone", zones.get("t_zone", "Slightly Oily")),
        ("U", "Cheeks", zones.get("cheeks", "Normal to Dry")),
        ("O", "Chin", zones.get("chin", "Balanced")),
    ]
    for i, (icon, label, value) in enumerate(items):
        cx = x + 48 + i * 72
        c.setStrokeColor(MUTED)
        c.circle(cx, y + 38, 13, stroke=1, fill=0)
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(MUTED)
        c.drawCentredString(cx, y + 34, icon)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 6.8)
        c.drawCentredString(cx, y + 17, label)
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 6)
        _center_ellipsized(c, value, cx, y + 7, 58)


def _draw_concerns(c: canvas.Canvas, data: dict, x: float, y: float, w: float, h: float) -> None:
    _card_title(c, x, y, w, h, "VISIBLE CONCERNS")
    concerns = data.get("concerns") or [
        {"name": "Dark Spots", "severity": "Mild"},
        {"name": "Uneven Tone", "severity": "Mild"},
        {"name": "Pores", "severity": "Visible"},
        {"name": "Texture", "severity": "Slight"},
    ]
    labels = [(f"{c.get('severity', '').strip()} {c.get('name', '').strip()}").strip() for c in concerns[:4]]
    while len(labels) < 4:
        labels.append("Balanced")
    swatches = ["#D28A65", "#E0A17E", "#A45F4E", "#BD825F"]
    for i, label in enumerate(labels[:4]):
        cx = x + 35 + i * 56
        _skin_swatch(c, cx, y + 43, 21, colors.HexColor(swatches[i]))
        c.setFillColor(INK)
        c.setFont("Helvetica", 6.2)
        _draw_wrapped_center(c, label, cx, y + 15, 45, 7.5, max_lines=2)


def _draw_metrics(c: canvas.Canvas, data: dict, x: float, y: float, w: float, h: float) -> None:
    _round_rect(c, x, y, w, h, 8, CARD, RULE)
    metrics = data.get("metrics", {})
    items = [
        ("HYDRATION", metrics.get("hydration", "Good"), BLUE, "drop"),
        ("TEXTURE", metrics.get("texture", "Smooth"), SAGE, "waves"),
        ("PORES", metrics.get("pores", "Small - Medium"), GOLD, "pores"),
        ("RADIANCE", metrics.get("radiance", "Healthy Glow"), LILAC, "spark"),
    ]
    col_w = w / 4
    for i, (label, value, color, icon) in enumerate(items):
        ix = x + i * col_w
        if i:
            c.setStrokeColor(RULE)
            c.line(ix, y + 8, ix, y + h - 8)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawCentredString(ix + col_w / 2, y + h - 17, label)
        _metric_icon(c, ix + col_w / 2, y + 42, color, icon)
        c.setFillColor(INK)
        c.setFont("Helvetica", 6)
        _draw_wrapped_center(c, value, ix + col_w / 2, y + 21, col_w - 12, 7, max_lines=2)
        _rating_dots(c, ix + col_w / 2 - 15, y + 10, color)


def _draw_undertone(c: canvas.Canvas, data: dict, x: float, y: float, w: float, h: float) -> None:
    _card_title(c, x, y, w, h, "UNDERTONE")
    tone = str(data.get("undertone", "Warm")).upper()
    shades = data.get("undertone_shades", "Warm - Golden - Peachy")
    c.setFillColor(INK)
    c.setFont("Times-Bold", 12)
    _draw_wrapped_center(c, tone, x + w / 2, y + 71, w - 20, 13, max_lines=2)
    for i, col in enumerate(["#EFC79E", "#E8B978", "#DDA353"]):
        c.setFillColor(colors.HexColor(col))
        c.circle(x + 32 + i * 34, y + 46, 12, fill=1, stroke=0)
    c.setStrokeColor(GOLD)
    c.setLineWidth(2)
    c.line(x + 24, y + 22, x + w - 24, y + 22)
    c.setFillColor(INK)
    c.circle(x + w / 2, y + 22, 3, fill=1, stroke=0)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 6)
    _center_ellipsized(c, str(shades), x + w / 2, y + 7, w - 18)


def _draw_barrier(c: canvas.Canvas, data: dict, x: float, y: float, w: float, h: float) -> None:
    _card_title(c, x, y, w, h, "SKIN BARRIER")
    barrier = str(data.get("skin_barrier", "Strong")).upper()
    c.setStrokeColor(SAGE)
    c.setLineWidth(1.4)
    c.roundRect(x + w / 2 - 13, y + 72, 26, 24, 8, stroke=1, fill=0)
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(SAGE)
    c.drawCentredString(x + w / 2, y + 77, "+")
    c.setFillColor(INK)
    c.setFont("Times-Bold", 12)
    c.drawCentredString(x + w / 2, y + 59, barrier)
    _barrier_cells(c, x + 18, y + 18, w - 36, 24)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 6)
    c.drawCentredString(x + w / 2, y + 7, "Well-Protected")


def _draw_before_after(
    c: canvas.Canvas,
    paths: tuple[str | None, str | None],
    data: dict,
    x: float,
    y: float,
    w: float,
    h: float,
) -> None:
    _round_rect(c, x, y, w, h, 8, colors.HexColor("#2C211C"), RULE)
    before_path, after_path = paths
    gap = 2
    img_w = (w - gap) / 2
    if before_path:
        _clip_image_path(c, before_path, x, y + 17, img_w, h - 17, radius=6)
    if after_path:
        _clip_image_path(c, after_path, x + img_w + gap, y + 17, img_w, h - 17, radius=6)
    c.setFillColor(colors.Color(0, 0, 0, alpha=0.32))
    c.rect(x, y + h - 18, img_w, 18, fill=1, stroke=0)
    c.rect(x + img_w + gap, y + h - 18, img_w, 18, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 6.8)
    c.drawCentredString(x + img_w / 2, y + h - 12, "BEFORE")
    c.drawCentredString(x + img_w + gap + img_w / 2, y + h - 12, "AFTER OPTIMISED")
    c.setFillColor(colors.white)
    c.circle(x + w / 2, y + 58, 11, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(x + w / 2, y + 54, ">")
    c.setFillColor(colors.HexColor("#6D5548"))
    c.rect(x, y, w, 17, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 5.7)
    c.drawCentredString(x + img_w / 2, y + 5.7, "Skin texture and tone baseline")
    c.drawCentredString(x + img_w + gap + img_w / 2, y + 5.7, "Balanced - smoother - radiant")


def _draw_routine(c: canvas.Canvas, data: dict, x: float, y: float, w: float, h: float) -> None:
    _round_rect(c, x, y, w, h, 8, CARD, RULE)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(x + w / 2, y + h - 12, "RECOMMENDED ROUTINE")
    routine = data.get("recommended_routine", {})
    steps = [
        ("CLEANSER", "cleanser", BLUE),
        ("TONER", "toner", SAGE),
        ("SERUM AM", "serum_am", TERRACOTTA),
        ("SERUM PM", "serum_pm", LILAC),
        ("MOISTURISER", "moisturizer", BLUE),
        ("SUNSCREEN AM", "sunscreen", GOLD),
    ]
    col_w = w / 6
    for i, (label, key, color) in enumerate(steps):
        ix = x + i * col_w
        if i:
            c.setStrokeColor(RULE)
            c.line(ix, y + 8, ix, y + h - 18)
        item = routine.get(key, {})
        product = item.get("product", label.title())
        note = item.get("note", "")
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 6.2)
        c.drawCentredString(ix + col_w / 2, y + h - 25, label)
        _product_icon(c, ix + col_w / 2, y + 39, color, i)
        c.setFillColor(INK)
        c.setFont("Helvetica", 5.8)
        _draw_wrapped_center(c, product, ix + col_w / 2, y + 17, col_w - 10, 6.6, max_lines=2)
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 5.2)
        _center_ellipsized(c, note, ix + col_w / 2, y + 7, col_w - 12)


def _draw_ingredients(c: canvas.Canvas, data: dict, x: float, y: float, w: float, h: float) -> None:
    _round_rect(c, x, y, w, h, 8, CARD, RULE)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 6.8)
    c.drawString(x + 12, y + h - 15, "BEST INGREDIENTS FOR YOU")
    items = list(data.get("best_ingredients") or ["Niacinamide", "Vitamin C", "Hyaluronic Acid", "Ceramides", "Panthenol"])
    items = items[:5]
    col_w = (w - 18) / max(1, len(items))
    palette = [BLUE, colors.HexColor("#F5A623"), colors.HexColor("#9DCAE2"), GOLD, SAGE]
    for i, name in enumerate(items):
        cx = x + 16 + col_w * i + col_w / 2
        _ingredient_orb(c, cx, y + 39, palette[i % len(palette)])
        c.setFillColor(INK)
        c.setFont("Helvetica", 5.6)
        _draw_wrapped_center(c, name, cx, y + 14, col_w - 8, 6.2, max_lines=2)


def _draw_avoid_and_tips(c: canvas.Canvas, data: dict, x: float, y: float, w: float, h: float) -> None:
    _round_rect(c, x, y, w, h, 8, CARD, RULE)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 6.8)
    c.drawCentredString(x + w / 2, y + h - 15, "AVOID / LIMIT")
    avoid = list(data.get("avoid_ingredients") or ["Harsh Scrubs", "Alcohol Heavy", "Strong Fragrance"])[:3]
    col_w = w / 3
    for i, name in enumerate(avoid):
        cx = x + col_w * i + col_w / 2
        _avoid_icon(c, cx, y + 40, i)
        c.setFillColor(RED)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(cx + 14, y + 31, "x")
        c.setFillColor(INK)
        c.setFont("Helvetica", 5.5)
        _draw_wrapped_center(c, name, cx, y + 14, col_w - 7, 6.2, max_lines=2)


def _draw_footer(c: canvas.Canvas) -> None:
    tips = ["Stay Hydrated", "Always Wear SPF", "Sleep Well", "Eat Balanced", "Manage Stress"]
    c.setFillColor(colors.HexColor("#EFE5D8"))
    c.rect(0, 0, W, 38, fill=1, stroke=0)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 6.5)
    for i, tip in enumerate(tips):
        c.drawCentredString(74 + i * 112, 18, tip)
    c.setFont("Helvetica", 5.6)
    c.drawCentredString(W / 2, 6, "AI generated educational report. For medical concerns, consult a qualified dermatologist.")


def _round_rect(c: canvas.Canvas, x: float, y: float, w: float, h: float, r: float, fill, stroke=None) -> None:
    c.saveState()
    c.setFillColor(fill)
    if stroke:
        c.setStrokeColor(stroke)
        c.setLineWidth(0.7)
        c.roundRect(x, y, w, h, r, fill=1, stroke=1)
    else:
        c.roundRect(x, y, w, h, r, fill=1, stroke=0)
    c.restoreState()


def _card_title(c: canvas.Canvas, x: float, y: float, w: float, h: float, title: str) -> None:
    _round_rect(c, x, y, w, h, 8, CARD, RULE)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawCentredString(x + w / 2, y + h - 18, title)


def _clip_image(c: canvas.Canvas, img: Image.Image, x: float, y: float, w: float, h: float, radius: float = 8) -> None:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    buf.seek(0)
    path = c.beginPath()
    path.roundRect(x, y, w, h, radius)
    c.saveState()
    c.clipPath(path, stroke=0, fill=0)
    c.drawImage(ImageReader(buf), x, y, width=w, height=h, preserveAspectRatio=False, mask="auto")
    c.restoreState()


def _clip_image_path(c: canvas.Canvas, image_path: str, x: float, y: float, w: float, h: float, radius: float = 8) -> None:
    path = c.beginPath()
    path.roundRect(x, y, w, h, radius)
    c.saveState()
    c.clipPath(path, stroke=0, fill=0)
    c.drawImage(image_path, x, y, width=w, height=h, preserveAspectRatio=False, mask="auto")
    c.restoreState()


def _zone_line(c: canvas.Canvas, x1: float, y1: float, x2: float, y2: float, label: str) -> None:
    c.line(x1, y1, x2 - 18, y2)
    c.setFont("Helvetica-Bold", 5.5)
    c.setFillColor(INK)
    c.drawString(x2 - 14, y2 - 2, label)


def _score(value) -> float:
    try:
        return max(1.0, min(10.0, float(value)))
    except (TypeError, ValueError):
        return 7.0


def _skin_swatch(c: canvas.Canvas, cx: float, cy: float, r: float, fill) -> None:
    c.setFillColor(fill)
    c.circle(cx, cy, r, fill=1, stroke=0)
    c.setFillColor(colors.Color(1, 1, 1, alpha=0.18))
    for dx, dy, rr in [(-6, 5, 3), (5, 1, 2), (0, -6, 2.5), (8, 7, 1.8)]:
        c.circle(cx + dx, cy + dy, rr, fill=1, stroke=0)


def _metric_icon(c: canvas.Canvas, cx: float, cy: float, color, kind: str) -> None:
    c.setStrokeColor(color)
    c.setFillColor(colors.Color(color.red, color.green, color.blue, alpha=0.20))
    c.setLineWidth(1.2)
    if kind == "drop":
        p = c.beginPath()
        p.moveTo(cx, cy + 13)
        p.curveTo(cx - 12, cy - 2, cx - 7, cy - 12, cx, cy - 12)
        p.curveTo(cx + 7, cy - 12, cx + 12, cy - 2, cx, cy + 13)
        c.drawPath(p, stroke=1, fill=1)
    elif kind == "waves":
        for offset in [-8, 0, 8]:
            c.bezier(cx - 15, cy + offset, cx - 8, cy + offset + 6, cx - 4, cy + offset - 6, cx + 3, cy + offset)
            c.bezier(cx + 3, cy + offset, cx + 8, cy + offset + 6, cx + 15, cy + offset - 4, cx + 17, cy + offset)
    elif kind == "pores":
        c.circle(cx, cy, 11, stroke=1, fill=0)
        for dx, dy in [(-5, 4), (4, 3), (0, -5), (6, -5), (-7, -4)]:
            c.circle(cx + dx, cy + dy, 1.6, stroke=1, fill=0)
    else:
        c.setFont("Helvetica-Bold", 19)
        c.setFillColor(color)
        c.drawCentredString(cx, cy - 6, "*")


def _rating_dots(c: canvas.Canvas, x: float, y: float, color) -> None:
    for i in range(5):
        c.setFillColor(color if i < 4 else colors.HexColor("#E4D8CA"))
        c.circle(x + i * 7, y, 2.2, fill=1, stroke=0)


def _barrier_cells(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    c.setFillColor(colors.HexColor("#F7C4B7"))
    c.setStrokeColor(colors.HexColor("#F0A99B"))
    cell_w = w / 6 - 2
    for row in range(2):
        for col in range(6):
            cx = x + col * (cell_w + 2)
            cy = y + row * (h / 2)
            c.roundRect(cx, cy, cell_w, h / 2 - 2, 4, fill=1, stroke=1)
            c.setFillColor(colors.HexColor("#E79488"))
            c.circle(cx + cell_w / 2, cy + 4, 1.5, fill=1, stroke=0)
            c.setFillColor(colors.HexColor("#F7C4B7"))


def _product_icon(c: canvas.Canvas, cx: float, cy: float, color, index: int) -> None:
    c.setFillColor(colors.HexColor("#F8F7F4"))
    c.setStrokeColor(colors.HexColor("#D7CEC2"))
    c.setLineWidth(0.7)
    if index in (0, 5):
        c.roundRect(cx - 10, cy - 23, 20, 44, 4, fill=1, stroke=1)
        c.setFillColor(color)
        c.rect(cx - 8, cy - 2, 16, 13, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.rect(cx - 6, cy + 15, 12, 4, fill=1, stroke=0)
    elif index == 4:
        c.roundRect(cx - 17, cy - 17, 34, 26, 4, fill=1, stroke=1)
        c.setFillColor(color)
        c.rect(cx - 15, cy - 8, 30, 10, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#D4ECF4"))
        c.ellipse(cx - 17, cy + 5, cx + 17, cy + 16, fill=1, stroke=1)
    else:
        c.roundRect(cx - 8, cy - 22, 16, 38, 4, fill=1, stroke=1)
        c.setFillColor(color)
        c.rect(cx - 6, cy - 7, 12, 16, fill=1, stroke=0)
        c.setFillColor(INK)
        c.rect(cx - 4, cy + 17, 8, 6, fill=1, stroke=0)


def _ingredient_orb(c: canvas.Canvas, cx: float, cy: float, color) -> None:
    c.setFillColor(colors.Color(color.red, color.green, color.blue, alpha=0.24))
    c.setStrokeColor(color)
    c.circle(cx, cy, 14, fill=1, stroke=1)
    c.setFillColor(colors.Color(1, 1, 1, alpha=0.65))
    for dx, dy, rr in [(-6, 3, 4), (4, 5, 3), (2, -5, 3), (-1, 0, 2)]:
        c.circle(cx + dx, cy + dy, rr, fill=1, stroke=0)


def _avoid_icon(c: canvas.Canvas, cx: float, cy: float, index: int) -> None:
    c.setStrokeColor(colors.HexColor("#CFC6BA"))
    c.setFillColor(colors.HexColor("#EFE9E1"))
    if index == 0:
        c.circle(cx, cy, 14, fill=1, stroke=1)
        c.setStrokeColor(colors.HexColor("#BDB2A6"))
        for i in range(5):
            c.line(cx - 8 + i * 4, cy + 10, cx - 3 + i * 4, cy - 10)
    elif index == 1:
        c.roundRect(cx - 8, cy - 16, 16, 30, 3, fill=1, stroke=1)
        c.rect(cx - 5, cy + 14, 10, 5, fill=1, stroke=1)
    else:
        c.roundRect(cx - 9, cy - 14, 18, 28, 4, fill=1, stroke=1)
        c.line(cx - 7, cy + 10, cx + 7, cy + 10)


def _draw_wrapped_center(
    c: canvas.Canvas,
    text: str,
    cx: float,
    y_top: float,
    width: float,
    leading: float,
    max_lines: int = 2,
) -> None:
    words = str(text or "").split()
    lines: list[str] = []
    line = ""
    font = c._fontname
    size = c._fontsize
    for word in words:
        attempt = f"{line} {word}".strip()
        if c.stringWidth(attempt, font, size) <= width or not line:
            line = attempt
        else:
            lines.append(line)
            line = word
        if len(lines) == max_lines:
            break
    if line and len(lines) < max_lines:
        lines.append(line)
    for i, line in enumerate(lines[:max_lines]):
        if i == max_lines - 1 and c.stringWidth(line, font, size) > width:
            line = _ellipsize(c, line, width)
        c.drawCentredString(cx, y_top - i * leading, line)


def _center_ellipsized(c: canvas.Canvas, text: str, cx: float, y: float, width: float) -> None:
    c.drawCentredString(cx, y, _ellipsize(c, str(text or ""), width))


def _ellipsize(c: canvas.Canvas, text: str, width: float) -> str:
    font = c._fontname
    size = c._fontsize
    if c.stringWidth(text, font, size) <= width:
        return text
    out = text
    while out and c.stringWidth(out + "...", font, size) > width:
        out = out[:-1]
    return (out.rstrip() + "...") if out else ""


def _demo_data() -> dict:
    return {
        "overall_score": 8.5,
        "skin_type": "Combination",
        "skin_type_detail": "Balanced Overall",
        "undertone": "Warm Golden",
        "undertone_shades": "Warm - Golden - Peachy",
        "skin_barrier": "Strong",
        "zones": {"t_zone": "Slightly Oily", "cheeks": "Normal to Dry", "chin": "Balanced"},
        "metrics": {
            "hydration": "Good",
            "texture": "Smooth",
            "pores": "Small - Medium",
            "radiance": "Healthy Glow",
        },
        "concerns": [
            {"name": "Dark Spots", "severity": "Mild"},
            {"name": "Uneven Tone", "severity": "Mild"},
            {"name": "Pores", "severity": "Visible"},
            {"name": "Texture", "severity": "Slight"},
        ],
        "recommended_routine": {
            "cleanser": {"product": "Gentle Hydrating", "note": "AM/PM"},
            "toner": {"product": "Hydrating Soothing", "note": "After cleanse"},
            "serum_am": {"product": "Brightening Antioxidant", "note": "Vitamin C"},
            "serum_pm": {"product": "Pore Control Even Tone", "note": "Night"},
            "moisturizer": {"product": "Lightweight Hydrating", "note": "Barrier care"},
            "sunscreen": {"product": "Broad Spectrum SPF 50", "note": "Daily"},
        },
        "best_ingredients": ["Niacinamide", "Vitamin C", "Hyaluronic Acid", "Ceramides", "Panthenol"],
        "avoid_ingredients": ["Harsh Scrubs", "Alcohol Heavy", "Fragrance Strong"],
        "lifestyle_tips": ["Stay hydrated", "Wear SPF", "Sleep well"],
    }


if __name__ == "__main__":
    generate_pdf(_demo_data(), r"C:\Users\FUTURE TECH\Downloads\fasec.jpeg", "skin_report_demo.pdf")
    print("Saved skin_report_demo.pdf")
