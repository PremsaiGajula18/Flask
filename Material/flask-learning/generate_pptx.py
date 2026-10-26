from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
import copy

# ── Colors ──
BG       = RGBColor(0x0B, 0x0F, 0x19)
BG2      = RGBColor(0x11, 0x18, 0x27)
BG3      = RGBColor(0x1E, 0x29, 0x3B)
WHITE    = RGBColor(0xFF, 0xFF, 0xFF)
TEXT     = RGBColor(0xE2, 0xE8, 0xF0)
TEXT2    = RGBColor(0x94, 0xA3, 0xB8)
TEXT3    = RGBColor(0x64, 0x74, 0x8B)
ACCENT   = RGBColor(0x3B, 0x82, 0xF6)
GREEN    = RGBColor(0x22, 0xC5, 0x5E)
RED      = RGBColor(0xEF, 0x44, 0x44)
ORANGE   = RGBColor(0xF5, 0x9E, 0x0B)
PURPLE   = RGBColor(0xA7, 0x8B, 0xFA)
CYAN     = RGBColor(0x06, 0xB6, 0xD4)
PINK     = RGBColor(0xF4, 0x72, 0xB6)
CODE_BG  = RGBColor(0x16, 0x1B, 0x22)
BORDER   = RGBColor(0x2D, 0x3A, 0x4F)

prs = Presentation()
prs.slide_width  = Inches(13.333)
prs.slide_height = Inches(7.5)

W = prs.slide_width
H = prs.slide_height

# ── Helpers ──
def set_slide_bg(slide, color):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color

def add_shape(slide, left, top, width, height, fill_color=None, border_color=None, border_width=Pt(1), radius=None):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color or BG3
    if border_color:
        shape.line.color.rgb = border_color
        shape.line.width = border_width
    else:
        shape.line.fill.background()
    # Rounded corners
    if radius:
        shape.adjustments[0] = radius
    else:
        shape.adjustments[0] = 0.05
    return shape

def add_text(slide, left, top, width, height, text, font_size=18, color=TEXT, bold=False, alignment=PP_ALIGN.LEFT, font_name='Segoe UI'):
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.color.rgb = color
    p.font.bold = bold
    p.font.name = font_name
    p.alignment = alignment
    return txBox

def add_rich_text(slide, left, top, width, height, lines, font_size=16, line_spacing=1.4, font_name='Segoe UI'):
    """lines = [(text, color, bold), ...]"""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    for i, (text, color, bold) in enumerate(lines):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = text
        p.font.size = Pt(font_size)
        p.font.color.rgb = color
        p.font.bold = bold
        p.font.name = font_name
        p.space_after = Pt(font_size * 0.4)
        if line_spacing:
            p.line_spacing = Pt(font_size * line_spacing)
    return txBox

