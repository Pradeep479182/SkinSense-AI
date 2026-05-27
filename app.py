import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import base64
import json
import os
import os
from dotenv import load_dotenv
load_dotenv()
from PIL import Image, ImageTk
import requests
from datetime import datetime
from pdf_report import generate_pdf

# ─── Theme Setup ───────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

ACCENT    = "#C8A96E"   # warm gold
BG_DARK   = "#0F0F0F"
BG_CARD   = "#1A1A1A"
BG_INPUT  = "#242424"
TEXT_PRI  = "#F5F0E8"
TEXT_SEC  = "#9A9488"
SUCCESS   = "#4CAF7D"
DANGER    = "#E05C5C"

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", "")
GOOGLE_MODEL   = os.environ.get("GOOGLE_MODEL", "gemini-1.5-mini")

# ─── Utility ───────────────────────────────────────────────────
def encode_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")

def get_ext(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    return {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp", "gif": "gif"}.get(ext.lstrip("."), "jpeg")

# ─── API Call ──────────────────────────────────────────────────
def analyze_skin(image_path: str, form_data: dict) -> dict:
    img_b64  = encode_image(image_path)
    img_type = get_ext(image_path)

    prompt = f"""You are an expert dermatologist AI. Analyze the face image provided.
Also consider this user information:
- Age: {form_data.get('age', 'unknown')}
- Skin concerns: {form_data.get('concerns', 'none mentioned')}
- Current routine: {form_data.get('routine', 'none mentioned')}
- Sensitivity level: {form_data.get('sensitivity', 'normal')}

Return ONLY valid JSON (no markdown, no explanation) in this exact structure:
{{
  "overall_score": <number 1-10, one decimal>,
  "skin_type": "<Oily|Dry|Combination|Normal|Sensitive>",
  "skin_type_detail": "<one line description>",
  "undertone": "<Warm|Cool|Neutral>",
  "undertone_shades": "<e.g. Warm · Golden · Peachy>",
  "skin_barrier": "<Weak|Moderate|Strong>",
  "zones": {{
    "t_zone": "<Oily|Normal|Dry>",
    "cheeks": "<Oily|Normal|Dry>",
    "chin": "<Oily|Normal|Dry>"
  }},
  "metrics": {{
    "hydration": "<Poor|Fair|Good|Excellent>",
    "texture": "<Rough|Uneven|Smooth|Very Smooth>",
    "pores": "<Large|Medium|Small>",
    "radiance": "<Dull|Fair|Healthy Glow|Luminous>"
  }},
  "concerns": [
    {{"name": "<concern name>", "severity": "<Mild|Moderate|Severe>"}},
    {{"name": "<concern name>", "severity": "<Mild|Moderate|Severe>"}}
  ],
  "recommended_routine": {{
    "cleanser": {{"product": "<product type>", "note": "<short note>"}},
    "toner": {{"product": "<product type>", "note": "<short note>"}},
    "serum_am": {{"product": "<product type>", "note": "<short note>"}},
    "serum_pm": {{"product": "<product type>", "note": "<short note>"}},
    "moisturizer": {{"product": "<product type>", "note": "<short note>"}},
    "sunscreen": {{"product": "<product type>", "note": "<short note>"}}
  }},
  "best_ingredients": ["<ingredient1>", "<ingredient2>", "<ingredient3>", "<ingredient4>", "<ingredient5>"],
  "avoid_ingredients": ["<ingredient1>", "<ingredient2>", "<ingredient3>"],
  "lifestyle_tips": ["<tip1>", "<tip2>", "<tip3>", "<tip4>"]
}}"""

    if not GOOGLE_API_KEY:
        raise Exception("Missing Google API key. Set GOOGLE_API_KEY in your environment or .env file.")

    url = f"https://generativelanguage.googleapis.com/v1beta2/models/{GOOGLE_MODEL}:generate"
    params = {"key": GOOGLE_API_KEY}
    body = {
        "prompt": {
            "text": prompt
        },
        "temperature": 0.2,
        "maxOutputTokens": 1200,
        "candidateCount": 1,
        "image": {
            "imageBytes": img_b64,
            "mimeType": f"image/{img_type}"
        }
    }
    resp = requests.post(url, params=params, json=body, timeout=60)
    # Raise a clear exception including body so we can diagnose 4xx/5xx responses
    try:
        resp.raise_for_status()
    except requests.HTTPError:
        # include response body for debugging
        raise Exception(f"HTTP {resp.status_code} {resp.reason}: {resp.text}")

    # Parse response safely and be tolerant of different shapes
    resp_json = resp.json()
    raw = None
    if isinstance(resp_json, dict):
        candidates = resp_json.get("candidates") or resp_json.get("outputs") or []
        if isinstance(candidates, list) and len(candidates) > 0:
            first = candidates[0]
            if isinstance(first, dict):
                raw = first.get("output") or first.get("content") or first.get("text")
            elif isinstance(first, str):
                raw = first
        if raw is None:
            raw = resp_json.get("output") or resp_json.get("content") or resp_json.get("text")

    if raw is None:
        raw = json.dumps(resp_json)

    raw = str(raw).strip()
    # strip possible markdown fences
    if raw.startswith("```"):
        parts = raw.split("```")
        if len(parts) >= 2:
            raw = parts[1]
            if raw.startswith("json"):
                raw = raw[4:]

    return json.loads(raw.strip())


# ═══════════════════════════════════════════════════════════════
#  MAIN APP
# ═══════════════════════════════════════════════════════════════
class SkinAnalyzerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("✦ SkinSense AI — Skin Analysis")
        self.geometry("1100x780")
        self.minsize(900, 680)
        self.configure(fg_color=BG_DARK)

        self.image_path  = None
        self.result_data = None
        self._anim_dots  = 0

        self._build_ui()

    # ── Layout ────────────────────────────────────────────────
    def _build_ui(self):
        # Left panel
        self.left = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=0, width=380)
        self.left.pack(side="left", fill="y", padx=0, pady=0)
        self.left.pack_propagate(False)

        # Right panel
        self.right = ctk.CTkScrollableFrame(self, fg_color=BG_DARK, corner_radius=0)
        self.right.pack(side="right", fill="both", expand=True)

        self._build_left()
        self._build_right_placeholder()

    # ── Left Panel ────────────────────────────────────────────
    def _build_left(self):
        p = self.left

        # Logo
        ctk.CTkLabel(p, text="✦ SkinSense AI", font=("Georgia", 22, "italic"),
                     text_color=ACCENT).pack(pady=(28, 2))
        ctk.CTkLabel(p, text="PERSONALISED SKIN ANALYSIS",
                     font=("Courier", 9), text_color=TEXT_SEC).pack()

        self._divider(p)

        # Image upload area
        self.upload_box = ctk.CTkFrame(p, fg_color=BG_INPUT, corner_radius=12,
                                        border_width=1, border_color="#333333",
                                        height=200, width=320)
        self.upload_box.pack(padx=28, pady=(4, 12))
        self.upload_box.pack_propagate(False)

        self.upload_label = ctk.CTkLabel(self.upload_box,
            text="⬆\n\nDrag & Drop or Click\nto upload your photo",
            font=("Helvetica", 13), text_color=TEXT_SEC, justify="center")
        self.upload_label.place(relx=0.5, rely=0.5, anchor="center")
        self.upload_box.bind("<Button-1>", lambda e: self._pick_image())
        self.upload_label.bind("<Button-1>", lambda e: self._pick_image())

        self.img_preview = ctk.CTkLabel(self.upload_box, text="")
        # hidden until image chosen

        # Form
        self._section(p, "YOUR DETAILS")

        self._field(p, "Age", "age_entry", "e.g. 24")
        self._field(p, "Main Skin Concerns", "concerns_entry",
                    "e.g. dark spots, acne, dullness")
        self._field(p, "Current Routine (optional)", "routine_entry",
                    "e.g. only cleanser + moisturiser")

        ctk.CTkLabel(p, text="Skin Sensitivity", font=("Helvetica", 12),
                     text_color=TEXT_SEC, anchor="w").pack(padx=28, pady=(10, 2), anchor="w")
        self.sensitivity_var = ctk.StringVar(value="Normal")
        sens_menu = ctk.CTkOptionMenu(p, values=["Low", "Normal", "Sensitive", "Very Sensitive"],
                                      variable=self.sensitivity_var,
                                      fg_color=BG_INPUT, button_color=ACCENT,
                                      button_hover_color="#A8893E",
                                      dropdown_fg_color=BG_CARD, font=("Helvetica", 12),
                                      text_color=TEXT_PRI, width=324)
        sens_menu.pack(padx=28, pady=(0, 16))

        # Analyze button
        self.analyze_btn = ctk.CTkButton(p, text="ANALYSE MY SKIN  →",
            font=("Courier", 13, "bold"),
            fg_color=ACCENT, hover_color="#A8893E", text_color="#0F0F0F",
            height=46, corner_radius=8, command=self._start_analysis)
        self.analyze_btn.pack(padx=28, pady=(0, 12), fill="x")

        self.status_label = ctk.CTkLabel(p, text="", font=("Helvetica", 11),
                                          text_color=TEXT_SEC)
        self.status_label.pack()

        # API key warning
        if not ANTHROPIC_API_KEY:
            ctk.CTkLabel(p, text="⚠  Set ANTHROPIC_API_KEY env variable",
                         font=("Helvetica", 10), text_color=DANGER,
                         wraplength=320).pack(padx=28, pady=(6, 0))

    def _field(self, parent, label, attr, placeholder):
        ctk.CTkLabel(parent, text=label, font=("Helvetica", 12),
                     text_color=TEXT_SEC, anchor="w").pack(padx=28, pady=(10, 2), anchor="w")
        entry = ctk.CTkEntry(parent, placeholder_text=placeholder,
                             fg_color=BG_INPUT, border_color="#333333",
                             text_color=TEXT_PRI, placeholder_text_color="#555",
                             height=38, corner_radius=8, width=324)
        entry.pack(padx=28, pady=(0, 0))
        setattr(self, attr, entry)

    def _section(self, parent, text):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", padx=28, pady=(10, 4))
        ctk.CTkLabel(f, text=text, font=("Courier", 9),
                     text_color=ACCENT).pack(side="left")

    def _divider(self, parent):
        ctk.CTkFrame(parent, height=1, fg_color="#2A2A2A").pack(
            fill="x", padx=24, pady=12)

    # ── Right Panel: placeholder ───────────────────────────────
    def _build_right_placeholder(self):
        self._clear_right()
        f = ctk.CTkFrame(self.right, fg_color="transparent")
        f.pack(expand=True, pady=160)
        ctk.CTkLabel(f, text="✦", font=("Georgia", 48), text_color=ACCENT).pack()
        ctk.CTkLabel(f, text="Upload your photo and fill in\nyour details to begin",
                     font=("Helvetica", 15), text_color=TEXT_SEC, justify="center").pack(pady=12)

    def _clear_right(self):
        for w in self.right.winfo_children():
            w.destroy()

    # ── Image pick ────────────────────────────────────────────
    def _pick_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.jpg *.jpeg *.png *.webp")])
        if not path:
            return
        self.image_path = path
        img = Image.open(path).convert("RGB")
        img.thumbnail((320, 196))
        photo = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
        self.img_preview.configure(image=photo, text="")
        self.img_preview.image = photo
        self.img_preview.place(relx=0.5, rely=0.5, anchor="center")
        self.upload_label.place_forget()

    # ── Analysis ──────────────────────────────────────────────
    def _start_analysis(self):
        if not self.image_path:
            messagebox.showwarning("No image", "Please upload a face photo first!")
            return
        if not ANTHROPIC_API_KEY:
            messagebox.showerror("API Key Missing",
                "Set your ANTHROPIC_API_KEY environment variable first.\n"
                "See README.md for instructions.")
            return

        self.analyze_btn.configure(state="disabled", text="Analysing…")
        self._anim_dots = 0
        self._animate_status()

        form = {
            "age":         self.age_entry.get().strip() or "unknown",
            "concerns":    self.concerns_entry.get().strip() or "none",
            "routine":     self.routine_entry.get().strip() or "none",
            "sensitivity": self.sensitivity_var.get(),
        }

        def run():
            try:
                data = analyze_skin(self.image_path, form)
                self.result_data = data
                self.after(0, lambda: self._show_results(data))
            except Exception as e:
                self.after(0, lambda err=e: self._on_error(err))

        threading.Thread(target=run, daemon=True).start()

    def _animate_status(self):
        dots = "." * (self._anim_dots % 4)
        self.status_label.configure(text=f"Analysing your skin{dots}")
        self._anim_dots += 1
        if self.analyze_btn.cget("state") == "disabled":
            self.after(400, self._animate_status)

    def _on_error(self, err):
        self.analyze_btn.configure(state="normal", text="ANALYSE MY SKIN  →")
        self.status_label.configure(text="")
        s = str(err)
        # Friendly guidance for common API issues
        if "credit balance" in s or "too low to access" in s or "insufficient" in s:
            msg = (
                "Analysis failed: Your Anthropic account has insufficient credits.\n"
                "Please visit Anthropic → Plans & Billing to add credits or upgrade your plan.\n\n"
                "If you posted your API key publicly, revoke it and create a new key, then update your .env file."
            )
            messagebox.showerror("API Credits Required", msg)
        elif "Unauthorized" in s or "401" in s:
            msg = (
                "Analysis failed: API key unauthorized.\n"
                "Check that ANTHROPIC_API_KEY in your .env is correct (no quotes) and restart the app.\n"
                "If you exposed the key, revoke and replace it in the Anthropic dashboard."
            )
            messagebox.showerror("API Key Error", msg)
        else:
            messagebox.showerror("Error", f"Analysis failed:\n{s}")

    # ── Results Dashboard ─────────────────────────────────────
    def _show_results(self, d: dict):
        self.analyze_btn.configure(state="normal", text="RE-ANALYSE  →")
        self.status_label.configure(text="✓ Analysis complete")
        self._clear_right()

        pad = {"padx": 24, "pady": 8}

        # ── Header ──
        header = ctk.CTkFrame(self.right, fg_color="transparent")
        header.pack(fill="x", **pad)
        ctk.CTkLabel(header, text="SKIN ANALYSIS", font=("Courier", 11),
                     text_color=ACCENT).pack(anchor="w")
        ctk.CTkLabel(header, text="Personalised for you  ✦",
                     font=("Georgia", 13, "italic"), text_color=TEXT_SEC).pack(anchor="w")

        # ── Score + Type row ──
        row1 = ctk.CTkFrame(self.right, fg_color="transparent")
        row1.pack(fill="x", **pad)

        score_card = self._card(row1, width=180)
        score_card.pack(side="left", padx=(0, 12))
        ctk.CTkLabel(score_card, text="OVERALL SCORE", font=("Courier", 9),
                     text_color=TEXT_SEC).pack(pady=(16, 0))
        score = d.get("overall_score", 7.0)
        ctk.CTkLabel(score_card, text=f"{score}", font=("Georgia", 52, "italic"),
                     text_color=ACCENT).pack()
        stars = "★" * int(round(float(score) / 2)) + "☆" * (5 - int(round(float(score) / 2)))
        ctk.CTkLabel(score_card, text=stars, font=("Helvetica", 14),
                     text_color=ACCENT).pack(pady=(0, 16))

        type_card = self._card(row1)
        type_card.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(type_card, text="SKIN TYPE", font=("Courier", 9),
                     text_color=TEXT_SEC).pack(pady=(16, 0))
        ctk.CTkLabel(type_card, text=d.get("skin_type", "—"),
                     font=("Georgia", 28, "italic"), text_color=TEXT_PRI).pack()
        ctk.CTkLabel(type_card, text=d.get("skin_type_detail", ""),
                     font=("Helvetica", 11), text_color=TEXT_SEC,
                     wraplength=320).pack(pady=(0, 8))

        zones = d.get("zones", {})
        zone_row = ctk.CTkFrame(type_card, fg_color="transparent")
        zone_row.pack(pady=(0, 16))
        for label, key in [("T-Zone", "t_zone"), ("Cheeks", "cheeks"), ("Chin", "chin")]:
            z = ctk.CTkFrame(zone_row, fg_color=BG_INPUT, corner_radius=8, width=90)
            z.pack(side="left", padx=6)
            z.pack_propagate(False)
            ctk.CTkLabel(z, text=label, font=("Courier", 8),
                         text_color=TEXT_SEC).pack(pady=(8, 0))
            ctk.CTkLabel(z, text=zones.get(key, "—"),
                         font=("Helvetica", 11), text_color=TEXT_PRI).pack(pady=(0, 8))

        # ── Undertone + Barrier ──
        row2 = ctk.CTkFrame(self.right, fg_color="transparent")
        row2.pack(fill="x", **pad)

        ut_card = self._card(row2)
        ut_card.pack(side="left", fill="both", expand=True, padx=(0, 12))
        ctk.CTkLabel(ut_card, text="UNDERTONE", font=("Courier", 9),
                     text_color=TEXT_SEC).pack(pady=(14, 0))
        ctk.CTkLabel(ut_card, text=d.get("undertone", "—"),
                     font=("Georgia", 22, "italic"), text_color=TEXT_PRI).pack()
        ctk.CTkLabel(ut_card, text=d.get("undertone_shades", ""),
                     font=("Helvetica", 11), text_color=TEXT_SEC).pack(pady=(0, 14))

        bar_card = self._card(row2)
        bar_card.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(bar_card, text="SKIN BARRIER", font=("Courier", 9),
                     text_color=TEXT_SEC).pack(pady=(14, 0))
        barrier = d.get("skin_barrier", "Strong")
        b_color = SUCCESS if barrier == "Strong" else (ACCENT if barrier == "Moderate" else DANGER)
        ctk.CTkLabel(bar_card, text=f"⬡  {barrier}",
                     font=("Georgia", 22, "italic"), text_color=b_color).pack()
        ctk.CTkLabel(bar_card, text="Skin protection status",
                     font=("Helvetica", 11), text_color=TEXT_SEC).pack(pady=(0, 14))

        # ── Metrics ──
        self._section_header("SKIN METRICS")
        metrics = d.get("metrics", {})
        m_frame = ctk.CTkFrame(self.right, fg_color="transparent")
        m_frame.pack(fill="x", **pad)
        for label, key in [("Hydration", "hydration"), ("Texture", "texture"),
                            ("Pores", "pores"), ("Radiance", "radiance")]:
            mc = self._card(m_frame, width=130)
            mc.pack(side="left", padx=(0, 10), fill="y")
            ctk.CTkLabel(mc, text=label, font=("Courier", 8),
                         text_color=TEXT_SEC).pack(pady=(12, 0))
            ctk.CTkLabel(mc, text=metrics.get(key, "—"),
                         font=("Helvetica", 12), text_color=TEXT_PRI,
                         wraplength=110, justify="center").pack(pady=(4, 12))

        # ── Concerns ──
        self._section_header("VISIBLE CONCERNS")
        concerns = d.get("concerns", [])
        c_frame = ctk.CTkFrame(self.right, fg_color="transparent")
        c_frame.pack(fill="x", **pad)
        for c in concerns:
            sev = c.get("severity", "Mild")
            col = DANGER if sev == "Severe" else (ACCENT if sev == "Moderate" else TEXT_SEC)
            pill = ctk.CTkFrame(c_frame, fg_color=BG_CARD, corner_radius=20,
                                border_width=1, border_color=col)
            pill.pack(side="left", padx=(0, 8), pady=4)
            ctk.CTkLabel(pill, text=f"  {c.get('name','?')}  ·  {sev}  ",
                         font=("Helvetica", 11), text_color=col).pack(pady=6)

        # ── Routine ──
        self._section_header("RECOMMENDED ROUTINE")
        routine = d.get("recommended_routine", {})
        r_frame = ctk.CTkFrame(self.right, fg_color="transparent")
        r_frame.pack(fill="x", **pad)
        steps = [
            ("☀", "AM Cleanser",   "cleanser"),
            ("◎", "Toner",         "toner"),
            ("●", "AM Serum",      "serum_am"),
            ("◗", "PM Serum",      "serum_pm"),
            ("◈", "Moisturiser",   "moisturizer"),
            ("☼", "Sunscreen",     "sunscreen"),
        ]
        for icon, label, key in steps:
            item = routine.get(key, {})
            rc = self._card(r_frame, width=148)
            rc.pack(side="left", padx=(0, 8), fill="y")
            ctk.CTkLabel(rc, text=icon, font=("Helvetica", 20),
                         text_color=ACCENT).pack(pady=(12, 0))
            ctk.CTkLabel(rc, text=label, font=("Courier", 8),
                         text_color=TEXT_SEC).pack()
            ctk.CTkLabel(rc, text=item.get("product", "—"),
                         font=("Helvetica", 11), text_color=TEXT_PRI,
                         wraplength=128, justify="center").pack(pady=4)
            ctk.CTkLabel(rc, text=item.get("note", ""),
                         font=("Helvetica", 9), text_color=TEXT_SEC,
                         wraplength=128, justify="center").pack(pady=(0, 12))

        # ── Ingredients ──
        row_ing = ctk.CTkFrame(self.right, fg_color="transparent")
        row_ing.pack(fill="x", **pad)

        best_card = self._card(row_ing)
        best_card.pack(side="left", fill="both", expand=True, padx=(0, 12))
        ctk.CTkLabel(best_card, text="BEST INGREDIENTS", font=("Courier", 9),
                     text_color=SUCCESS).pack(pady=(14, 4), anchor="w", padx=14)
        for ing in d.get("best_ingredients", []):
            ctk.CTkLabel(best_card, text=f"✓  {ing}",
                         font=("Helvetica", 11), text_color=TEXT_PRI,
                         anchor="w").pack(anchor="w", padx=14, pady=1)
        ctk.CTkLabel(best_card, text="").pack(pady=6)

        avoid_card = self._card(row_ing)
        avoid_card.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(avoid_card, text="AVOID / LIMIT", font=("Courier", 9),
                     text_color=DANGER).pack(pady=(14, 4), anchor="w", padx=14)
        for ing in d.get("avoid_ingredients", []):
            ctk.CTkLabel(avoid_card, text=f"✕  {ing}",
                         font=("Helvetica", 11), text_color=TEXT_PRI,
                         anchor="w").pack(anchor="w", padx=14, pady=1)
        ctk.CTkLabel(avoid_card, text="").pack(pady=6)

        # ── Lifestyle tips ──
        self._section_header("LIFESTYLE TIPS")
        tips_card = self._card(self.right)
        tips_card.pack(fill="x", **pad)
        tips = d.get("lifestyle_tips", [])
        tip_row = ctk.CTkFrame(tips_card, fg_color="transparent")
        tip_row.pack(fill="x", padx=14, pady=14)
        for tip in tips:
            ctk.CTkLabel(tip_row, text=f"◦  {tip}",
                         font=("Helvetica", 12), text_color=TEXT_PRI,
                         anchor="w", wraplength=700).pack(anchor="w", pady=2)

        # ── PDF Export button ──
        self._divider_right()
        ctk.CTkButton(self.right, text="⬇  DOWNLOAD PDF REPORT",
                      font=("Courier", 12, "bold"),
                      fg_color="transparent", hover_color=BG_CARD,
                      border_width=1, border_color=ACCENT,
                      text_color=ACCENT, height=44, corner_radius=8,
                      command=self._export_pdf).pack(padx=24, pady=(4, 24), fill="x")

    # ── PDF Export ────────────────────────────────────────────
    def _export_pdf(self):
        if not self.result_data:
            return
        save_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"skin_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        if not save_path:
            return
        try:
            generate_pdf(self.result_data, self.image_path, save_path)
            messagebox.showinfo("Done!", f"PDF saved to:\n{save_path}")
        except Exception as e:
            messagebox.showerror("PDF Error", str(e))

    # ── Helpers ───────────────────────────────────────────────
    def _card(self, parent, width=None):
        kw = {"fg_color": BG_CARD, "corner_radius": 12,
              "border_width": 1, "border_color": "#2A2A2A"}
        if width:
            kw["width"] = width
        return ctk.CTkFrame(parent, **kw)

    def _section_header(self, text):
        f = ctk.CTkFrame(self.right, fg_color="transparent")
        f.pack(fill="x", padx=24, pady=(18, 4))
        ctk.CTkLabel(f, text=text, font=("Courier", 9),
                     text_color=ACCENT).pack(side="left")

    def _divider_right(self):
        ctk.CTkFrame(self.right, height=1, fg_color="#2A2A2A").pack(
            fill="x", padx=24, pady=16)


# ─── Entry Point ───────────────────────────────────────────────
if __name__ == "__main__":
    app = SkinAnalyzerApp()
    app.mainloop()