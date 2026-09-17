"""
theme.py
--------
Dark-violet / gradient color palette + a reusable Plotly template, so every
chart in app.py pulls from one place instead of scattering hex codes around.
Matches the dark dashboard reference: deep indigo background, gradient KPI
chips (coral / pink / blue / purple), dark panels behind each chart.
"""

import plotly.graph_objects as go

# --- base palette --------------------------------------------------------
BG_MAIN = "#2b2657"
BG_PANEL = "#332c63"
BG_PANEL_BORDER = "#443c7a"
GRID_LINE = "#443c7a"
TEXT_PRIMARY = "#f5f3fa"
TEXT_MUTED = "#b6b0d9"

# --- accent colors, taken from the reference dashboard --------------------
CORAL = "#f4795f"
CORAL_LIGHT = "#f7a97e"
PINK = "#e35fa8"
PINK_LIGHT = "#f091c6"
BLUE = "#4f9ce0"
BLUE_LIGHT = "#7cc3f0"
PURPLE = "#8b7ee8"
PURPLE_LIGHT = "#a58ff0"
GOLD = "#f0c869"

# order matches the 4 KPI cards in app.py
KPI_GRADIENTS = [
    f"linear-gradient(135deg, {CORAL} 0%, {CORAL_LIGHT} 100%)",
    f"linear-gradient(135deg, {PINK} 0%, {PINK_LIGHT} 100%)",
    f"linear-gradient(135deg, {BLUE} 0%, {BLUE_LIGHT} 100%)",
    f"linear-gradient(135deg, {PURPLE} 0%, {PURPLE_LIGHT} 100%)",
]

# continuous scales for charts that color by value
RETURN_RATE_SCALE = [PINK_LIGHT, PINK, CORAL, CORAL_LIGHT]
RATING_SCALE = [PURPLE_LIGHT, PURPLE, "#6f5fd0"]

# discrete palette for multi-category bars (segments, etc.)
DISCRETE_SEQUENCE = [BLUE, PURPLE, PINK, CORAL, BLUE_LIGHT]

PLOTLY_TEMPLATE = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor=BG_PANEL,
        plot_bgcolor=BG_PANEL,
        font=dict(color=TEXT_PRIMARY, family="Segoe UI, Helvetica, Arial, sans-serif"),
        title=dict(font=dict(color=TEXT_PRIMARY)),
        xaxis=dict(gridcolor=GRID_LINE, zerolinecolor=GRID_LINE, color=TEXT_MUTED),
        yaxis=dict(gridcolor=GRID_LINE, zerolinecolor=GRID_LINE, color=TEXT_MUTED),
        legend=dict(font=dict(color=TEXT_PRIMARY)),
        margin=dict(t=30, l=10, r=10, b=10),
    )
)

LIGHT_FIELD = "#4a4380"
LIGHT_FIELD_BORDER = "#6a60b0"

CSS = f"""
<style>
.stApp {{
    background-color: {BG_MAIN};
}}

/* tighten overall page padding so more content is visible without scrolling */
.block-container {{
    padding-top: 1.75rem !important;
    padding-bottom: 1.5rem !important;
}}

/* reduce vertical gap between stacked elements and between columns */
div[data-testid="stVerticalBlock"] {{
    gap: 0.6rem;
}}
div[data-testid="stHorizontalBlock"] {{
    gap: 0.75rem;
}}

/* headers: less breathing room above/below */
h1 {{ margin-bottom: 0.2rem !important; }}
h3 {{ margin-top: 0 !important; margin-bottom: 0.3rem !important; padding: 0 !important; }}

/* KPI cards */
.kpi-row {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 4px;
}}
.kpi-card {{
    border-radius: 14px;
    padding: 16px 20px;
    color: white;
    box-shadow: 0 4px 14px rgba(0,0,0,0.25);
}}
.kpi-label {{
    font-size: 13px;
    opacity: 0.85;
    margin-bottom: 6px;
}}
.kpi-value {{
    font-size: 26px;
    font-weight: 700;
}}

/* dark panel behind bordered containers (used to frame each chart / the query box) */
div[data-testid="stVerticalBlockBorderWrapper"] {{
    background-color: {BG_PANEL};
    border: 1px solid {BG_PANEL_BORDER};
    border-radius: 14px;
}}
div[data-testid="stVerticalBlockBorderWrapper"] > div {{
    background-color: transparent;
}}
div[data-testid="stVerticalBlockBorderWrapper"] .block-container {{
    padding: 0 !important;
}}
/* trim the default padding Streamlit adds inside a bordered container */
div[data-testid="stVerticalBlockBorderWrapper"] > div > div[data-testid="stVerticalBlock"] {{
    padding: 0.9rem 1.1rem;
    gap: 0.4rem;
}}

/* lighter, clearly differentiated input fields against the dark panel */
.stTextInput input,
.stSelectbox div[data-baseweb="select"] > div,
.stNumberInput input {{
    background-color: {LIGHT_FIELD} !important;
    border: 1px solid {LIGHT_FIELD_BORDER} !important;
    color: {TEXT_PRIMARY} !important;
    border-radius: 8px !important;
}}
.stSelectbox svg {{
    fill: {TEXT_PRIMARY} !important;
}}
div[data-baseweb="popover"] li {{
    background-color: {LIGHT_FIELD} !important;
}}

/* Ask button: filled pink-to-purple pill instead of default outline */
.stButton button {{
    background: linear-gradient(135deg, {PINK} 0%, {PURPLE} 100%);
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
}}
.stButton button:hover {{
    filter: brightness(1.08);
    color: white;
}}
</style>
"""


def kpi_card_html(label: str, value: str, gradient_index: int) -> str:
    gradient = KPI_GRADIENTS[gradient_index % len(KPI_GRADIENTS)]
    return (
        f'<div class="kpi-card" style="background: {gradient};">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f"</div>"
    )