def add_bullet_list(slide, left, top, width, height, items, font_size=16, icon_items=None, color=TEXT):
    """items = list of strings. icon_items = list of icon strings (emoji) or None."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        icon = icon_items[i] if icon_items else "▸"
        p.text = f"{icon}  {item}"
        p.font.size = Pt(font_size)
        p.font.color.rgb = color
        p.font.name = 'Segoe UI'
        p.space_after = Pt(font_size * 0.5)
        p.line_spacing = Pt(font_size * 1.5)
    return txBox

def add_code_block(slide, left, top, width, height, code_text, font_size=13):
    shape = add_shape(slide, left, top, width, height, fill_color=CODE_BG, border_color=BORDER)
    tf = shape.text_frame
    tf.word_wrap = True
    tf.margin_left = Pt(16)
    tf.margin_right = Pt(16)
    tf.margin_top = Pt(12)
    tf.margin_bottom = Pt(12)
    lines = code_text.split('\n')
    for i, line in enumerate(lines):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = line
        p.font.size = Pt(font_size)
        p.font.color.rgb = TEXT
        p.font.name = 'Cascadia Code'
        p.space_after = Pt(2)
        p.line_spacing = Pt(font_size * 1.6)
    return shape

def add_tag(slide, left, top, text, color=ACCENT):
    add_text(slide, left, top, Inches(5), Pt(20), text, font_size=10, color=color, bold=True)

def add_slide_number(slide, num, total=6):
    add_text(slide, W - Inches(1.2), H - Inches(0.5), Inches(1), Pt(16),
             f"{num} / {total}", font_size=9, color=TEXT3, alignment=PP_ALIGN.RIGHT)

def add_table(slide, left, top, width, rows_data, col_widths=None, font_size=12):
    """rows_data = list of lists. First row = header."""
    n_rows = len(rows_data)
    n_cols = len(rows_data[0])
    table_shape = slide.shapes.add_table(n_rows, n_cols, left, top, width, Inches(0.35 * n_rows))
    table = table_shape.table

    if col_widths:
        for i, w in enumerate(col_widths):
            table.columns[i].width = w

    for r, row in enumerate(rows_data):
        for c, cell_text in enumerate(row):
            cell = table.cell(r, c)
            cell.text = cell_text
            p = cell.text_frame.paragraphs[0]
            p.font.size = Pt(font_size)
            p.font.name = 'Segoe UI'

            # Style
            fill = cell.fill
            fill.solid()
            if r == 0:
                fill.fore_color.rgb = BG3
                p.font.color.rgb = ACCENT
                p.font.bold = True
            else:
                fill.fore_color.rgb = BG2 if r % 2 == 0 else BG
                p.font.color.rgb = TEXT2

            # Borders – set via XML manipulation
            cell.margin_left = Pt(8)
            cell.margin_right = Pt(8)
            cell.margin_top = Pt(6)
            cell.margin_bottom = Pt(6)
    return table_shape

def add_flow_arrow(slide, left, top, direction='down', size=Inches(0.25)):
    if direction == 'down':
        add_text(slide, left, top, size, size, "↓", font_size=14, color=TEXT3, alignment=PP_ALIGN.CENTER)
    elif direction == 'right':
        add_text(slide, left, top, size, size, "→", font_size=14, color=TEXT3, alignment=PP_ALIGN.CENTER)

def add_flow_node(slide, left, top, width, text, highlight=False):
    h = Inches(0.38)
    color = BG3
    border = BORDER
    text_color = TEXT
    if highlight:
        border = ACCENT
        text_color = ACCENT
    shape = add_shape(slide, left, top, width, h, fill_color=color, border_color=border, border_width=Pt(1.5))
    tf = shape.text_frame
    tf.word_wrap = True
    tf.margin_left = Pt(8)
    tf.margin_right = Pt(8)
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(11)
    p.font.color.rgb = text_color
    p.font.bold = True
    p.font.name = 'Segoe UI'
    p.alignment = PP_ALIGN.CENTER
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    return shape


# ════════════════════════════════════════════════════════════════
# SLIDE 1 — Title + Agenda
# ════════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank
set_slide_bg(slide, BG)

# Flask icon
add_text(slide, Inches(0), Inches(1.0), W, Inches(0.8), "🧪", font_size=52, color=WHITE, alignment=PP_ALIGN.CENTER)

# Title
add_text(slide, Inches(0), Inches(1.9), W, Inches(1.0),
         "Flask Fundamentals", font_size=48, color=WHITE, bold=True, alignment=PP_ALIGN.CENTER)

# Subtitle
add_text(slide, Inches(0), Inches(2.85), W, Inches(0.5),
         "Step-by-step introduction to Python Flask", font_size=18, color=TEXT2, alignment=PP_ALIGN.CENTER)

# Agenda items (2 columns)
agenda_left = [("01", "Basic Flask App"), ("02", "Web Architecture"), ("03", "Debug Mode")]
agenda_right = [("04", "app.route()"), ("05", "GET & POST"), ("06", "Dynamic Routes & url_for()")]

for i, (num, title) in enumerate(agenda_left):
    y = Inches(3.8) + Inches(i * 0.55)
    add_text(slide, Inches(4.2), y, Inches(0.5), Inches(0.4), num, font_size=14, color=ACCENT, bold=True)
    add_text(slide, Inches(4.75), y, Inches(2.5), Inches(0.4), title, font_size=14, color=TEXT)

for i, (num, title) in enumerate(agenda_right):
    y = Inches(3.8) + Inches(i * 0.55)
    add_text(slide, Inches(7.5), y, Inches(0.5), Inches(0.4), num, font_size=14, color=ACCENT, bold=True)
    add_text(slide, Inches(8.05), y, Inches(3), Inches(0.4), title, font_size=14, color=TEXT)

add_slide_number(slide, 1)


# ════════════════════════════════════════════════════════════════
# SLIDE 2 — Basic Flask App
# ════════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_slide_bg(slide, BG)
add_tag(slide, Inches(0.6), Inches(0.4), "01 · BASIC FLASK APP")
add_text(slide, Inches(0.6), Inches(0.7), Inches(8), Inches(0.6),
         "What is Flask & Your First App", font_size=28, color=WHITE, bold=True)

# LEFT — Code block
add_text(slide, Inches(0.6), Inches(1.45), Inches(3), Inches(0.3), "app.py", font_size=11, color=ACCENT, bold=True)
code = """from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Hello, Flask!"

