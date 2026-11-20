from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# ---------------------------------------------------------
# PulseIQ Analytics - Board Presentation
# Version: 1.0.0
# Reporting period: September 2026
# ---------------------------------------------------------

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "reports"
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "PulseIQ_Board_Presentation_v1.0.0.pptx"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# Theme
NAVY = RGBColor(20, 35, 58)
DARK = RGBColor(34, 49, 70)
TEAL = RGBColor(0, 150, 145)
CYAN = RGBColor(72, 190, 190)
WHITE = RGBColor(255, 255, 255)
LIGHT = RGBColor(242, 246, 249)
MID = RGBColor(105, 120, 138)
GREY = RGBColor(220, 227, 233)
GREEN = RGBColor(42, 145, 103)
AMBER = RGBColor(220, 155, 45)
RED = RGBColor(190, 70, 70)

FONT = "Aptos"


def add_rect(slide, x, y, w, h, fill, radius=False, line=None):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(
        shape_type, Inches(x), Inches(y), Inches(w), Inches(h)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.fill.background() if line is None else None
    if line is not None:
        shape.line.color.rgb = line
    return shape


def add_text(slide, text, x, y, w, h, size=16, color=DARK,
             bold=False, align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(
        Inches(x), Inches(y), Inches(w), Inches(h)
    )
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = Inches(0.04)
    tf.margin_right = Inches(0.04)
    tf.margin_top = Inches(0.02)
    tf.margin_bottom = Inches(0.02)

    p = tf.paragraphs[0]
    p.alignment = align
    p.space_after = Pt(2)
    run = p.add_run()
    run.text = str(text)
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    return box


def add_bullet_list(slide, items, x, y, w, h, size=16, color=DARK):
    box = slide.shapes.add_textbox(
        Inches(x), Inches(y), Inches(w), Inches(h)
    )
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = Inches(0.08)
    tf.margin_top = Inches(0.04)

    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = "• " + item
        p.font.name = FONT
        p.font.size = Pt(size)
        p.font.color.rgb = color
        p.space_after = Pt(12)
    return box


def add_base(title, subtitle="", number=1):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = LIGHT

    add_rect(slide, 0, 0, 13.333, 0.16, TEAL)
    add_text(slide, title, 0.55, 0.38, 12.1, 0.52, 25, NAVY, True)

    if subtitle:
        add_text(slide, subtitle, 0.58, 0.94, 12.0, 0.35, 11, MID)

    add_rect(slide, 0.55, 7.12, 12.2, 0.015, GREY)
    add_text(
        slide, "PULSEIQ ANALYTICS  |  SEPTEMBER 2026",
        0.58, 7.19, 8.5, 0.18, 8, MID
    )
    add_text(
        slide, f"{number:02d} / 10",
        11.7, 7.17, 1.0, 0.2, 8, MID, align=PP_ALIGN.RIGHT
    )
    return slide


def add_card(slide, x, y, w, h, label, value, note="", accent=TEAL):
    add_rect(slide, x, y, w, h, WHITE, True)
    add_rect(slide, x, y, 0.07, h, accent)
    add_text(slide, label.upper(), x + 0.22, y + 0.18, w - 0.4, 0.25,
             10, MID, True)
    add_text(slide, value, x + 0.22, y + 0.55, w - 0.4, 0.55,
             24, NAVY, True)
    if note:
        add_text(slide, note, x + 0.22, y + 1.14, w - 0.4, 0.35,
                 9, MID)


def add_recommendation(slide, text, y=5.75):
    add_rect(slide, 0.7, y, 11.95, 0.85, NAVY, True)
    add_text(slide, "RECOMMENDATION", 0.95, y + 0.13, 2.0, 0.2,
             9, CYAN, True)
    add_text(slide, text, 2.65, y + 0.12, 9.65, 0.55,
             13, WHITE, True)


def add_bar_chart(slide, title, labels, values, x, y, w, h,
                  value_suffix="", max_value=None):
    add_text(slide, title, x, y, w, 0.35, 15, NAVY, True)

    chart_y = y + 0.65
    chart_h = h - 1.15
    chart_x = x + 0.15
    chart_w = w - 0.3

    if max_value is None:
        max_value = max(values) * 1.15

    add_rect(slide, chart_x, chart_y + chart_h, chart_w, 0.015, GREY)

    count = len(values)
    slot = chart_w / count
    bar_w = min(0.72, slot * 0.48)

    for i, (label, value) in enumerate(zip(labels, values)):
        bar_h = max(0.04, (value / max_value) * chart_h)
        bx = chart_x + i * slot + (slot - bar_w) / 2
        by = chart_y + chart_h - bar_h

        bar_color = TEAL if i == count - 1 else CYAN
        add_rect(slide, bx, by, bar_w, bar_h, bar_color, True)

        value_text = f"{value:,.2f}{value_suffix}"
        add_text(slide, value_text, bx - 0.28, by - 0.30,
                 bar_w + 0.56, 0.23, 9, NAVY, True,
                 align=PP_ALIGN.CENTER)
        add_text(slide, label, chart_x + i * slot, chart_y + chart_h + 0.12,
                 slot, 0.3, 10, MID, True, align=PP_ALIGN.CENTER)


def add_line_chart(slide, title, labels, values, x, y, w, h,
                   value_suffix="", min_value=0, max_value=None):
    add_text(slide, title, x, y, w, 0.35, 15, NAVY, True)

    chart_x = x + 0.45
    chart_y = y + 0.7
    chart_w = w - 0.9
    chart_h = h - 1.35

    if max_value is None:
        max_value = max(values) * 1.15

    add_rect(slide, chart_x, chart_y + chart_h, chart_w, 0.015, GREY)

    points = []
    for i, value in enumerate(values):
        px = chart_x + (chart_w * i / max(1, len(values) - 1))
        ratio = (value - min_value) / max(0.0001, max_value - min_value)
        py = chart_y + chart_h - ratio * chart_h
        points.append((px, py))

    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        line = slide.shapes.add_connector(
            1, Inches(x1), Inches(y1), Inches(x2), Inches(y2)
        )
        line.line.color.rgb = TEAL
        line.line.width = Pt(2.5)

    for i, (px, py) in enumerate(points):
        dot = slide.shapes.add_shape(
            MSO_SHAPE.OVAL, Inches(px - 0.07), Inches(py - 0.07),
            Inches(0.14), Inches(0.14)
        )
        dot.fill.solid()
        dot.fill.fore_color.rgb = TEAL
        dot.line.fill.background()

        add_text(slide, f"{values[i]:.2f}{value_suffix}",
                 px - 0.48, py - 0.34, 0.96, 0.22,
                 9, NAVY, True, align=PP_ALIGN.CENTER)
        add_text(slide, labels[i], px - 0.4, chart_y + chart_h + 0.15,
                 0.8, 0.25, 10, MID, True, align=PP_ALIGN.CENTER)


# ---------------------------------------------------------
# SLIDE 1 - TITLE
# ---------------------------------------------------------
slide = prs.slides.add_slide(prs.slide_layouts[6])
slide.background.fill.solid()
slide.background.fill.fore_color.rgb = NAVY

add_rect(slide, 0, 0, 0.18, 7.5, TEAL)
add_text(slide, "PULSEIQ", 0.9, 1.35, 6.5, 0.75, 35, CYAN, True)
add_text(slide, "ANALYTICS", 0.9, 2.05, 7.0, 0.9, 43, WHITE, True)
add_text(slide, "BOARD REVIEW", 0.95, 3.25, 5.5, 0.45, 19, WHITE, True)
add_text(slide, "September 2026 reporting period",
         0.95, 3.85, 7.0, 0.4, 16, RGBColor(195, 210, 222))
add_rect(slide, 0.95, 4.65, 2.2, 0.06, TEAL)
add_text(slide, "Release 1.0.0  |  20 November 2026",
         0.95, 4.95, 7.0, 0.35, 12, RGBColor(195, 210, 222))
add_text(slide, "Workforce • Finance • Operations • Governance",
         0.95, 6.55, 10.5, 0.3, 11, RGBColor(195, 210, 222))


# ---------------------------------------------------------
# SLIDE 2 - EXECUTIVE SNAPSHOT
# ---------------------------------------------------------
slide = add_base(
    "Executive snapshot",
    "September 2026 is the latest available reporting month in the source dataset.",
    2
)

add_card(slide, 0.7, 1.65, 2.25, 1.65, "Headcount", "441",
         "Company workforce", TEAL)
add_card(slide, 3.1, 1.65, 2.25, 1.65, "Revenue", "₹8.03 Cr",
         "September revenue", CYAN)
add_card(slide, 5.5, 1.65, 2.25, 1.65, "Net profit", "₹1.50 Cr",
         "September net profit", GREEN)
add_card(slide, 7.9, 1.65, 2.25, 1.65, "Operating margin", "18.67%",
         "Down from 27.16% in August", AMBER)
add_card(slide, 10.3, 1.65, 2.25, 1.65, "Attendance", "95.19%",
         "Above 94% reference target", TEAL)

add_rect(slide, 0.8, 3.75, 11.7, 1.35, WHITE, True)
add_text(slide, "BOARD TAKEAWAY", 1.05, 3.98, 2.2, 0.25,
         10, TEAL, True)
add_text(
    slide,
    "Workforce and attendance indicators are positive. "
    "The key financial concern is the fall in operating margin "
    "from August to September. Receivables and data-quality exceptions "
    "also require management attention.",
    1.05, 4.32, 11.0, 0.55, 15, NAVY, True
)

add_text(
    slide,
    "Reporting basis: source workbook loaded into the PulseIQ warehouse. "
    "Figures are sample business data, not live operational feeds.",
    0.9, 5.55, 11.5, 0.45, 10, MID
)


# ---------------------------------------------------------
# SLIDE 3 - WORKFORCE
# ---------------------------------------------------------
slide = add_base(
    "Workforce: steady growth and strong attendance",
    "Company-level monthly KPIs | July–September 2026",
    3
)

add_line_chart(
    slide, "Headcount trend",
    ["Jul", "Aug", "Sep"], [421, 427, 441],
    0.9, 1.55, 5.5, 3.6, "", 400, 450
)

add_line_chart(
    slide, "Attendance rate",
    ["Jul", "Aug", "Sep"], [94.10, 94.25, 95.19],
    6.8, 1.55, 5.5, 3.6, "%", 93, 96
)

add_text(
    slide,
    "September attrition: 0.70%  |  Hires: 17  |  Exits: 3",
    1.0, 5.25, 11.3, 0.3, 13, NAVY, True
)
add_recommendation(
    slide,
    "Maintain attendance above the 94% reference target and review "
    "retention patterns as headcount expands."
)


# ---------------------------------------------------------
# SLIDE 4 - FINANCIAL PERFORMANCE
# ---------------------------------------------------------
slide = add_base(
    "Finance: margin pressure needs attention",
    "Company-level financial performance | July–September 2026",
    4
)

add_bar_chart(
    slide, "Revenue (₹ Crore)",
    ["Jul", "Aug", "Sep"], [7.0034, 8.14594, 8.02682],
    0.8, 1.45, 5.6, 3.7, "", 9
)

add_bar_chart(
    slide, "Net profit (₹ Crore)",
    ["Jul", "Aug", "Sep"], [0.93886, 2.21266, 1.49860],
    6.8, 1.45, 5.6, 3.7, "", 2.5
)

add_rect(slide, 0.95, 5.15, 5.3, 0.45, WHITE, True)
add_text(slide, "Operating margin: 13.41% → 27.16% → 18.67%",
         1.12, 5.25, 5.0, 0.22, 11, NAVY, True)
add_rect(slide, 6.75, 5.15, 5.4, 0.45, WHITE, True)
add_text(slide, "Payroll cost: 69.17% of September revenue",
         6.95, 5.25, 5.0, 0.22, 11, NAVY, True)

add_recommendation(
    slide,
    "Investigate the August-to-September margin decline of 8.49 percentage "
    "points, focusing on expense categories and payroll cost."
)


# ---------------------------------------------------------
# SLIDE 5 - RECEIVABLES
# ---------------------------------------------------------
slide = add_base(
    "Receivables: overdue balances need focused collection",
    "September 2026 overdue receivables view",
    5
)

add_card(slide, 0.95, 1.8, 3.3, 1.8, "Overdue receivables",
         "₹2.71 Cr", "Aggregated overdue amount", AMBER)
add_card(slide, 4.55, 1.8, 3.3, 1.8, "Clients with overdue balances",
         "9", "September 2026", TEAL)
add_card(slide, 8.15, 1.8, 3.3, 1.8, "Collection priority",
         "High", "Review balances and aging", RED)

add_rect(slide, 0.95, 4.15, 11.4, 1.1, WHITE, True)
add_text(slide, "MANAGEMENT OBSERVATION", 1.2, 4.35, 2.5, 0.25,
         10, TEAL, True)
add_text(
    slide,
    "The September overdue balance is material. The current summary "
    "identifies nine clients, but this view does not provide a historical "
    "monthly trend.",
    1.2, 4.7, 10.7, 0.4, 13, NAVY
)

add_recommendation(
    slide,
    "Prioritize the largest overdue balances, assign collection owners, "
    "and review invoice aging and follow-up status."
)


# ---------------------------------------------------------
# SLIDE 6 - OPERATIONS
# ---------------------------------------------------------
slide = add_base(
    "Operations: early indicators are encouraging",
    "Averages across 16 records through 7 September 2026; not full-month totals.",
    6
)

add_card(slide, 1.0, 1.8, 4.8, 1.8, "Task completion",
         "86.23%", "Average across 16 records", TEAL)
add_card(slide, 7.0, 1.8, 4.8, 1.8, "On-time delivery",
         "94.19%", "Average across 16 records", GREEN)

add_rect(slide, 1.0, 4.15, 4.8, 0.35, GREY, True)
add_rect(slide, 1.0, 4.15, 4.14, 0.35, TEAL, True)
add_text(slide, "Task completion", 1.0, 4.62, 4.8, 0.25,
         11, NAVY, True, align=PP_ALIGN.CENTER)

add_rect(slide, 7.0, 4.15, 4.8, 0.35, GREY, True)
add_rect(slide, 7.0, 4.15, 4.52, 0.35, GREEN, True)
add_text(slide, "On-time delivery", 7.0, 4.62, 4.8, 0.25,
         11, NAVY, True, align=PP_ALIGN.CENTER)

add_text(
    slide,
    "Interpretation: these are averages from the available records up to "
    "7 September. They should not be presented as complete September "
    "company-wide results.",
    1.0, 5.12, 11.2, 0.35, 10, MID
)

add_recommendation(
    slide,
    "Review team-level delivery bottlenecks and track completion and "
    "on-time delivery consistently across the full reporting month."
)


# ---------------------------------------------------------
# SLIDE 7 - AI ANOMALIES
# ---------------------------------------------------------
slide = add_base(
    "AI signals: estimated exposure increased in September",
    "Model-generated anomaly flags and estimated money at risk",
    7
)

add_bar_chart(
    slide, "Estimated money at risk (₹ Lakh)",
    ["Jul", "Aug", "Sep"], [10.96, 17.45, 32.98],
    0.9, 1.55, 6.0, 3.8, "", 38
)

add_card(slide, 7.45, 1.85, 4.0, 1.65, "September records scored",
         "25", "Model-scored records", TEAL)
add_card(slide, 7.45, 3.75, 4.0, 1.65, "Records flagged",
         "25", "All 25 scored records flagged", AMBER)

add_text(
    slide,
    "Important: estimated exposure is a model output. A flag is not proof "
    "of fraud, error, or a confirmed financial loss.",
    1.0, 5.35, 11.2, 0.3, 11, RED, True
)

add_recommendation(
    slide,
    "Prioritize high-value flags for human review and record the outcome "
    "before taking financial or employee-related action."
)


# ---------------------------------------------------------
# SLIDE 8 - DATA QUALITY
# ---------------------------------------------------------
slide = add_base(
    "Data quality: reconciliations pass, exceptions remain",
    "Latest pipeline validation results",
    8
)

add_card(slide, 0.85, 1.65, 2.7, 1.55, "Passed checks",
         "3", "Of 14 DQ checks", GREEN)
add_card(slide, 3.75, 1.65, 2.7, 1.55, "Warnings",
         "7", "Require review", AMBER)
add_card(slide, 6.65, 1.65, 2.7, 1.55, "Failed checks",
         "4", "Require remediation", RED)
add_card(slide, 9.55, 1.65, 2.7, 1.55, "Metric spot-checks",
         "3,069", "All passed", TEAL)

add_rect(slide, 0.9, 3.65, 11.5, 1.35, WHITE, True)
add_text(slide, "RECONCILIATION AND CONTROL EVIDENCE",
         1.15, 3.85, 5.0, 0.25, 10, TEAL, True)
add_bullet_list(
    slide,
    [
        "33 of 33 source worksheets reconciled through row audit.",
        "31 of 31 primary-key tables enforced.",
        "Four DQ failures: payroll-ledger reconciliation, duplicate payroll, "
        "orphan employees and employee-history overlap.",
        "Two leave records were rejected during ETL."
    ],
    1.15, 4.18, 10.8, 0.95, 10, NAVY
)

add_recommendation(
    slide,
    "Resolve the four failed controls, review seven warnings, and retain "
    "reconciliation evidence before promoting future releases."
)


# ---------------------------------------------------------
# SLIDE 9 - ARCHITECTURE AND DELIVERY
# ---------------------------------------------------------
slide = add_base(
    "PulseIQ delivery: governed data from source to decision",
    "Current solution architecture and deployment status",
    9
)

stages = [
    ("SOURCE", "33-sheet Excel\nworkbook"),
    ("RAW", "Source data\nloaded to DuckDB"),
    ("ETL", "Clean, validate\nand quarantine"),
    ("WAREHOUSE", "Staging and\nstar schema"),
    ("METRICS", "28 governed\nmetric definitions"),
    ("CONSUMPTION", "Dashboard, API\nand Excel reports"),
]

x_positions = [0.55, 2.65, 4.75, 6.85, 8.95, 11.05]
for i, (heading, detail) in enumerate(stages):
    add_rect(slide, x_positions[i], 2.0, 1.75, 1.45, NAVY if i != 4 else TEAL, True)
    add_text(slide, heading, x_positions[i] + 0.08, 2.22, 1.59, 0.25,
             10, CYAN if i != 4 else WHITE, True, align=PP_ALIGN.CENTER)
    add_text(slide, detail, x_positions[i] + 0.08, 2.65, 1.59, 0.55,
             10, WHITE, False, align=PP_ALIGN.CENTER)

    if i < len(stages) - 1:
        add_text(slide, "→", x_positions[i] + 1.77, 2.55, 0.3, 0.3,
                 18, TEAL, True, align=PP_ALIGN.CENTER)

add_rect(slide, 0.85, 4.15, 5.55, 1.1, WHITE, True)
add_text(slide, "PUBLIC DASHBOARD", 1.1, 4.35, 2.5, 0.25,
         10, TEAL, True)
add_text(
    slide,
    "https://arpita-pulseiq-dashboard.streamlit.app/",
    1.1, 4.72, 5.0, 0.25, 10, NAVY
)

add_rect(slide, 6.75, 4.15, 5.55, 1.1, WHITE, True)
add_text(slide, "API AND REPORTING", 7.0, 4.35, 2.5, 0.25,
         10, TEAL, True)
add_text(
    slide,
    "FastAPI tested locally; monthly Excel report workflow available.",
    7.0, 4.72, 5.0, 0.3, 10, NAVY
)

add_text(
    slide,
    "Current limitation: the deployed dashboard does not yet receive "
    "automated scheduled data refreshes. The API is not publicly hosted.",
    1.0, 5.55, 11.3, 0.35, 10, RED, True
)


# ---------------------------------------------------------
# SLIDE 10 - BOARD ACTION PLAN
# ---------------------------------------------------------
slide = add_base(
    "Board priorities and next actions",
    "Recommended focus areas following the September 2026 review",
    10
)

actions = [
    ("01", "PROTECT MARGIN",
     "Investigate the 8.49 percentage-point margin decline from August."),
    ("02", "ACCELERATE COLLECTIONS",
     "Assign owners to nine overdue client balances totalling ₹2.71 Cr."),
    ("03", "REMEDIATE DATA QUALITY",
     "Close four failed controls and review seven warning conditions."),
    ("04", "VALIDATE AI FLAGS",
     "Review the ₹32.98 lakh estimated exposure; confirm before action."),
    ("05", "STRENGTHEN DELIVERY",
     "Implement scheduled dashboard refresh and public API hosting.")
]

for i, (num, heading, detail) in enumerate(actions):
    y = 1.45 + i * 0.82
    add_rect(slide, 0.9, y, 11.5, 0.65, WHITE, True)
    add_text(slide, num, 1.1, y + 0.16, 0.55, 0.25,
             13, TEAL, True)
    add_text(slide, heading, 1.85, y + 0.1, 2.65, 0.25,
             11, NAVY, True)
    add_text(slide, detail, 4.45, y + 0.1, 7.55, 0.38,
             11, DARK)

add_rect(slide, 0.9, 5.85, 11.5, 0.7, NAVY, True)
add_text(
    slide,
    "BOARD DECISION: Prioritize margin recovery, collections and data-quality "
    "remediation while approving the next phase of platform automation.",
    1.15, 6.02, 11.0, 0.35, 12, WHITE, True,
    align=PP_ALIGN.CENTER
)


# ---------------------------------------------------------
# SAVE PRESENTATION
# ---------------------------------------------------------
prs.save(OUTPUT_FILE)

print("Board presentation created successfully.")
print(f"File: {OUTPUT_FILE}")
print(f"Slides: {len(prs.slides)}")
print(f"Size: {OUTPUT_FILE.stat().st_size:,} bytes")