if __name__ == "__main__":
    app.run(debug=True)"""
add_code_block(slide, Inches(0.6), Inches(1.75), Inches(5.5), Inches(3.6), code, font_size=13)

# Install / Run badges
add_shape(slide, Inches(0.6), Inches(5.55), Inches(1.7), Inches(0.35), fill_color=BG3, border_color=BORDER)
add_text(slide, Inches(0.7), Inches(5.57), Inches(1.5), Inches(0.3), "$ pip install flask", font_size=10, color=GREEN, font_name='Cascadia Code')

add_shape(slide, Inches(2.5), Inches(5.55), Inches(1.5), Inches(0.35), fill_color=BG3, border_color=BORDER)
add_text(slide, Inches(2.6), Inches(5.57), Inches(1.3), Inches(0.3), "$ python app.py", font_size=10, color=GREEN, font_name='Cascadia Code')

add_shape(slide, Inches(4.2), Inches(5.55), Inches(1.7), Inches(0.35), fill_color=BG3, border_color=BORDER)
add_text(slide, Inches(4.3), Inches(5.57), Inches(1.5), Inches(0.3), "→ localhost:5000", font_size=10, color=CYAN, font_name='Cascadia Code')

# RIGHT — What is Flask + Line by Line
add_text(slide, Inches(6.6), Inches(1.45), Inches(3), Inches(0.3), "WHAT IS FLASK?", font_size=11, color=ACCENT, bold=True)
add_bullet_list(slide, Inches(6.6), Inches(1.8), Inches(6), Inches(1.5),
    ["Micro web framework for Python", "Lightweight, flexible, extensible", "Used by Netflix, Reddit, Lyft"],
    font_size=14, icon_items=["🐍", "📦", "🏢"])

add_text(slide, Inches(6.6), Inches(3.3), Inches(3), Inches(0.3), "LINE-BY-LINE", font_size=11, color=ACCENT, bold=True)

explanations = [
    ("Flask(__name__)", "Create app instance"),
    ("@app.route(\"/\")", "Map URL to function"),
    ("return \"Hello...\"", "Send browser response"),
    ("app.run(debug)", "Start dev server"),
]
for i, (code_t, desc) in enumerate(explanations):
    y = Inches(3.65) + Inches(i * 0.48)
    shape = add_shape(slide, Inches(6.6), y, Inches(6), Inches(0.4), fill_color=BG3, border_color=ACCENT, border_width=Pt(0.5))
    add_text(slide, Inches(6.75), y + Pt(2), Inches(2.3), Inches(0.35), code_t, font_size=10, color=PURPLE, font_name='Cascadia Code')
    add_text(slide, Inches(9.1), y + Pt(2), Inches(3.2), Inches(0.35), desc, font_size=11, color=TEXT2)

# Browser output
add_text(slide, Inches(6.6), Inches(5.6), Inches(2), Inches(0.3), "BROWSER OUTPUT", font_size=11, color=ACCENT, bold=True)
shape = add_shape(slide, Inches(8.8), Inches(5.5), Inches(3.3), Inches(0.45), fill_color=RGBColor(0xFF,0xFF,0xFF), border_color=BORDER)
tf = shape.text_frame
p = tf.paragraphs[0]
p.text = "Hello, Flask!"
p.font.size = Pt(14)
p.font.color.rgb = RGBColor(0, 0, 0)
p.font.bold = True
p.font.name = 'Segoe UI'
p.alignment = PP_ALIGN.CENTER
tf.vertical_anchor = MSO_ANCHOR.MIDDLE

add_slide_number(slide, 2)


# ════════════════════════════════════════════════════════════════
# SLIDE 3 — Web Architecture + Debug Mode
# ════════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_slide_bg(slide, BG)
add_tag(slide, Inches(0.6), Inches(0.4), "02 · WEB ARCHITECTURE   |   03 · DEBUG MODE")
add_text(slide, Inches(0.6), Inches(0.7), Inches(10), Inches(0.6),
         "Request–Response Flow & Debug Mode", font_size=28, color=WHITE, bold=True)

# LEFT — Architecture flow
add_text(slide, Inches(0.6), Inches(1.45), Inches(4), Inches(0.3), "REQUEST → RESPONSE CYCLE", font_size=11, color=ACCENT, bold=True)

flow_items = [
    ("🌐 Browser (Client)", True),
    ("📨 HTTP Request", False),
    ("🧪 Flask Application", True),
    ("🛤️ @app.route() → 🐍 Function", False),
    ("📩 HTTP Response", False),
    ("🌐 Browser (Displays)", True),
]
node_w = Inches(4.2)
start_x = Inches(0.8)
start_y = Inches(1.85)
for i, (label, hl) in enumerate(flow_items):
    y = start_y + Inches(i * 0.58)
    add_flow_node(slide, start_x, y, node_w, label, highlight=hl)
    if i < len(flow_items) - 1:
        add_flow_arrow(slide, start_x + node_w / 2 - Inches(0.12), y + Inches(0.38), 'down')

# Request/Response details
add_bullet_list(slide, Inches(0.8), Inches(5.5), Inches(5), Inches(0.8),
    ["Request: method, URL, headers, body", "Response: status code, headers, body"],
    font_size=12, icon_items=["📨", "📩"], color=TEXT2)

# RIGHT — Debug Mode
add_text(slide, Inches(6.8), Inches(1.45), Inches(4), Inches(0.3), "DEBUG MODE", font_size=11, color=ACCENT, bold=True)

debug_code = """# Development
app.run(debug=True)

# Production
app.run(debug=False)"""
add_code_block(slide, Inches(6.8), Inches(1.8), Inches(5.5), Inches(1.75), debug_code, font_size=12)

# Dev vs Prod table
table_data = [
    ["Feature", "debug=True", "debug=False"],
    ["Auto-reload", "✅ Yes", "❌ No"],
    ["Error details", "✅ Full traceback", "❌ Generic error"],
    ["Debugger", "✅ Interactive", "❌ Disabled"],
    ["Performance", "Slower", "Faster"],
    ["Security", "⚠️ Risky", "✅ Safe"],
]
add_table(slide, Inches(6.8), Inches(3.75), Inches(5.5), table_data, font_size=11)

# Warning
warn_shape = add_shape(slide, Inches(6.8), Inches(5.95), Inches(5.5), Inches(0.4), fill_color=RGBColor(0x2D, 0x10, 0x10), border_color=RED, border_width=Pt(1))
add_text(slide, Inches(6.95), Inches(5.97), Inches(5.2), Inches(0.35),
         "⚠️  Never use debug=True in production — allows code execution!", font_size=11, color=RED)

add_slide_number(slide, 3)


# ════════════════════════════════════════════════════════════════
# SLIDE 4 — app.route()
# ════════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_slide_bg(slide, BG)
add_tag(slide, Inches(0.6), Inches(0.4), "04 · APP.ROUTE()")
add_text(slide, Inches(0.6), Inches(0.7), Inches(10), Inches(0.6),
         "Routing — Mapping URLs to Functions", font_size=28, color=WHITE, bold=True)

# LEFT — Code
add_text(slide, Inches(0.6), Inches(1.45), Inches(4), Inches(0.3), "MULTIPLE ROUTES", font_size=11, color=ACCENT, bold=True)
routes_code = """@app.route("/")
def home():
    return "Home Page"

@app.route("/about")
def about():
    return "About Page"

@app.route("/contact")
def contact():
    return "Contact Page" """
add_code_block(slide, Inches(0.6), Inches(1.8), Inches(5.5), Inches(3.8), routes_code, font_size=13)

# Flow
flow_labels = ["URL", "Route", "Function", "Response"]
fx = Inches(0.8)
for i, label in enumerate(flow_labels):
    hl = (i == 3)
    add_flow_node(slide, fx, Inches(5.85), Inches(1.1), label, highlight=hl)
    if i < len(flow_labels) - 1:
        add_text(slide, fx + Inches(1.1), Inches(5.85), Inches(0.3), Inches(0.38), "→", font_size=14, color=TEXT3, alignment=PP_ALIGN.CENTER)
    fx += Inches(1.4)

# RIGHT — How it works + Table
add_text(slide, Inches(6.8), Inches(1.45), Inches(4), Inches(0.3), "HOW IT WORKS", font_size=11, color=ACCENT, bold=True)
add_bullet_list(slide, Inches(6.8), Inches(1.8), Inches(6), Inches(1.5),
    ["Route maps URL to function", "Uses Python decorator syntax", "URLs must start with /", "Each function needs unique name"],
    font_size=14, icon_items=["🛤️", " @ ", " / ", "📛"])

add_text(slide, Inches(6.8), Inches(3.55), Inches(4), Inches(0.3), "ROUTE MAPPING", font_size=11, color=ACCENT, bold=True)
route_table = [
    ["URL", "Function", "Response"],
    ["/", "home()", "Home Page"],
    ["/about", "about()", "About Page"],
    ["/contact", "contact()", "Contact Page"],
    ["/unknown", "—", "404 Not Found"],
]
add_table(slide, Inches(6.8), Inches(3.85), Inches(5.5), route_table, font_size=11)

add_slide_number(slide, 4)


# ════════════════════════════════════════════════════════════════
# SLIDE 5 — GET & POST
# ════════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_slide_bg(slide, BG)
add_tag(slide, Inches(0.6), Inches(0.4), "05 · GET & POST")
add_text(slide, Inches(0.6), Inches(0.7), Inches(10), Inches(0.6),
         "HTTP Methods & Form Handling", font_size=28, color=WHITE, bold=True)

# COL 1 — GET
add_text(slide, Inches(0.6), Inches(1.45), Inches(3), Inches(0.3), "GET — RETRIEVE DATA", font_size=11, color=CYAN, bold=True)
get_code = """@app.route("/login",
    methods=["GET"])
def login():
    return "Login Page" """
add_code_block(slide, Inches(0.6), Inches(1.8), Inches(3.7), Inches(1.55), get_code, font_size=11)
add_bullet_list(slide, Inches(0.6), Inches(3.5), Inches(3.7), Inches(1.2),
    ["Data visible in URL", "Bookmarkable, ~2 KB limit", "Default HTTP method"],
    font_size=12, icon_items=["📥", "🔖", "🔄"], color=TEXT2)

# COL 2 — POST
add_text(slide, Inches(4.7), Inches(1.45), Inches(3), Inches(0.3), "POST — SUBMIT DATA", font_size=11, color=PINK, bold=True)
post_code = """from flask import request

@app.route("/login",
    methods=["POST"])
def login():
    u = request.form.get("username")
    return f"Welcome {u}" """
add_code_block(slide, Inches(4.7), Inches(1.8), Inches(3.9), Inches(2.2), post_code, font_size=11)
add_bullet_list(slide, Inches(4.7), Inches(4.15), Inches(3.9), Inches(1.0),
    ["Data hidden in body", "Use for sensitive data", "No practical size limit"],
    font_size=12, icon_items=["📤", "🔒", "📦"], color=TEXT2)

# COL 3 — Comparison table
add_text(slide, Inches(9.0), Inches(1.45), Inches(4), Inches(0.3), "COMPARISON", font_size=11, color=ACCENT, bold=True)
comp_table = [
    ["Feature", "GET", "POST"],
    ["Purpose", "Retrieve", "Submit"],
    ["Data in", "URL", "Body"],
    ["Visible?", "✅ Yes", "❌ No"],
    ["Bookmark", "✅ Yes", "❌ No"],
    ["Size limit", "~2 KB", "None"],
    ["Use case", "Search", "Login"],
]
add_table(slide, Inches(9.0), Inches(1.8), Inches(3.8), comp_table, font_size=10)

# Key objects
add_text(slide, Inches(9.0), Inches(4.5), Inches(4), Inches(0.3), "KEY OBJECTS", font_size=11, color=ACCENT, bold=True)
add_bullet_list(slide, Inches(9.0), Inches(4.85), Inches(3.8), Inches(0.8),
    ["request.form → POST data", "request.args → GET data", "name= matches Python key"],
    font_size=12, icon_items=["📋", "🔍", "📛"], color=TEXT2)

add_slide_number(slide, 5)


# ════════════════════════════════════════════════════════════════
# SLIDE 6 — Dynamic Routes + url_for() + Summary
# ════════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_slide_bg(slide, BG)
add_tag(slide, Inches(0.6), Inches(0.4), "06 · DYNAMIC ROUTES   |   07 · URL_FOR()   |   SUMMARY")
add_text(slide, Inches(0.6), Inches(0.7), Inches(12), Inches(0.6),
         "Dynamic Routes, url_for() & Complete Flow", font_size=28, color=WHITE, bold=True)

# COL 1 — Dynamic Routes
add_text(slide, Inches(0.6), Inches(1.45), Inches(3), Inches(0.3), "DYNAMIC ROUTES", font_size=11, color=ACCENT, bold=True)
dyn_code = """@app.route("/student/<name>")
def student(name):
    return f"Name: {name}"

@app.route("/id/<int:id>")
def by_id(id):
    return f"ID: {id}" """
add_code_block(slide, Inches(0.6), Inches(1.8), Inches(3.7), Inches(2.3), dyn_code, font_size=11)

converter_table = [
    ["Converter", "Accepts"],
    ["<name>", "String (default)"],
    ["<int:id>", "Integer only"],
    ["<float:x>", "Decimal number"],
    ["<path:p>", "Text with slashes"],
]
add_table(slide, Inches(0.6), Inches(4.3), Inches(3.7), converter_table, font_size=10)

# COL 2 — url_for()
add_text(slide, Inches(4.7), Inches(1.45), Inches(3), Inches(0.3), "URL_FOR()", font_size=11, color=ACCENT, bold=True)
uf_code = """from flask import url_for

url_for("home")
# → "/"

url_for("student", name="Ravi")
# → "/student/Ravi" """
add_code_block(slide, Inches(4.7), Inches(1.8), Inches(3.9), Inches(2.3), uf_code, font_size=11)

add_bullet_list(slide, Inches(4.7), Inches(4.3), Inches(3.9), Inches(1.6),
    ["Uses function name, not URL", "URLs auto-update on change", "Catches typos at runtime", "Escapes special characters"],
    font_size=12, icon_items=["📛", "🔄", "🛡️", "🔗"], color=TEXT2)

# COL 3 — Final Flow + Checklist
add_text(slide, Inches(9.0), Inches(1.45), Inches(4), Inches(0.3), "COMPLETE FLASK FLOW", font_size=11, color=ACCENT, bold=True)

final_flow = [
    ("🌐 Browser", True),
    ("GET / POST Request", False),
    ("@app.route()", False),
    ("View Function", False),
    ("url_for() + Response", False),
    ("🌐 Browser", True),
]
node_w2 = Inches(3.2)
sx = Inches(9.2)
for i, (label, hl) in enumerate(final_flow):
    y = Inches(1.85) + Inches(i * 0.46)
    add_flow_node(slide, sx, y, node_w2, label, highlight=hl)
    if i < len(final_flow) - 1:
        add_flow_arrow(slide, sx + node_w2 / 2 - Inches(0.12), y + Inches(0.36), 'down')

# Checklist
add_text(slide, Inches(9.0), Inches(4.7), Inches(4), Inches(0.3), "✅ YOU SHOULD KNOW", font_size=11, color=GREEN, bold=True)
checklist = [
    "✅  Create & run Flask app",
    "✅  Request → Response cycle",
    "✅  Debug mode usage",
    "✅  Define routes with @app.route()",
    "✅  GET vs POST methods",
    "✅  Dynamic routes & url_for()",
]
add_rich_text(slide, Inches(9.0), Inches(5.0), Inches(3.8), Inches(2.0),
    [(item, TEXT, False) for item in checklist],
    font_size=11, line_spacing=1.5)

add_slide_number(slide, 6)


# ── Save ──
output_path = r"C:\Users\prems\.gemini\antigravity\scratch\flask-learning\Flask_Fundamentals.pptx"
prs.save(output_path)
print(f"✅ Presentation saved to: {output_path}")
