"""
csv_to_visual.py
----------------
Generic CSV → presentation-ready chart or table using the slide theme.
Edit the CONFIG section below, then run:  python csv_to_visual.py
"""

import os
import sys
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import font_manager


# ══════════════════════════════════════════════════════════════════════════════
# CONFIG — edit everything here
# ══════════════════════════════════════════════════════════════════════════════

# Path to your CSV file
CSV = "my_data.csv"

# Output mode: "table" or "chart"
MODE = "table"

# Output file (saved to output/ folder)
OUTPUT = "output/result.png"

# ── Shared ─────────────────────────────────────────────────────────────────
TITLE    = "My Table"
SUBTITLE = ""          # italic line below title; leave "" to hide
FOOTNOTE = ""          # small italic footer; leave "" to hide (table only)

# ── Table settings ──────────────────────────────────────────────────────────
# Column in your CSV to use as the left-side row labels.
# Leave "" to use the first column automatically.
LABEL_COL = ""

# Column in your CSV that controls per-row styling.
# Leave "" if you don't have one (all rows will look like plain data rows).
# Valid values in that column:
#   "header"  → navy bg, white bold text     (featured / subject row)
#   "peer"    → white / light-blue striped   (normal data rows)
#   "summary" → steel-blue bg, bold text     (totals, medians)
#   "delta"   → light-blue bg; negative values are red, positive are green
TYPE_COL = ""

# Group the data columns under spanning headers in the top (navy) bar.
# Format: list of ("Group Label", number_of_columns) tuples.
# The column counts must add up to the total number of data columns.
# Set to [] to use a single group spanning all columns (labelled with TITLE).
# Example: [("EV / EBITDA", 3), ("Forward P / E", 3)]
GROUPS = []

# Override the column sub-headers shown in the dark navy-mid bar.
# Must be a list with one string per data column, or [] to use CSV column names.
# Use "\n" within a string to wrap text, e.g. "Revenue\n($M)"
# Example: ["May '23", "May '24", "Oct '25"]
COL_HEADERS = []

# ── Chart settings ──────────────────────────────────────────────────────────
# Column to use as the x-axis. Leave "" to use the first column.
# Date columns are detected automatically and formatted as months.
X_COL = ""

# Columns to plot. Leave [] to plot all numeric columns automatically.
Y_COLS = []

# Y-axis label
Y_LABEL = ""

# Name of one series to draw thick with a subtle fill under it (like a subject line).
# Leave "" to treat all series equally.
HIGHLIGHT = ""

# Set to True to rebase all series to 100 at their first value (indexed chart).
INDEXED = False

# Path to a CSV of events to draw as vertical dashed lines.
# The CSV must have columns named "date" and "label".
# Leave "" to skip.
EVENTS_CSV = ""

# Per-series color overrides: {"Column Name": "#hexcolor", ...}
# Unspecified series cycle through the theme palette automatically.
COLORS = {}


# ══════════════════════════════════════════════════════════════════════════════
# THEME  (no need to edit below here)
# ══════════════════════════════════════════════════════════════════════════════

NAVY        = "#374768"
NAVY_MID    = "#43567f"
STEEL       = "#9bacca"
LIGHT_BLUE  = "#c2cde5"
OFF_WHITE   = "#fafafa"
NEAR_BLACK  = "#1b1b1b"
ROW_ALT     = "#f0f4f9"
DISC_NEG    = "#c0392b"
DISC_POS    = "#27ae60"
EVENT_COLOR = "#43567f"

ROW_TYPE_ALIASES = {
    "header": "header", "kvue":   "header",
    "peer":   "peer",
    "summary":"summary", "median": "summary",
    "delta":  "delta",   "disc":   "delta",
}

DEFAULT_COLORS = [
    "#374768", "#c8963a", "#5a8f6a", "#b85450",
    "#9bacca", "#1b1b1b", "#7b6fa0", "#4a9e8f",
]

_available = {f.name for f in font_manager.fontManager.ttflist}
for _font in ["Poppins", "Didact Gothic", "Arial", "Helvetica"]:
    if _font in _available:
        plt.rcParams["font.family"] = _font
        break

plt.rcParams["figure.facecolor"] = OFF_WHITE
plt.rcParams["axes.facecolor"]   = OFF_WHITE


# ══════════════════════════════════════════════════════════════════════════════
# TABLE
# ══════════════════════════════════════════════════════════════════════════════

def draw_table(col_data, col_headers, group_headers,
               row_labels, row_types,
               title, subtitle, footnote,
               out_path, col_widths=None):
    n_rows = len(col_data)
    n_cols = len(col_headers) + 1

    if col_widths is None:
        col_widths = [3.0] + [1.2] * len(col_headers)

    total_w    = sum(col_widths)
    ROW_H      = 0.50
    N_HDR_ROWS = 2

    fig_w = total_w + 0.3
    fig_h = (n_rows + N_HDR_ROWS) * ROW_H + 1.0

    fig = plt.figure(figsize=(fig_w, fig_h))
    fig.patch.set_facecolor(OFF_WHITE)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    L, R = 0.02, 0.98
    TOP  = 0.82
    BOT  = 0.06
    row_h = (TOP - BOT) / (n_rows + N_HDR_ROWS)

    x_b = [L]
    for w in col_widths:
        x_b.append(x_b[-1] + w / total_w * (R - L))

    def cx(c):
        return (x_b[c] + x_b[c + 1]) / 2

    def rect(c, top, h, fc, ec="#dddddd", lw=0.4, zorder=1):
        ax.add_patch(plt.Rectangle(
            (x_b[c], top - h), x_b[c + 1] - x_b[c], h,
            transform=ax.transAxes, facecolor=fc,
            edgecolor=ec, linewidth=lw, clip_on=False, zorder=zorder))

    def txt(x, y, s, color=NEAR_BLACK, size=8, weight="normal",
            ha="center", va="center"):
        ax.text(x, y, s, transform=ax.transAxes,
                ha=ha, va=va, fontsize=size, color=color,
                fontweight=weight, clip_on=False, zorder=5, linespacing=1.25)

    # Title / subtitle
    ax.text(0.5, 0.95, title, transform=ax.transAxes,
            ha="center", fontsize=10.5, fontweight="bold", color=NAVY, zorder=5)
    if subtitle:
        ax.text(0.5, 0.90, subtitle, transform=ax.transAxes,
                ha="center", fontsize=7.5, color=STEEL, style="italic", zorder=5)

    # Group header row (navy)
    hr1_top = TOP
    hr1_bot = TOP - row_h
    for c in range(n_cols):
        rect(c, hr1_top, row_h, NAVY, NAVY, 0)
    col_cursor = 1
    for g_label, g_size in group_headers:
        x_left  = x_b[col_cursor]
        x_right = x_b[col_cursor + g_size]
        txt((x_left + x_right) / 2, (hr1_top + hr1_bot) / 2,
            g_label, color=OFF_WHITE, size=9, weight="bold")
        if col_cursor + g_size < n_cols:
            ax.plot([x_b[col_cursor + g_size]] * 2, [hr1_bot, hr1_top],
                    transform=ax.transAxes, color=STEEL, lw=0.8, zorder=6)
        col_cursor += g_size

    # Sub-header row (navy-mid)
    hr2_top = hr1_bot
    hr2_bot = hr2_top - row_h
    for c in range(n_cols):
        rect(c, hr2_top, row_h, NAVY_MID, NAVY_MID, 0)
    for ci, h in enumerate(col_headers):
        txt(cx(ci + 1), (hr2_top + hr2_bot) / 2,
            h, color=OFF_WHITE, size=7.5, weight="bold")

    # Group separator x positions
    col_cursor = 1
    sep_x = []
    for _, g_size in group_headers:
        sep_x.append(x_b[col_cursor])
        col_cursor += g_size

    # Data rows
    peer_idx = 0
    for ri, (label, rtype, vals) in enumerate(zip(row_labels, row_types, col_data)):
        rt = hr2_bot - ri * row_h
        rb = rt - row_h

        if rtype == "peer":
            bg = OFF_WHITE if peer_idx % 2 == 0 else ROW_ALT
            peer_idx += 1
        elif rtype == "header":
            bg = NAVY
        elif rtype == "summary":
            bg = STEEL
        elif rtype == "delta":
            bg = LIGHT_BLUE
        else:
            bg = OFF_WHITE

        tc = OFF_WHITE if rtype == "header" else NEAR_BLACK
        wt = "bold" if rtype in ("header", "summary", "delta") else "normal"

        for c in range(n_cols):
            rect(c, rt, row_h, bg, ec="#dddddd", lw=0.4)

        for sx in sep_x:
            ax.plot([sx, sx], [rb, rt], transform=ax.transAxes,
                    color="#888888", lw=0.8, zorder=6)

        ax.text(x_b[0] + 0.007, (rt + rb) / 2, label,
                transform=ax.transAxes, ha="left", va="center",
                fontsize=8, color=tc, fontweight=wt, clip_on=False, zorder=5)

        for ci, val in enumerate(vals):
            cell_color = tc
            if rtype == "delta" and isinstance(val, str) and val not in ("—", "", "n/a"):
                cell_color = DISC_NEG if val.lstrip().startswith("-") else DISC_POS
            txt(cx(ci + 1), (rt + rb) / 2, str(val), color=cell_color, size=8.5, weight=wt)

    # Outer border
    table_bot = hr2_bot - n_rows * row_h
    ax.add_patch(plt.Rectangle(
        (L, table_bot), R - L, TOP - table_bot,
        transform=ax.transAxes, facecolor="none",
        edgecolor=NAVY_MID, linewidth=1.2, clip_on=False, zorder=7))

    # Footer
    if footnote:
        ax.text(0.5, 0.025, footnote, transform=ax.transAxes,
                ha="center", va="bottom", fontsize=6.5, color=STEEL,
                style="italic", zorder=5)

    os.makedirs(os.path.dirname(out_path) or "output", exist_ok=True)
    fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor=OFF_WHITE)
    print(f"Saved {out_path}")
    plt.close(fig)


def run_table(df):
    label_col = LABEL_COL or df.columns[0]
    type_col  = TYPE_COL  or None

    skip = {label_col}
    if type_col:
        skip.add(type_col)
    data_cols = [c for c in df.columns if c not in skip]

    if not data_cols:
        sys.exit("No data columns found. Check LABEL_COL / TYPE_COL settings.")

    # Groups
    if GROUPS:
        group_headers = GROUPS
        total = sum(n for _, n in group_headers)
        if total != len(data_cols):
            sys.exit(f"GROUPS column count ({total}) != data columns ({len(data_cols)}): {data_cols}")
    else:
        group_headers = [(TITLE or "Data", len(data_cols))]

    # Column sub-headers
    if COL_HEADERS:
        if len(COL_HEADERS) != len(data_cols):
            sys.exit(f"COL_HEADERS length ({len(COL_HEADERS)}) != data columns ({len(data_cols)})")
        col_headers = COL_HEADERS
    else:
        col_headers = list(data_cols)

    # Build rows
    row_labels, row_types, col_data = [], [], []
    for _, row in df.iterrows():
        row_labels.append(str(row[label_col]))
        raw = str(row[type_col]).strip().lower() if type_col else "peer"
        row_types.append(ROW_TYPE_ALIASES.get(raw, "peer"))
        col_data.append(["—" if pd.isna(row[c]) else str(row[c]) for c in data_cols])

    # Auto column widths
    max_label = max(len(l) for l in row_labels)
    max_cell  = max(
        max((len(h.replace("\n", "")) for h in col_headers), default=4),
        max((len(v) for row in col_data for v in row), default=4),
    )
    label_w = max(2.5, min(max_label * 0.13, 5.0))
    data_w  = max(1.0, min(max_cell  * 0.12, 2.5))

    draw_table(
        col_data      = col_data,
        col_headers   = col_headers,
        group_headers = group_headers,
        row_labels    = row_labels,
        row_types     = row_types,
        title         = TITLE,
        subtitle      = SUBTITLE,
        footnote      = FOOTNOTE,
        out_path      = OUTPUT,
        col_widths    = [label_w] + [data_w] * len(data_cols),
    )


# ══════════════════════════════════════════════════════════════════════════════
# CHART
# ══════════════════════════════════════════════════════════════════════════════

def run_chart(df):
    try:
        import seaborn as sns
        sns.set_theme(style="white", font_scale=1.05)
    except ImportError:
        pass
    plt.rcParams["figure.facecolor"] = OFF_WHITE
    plt.rcParams["axes.facecolor"]   = OFF_WHITE

    x_col = X_COL or df.columns[0]
    x_is_date = False
    try:
        x = pd.to_datetime(df[x_col])
        x_is_date = True
    except Exception:
        x = df[x_col]

    y_cols = Y_COLS or [c for c in df.columns
                        if c != x_col and pd.api.types.is_numeric_dtype(df[c])]
    if not y_cols:
        sys.exit("No numeric columns found to plot. Set Y_COLS.")

    color_map = {**{c: DEFAULT_COLORS[i % len(DEFAULT_COLORS)] for i, c in enumerate(y_cols)},
                 **COLORS}

    plot_df = df[y_cols].copy()
    if INDEXED:
        for col in y_cols:
            first = plot_df[col].dropna()
            if len(first):
                plot_df[col] = plot_df[col] / first.iloc[0] * 100

    events = {}
    if EVENTS_CSV and os.path.exists(EVENTS_CSV):
        ev_df = pd.read_csv(EVENTS_CSV)
        for _, row in ev_df.iterrows():
            events[pd.Timestamp(str(row["date"]))] = str(row["label"])

    fig, ax = plt.subplots(figsize=(13, 5))
    label_fracs = [0.95, 0.82, 0.70, 0.58, 0.46, 0.85, 0.72]

    for col in y_cols:
        is_hi = HIGHLIGHT and col == HIGHLIGHT
        ax.plot(x, plot_df[col], color=color_map[col],
                linewidth=2.5 if is_hi else 1.5,
                alpha=1.0 if is_hi else 0.75,
                zorder=3 if is_hi else 2, label=col)
        if is_hi:
            ax.fill_between(x, plot_df[col], plot_df[col].min() * 0.98,
                            color=color_map[col], alpha=0.12, zorder=2)
        if x_is_date:
            valid = plot_df[col].dropna()
            if len(valid):
                ax.annotate(col,
                            xy=(x.iloc[valid.index[-1]], valid.iloc[-1]),
                            xytext=(5, 0), textcoords="offset points",
                            color=color_map[col], fontsize=9, fontweight="bold",
                            va="center", annotation_clip=False)

    for i, (d, lbl) in enumerate(events.items()):
        ax.axvline(d, color=EVENT_COLOR, linewidth=0.9, linestyle="--", alpha=0.65, zorder=1)
        ax.text(d, label_fracs[i % len(label_fracs)], lbl,
                fontsize=7.5, color=EVENT_COLOR, ha="center", va="top",
                transform=ax.get_xaxis_transform(),
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.8))

    if INDEXED:
        ax.axhline(100, color=STEEL, linewidth=0.8, linestyle=":", alpha=0.8)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}"))

    ax.set_title(TITLE or "Chart", fontsize=13, fontweight="bold", color=NEAR_BLACK)
    if SUBTITLE:
        ax.text(0.5, 1.01, SUBTITLE, transform=ax.transAxes,
                ha="center", fontsize=8.5, color=STEEL, style="italic")

    ax.set_ylabel(Y_LABEL or ("Indexed Value (Base = 100)" if INDEXED else "Value"))

    if x_is_date:
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right")

    if len(y_cols) > 1 and not x_is_date:
        ax.legend(loc="best", frameon=True, fontsize=9)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout()
    os.makedirs(os.path.dirname(OUTPUT) or "output", exist_ok=True)
    fig.savefig(OUTPUT, dpi=150, bbox_inches="tight", facecolor=OFF_WHITE)
    print(f"Saved {OUTPUT}")
    plt.close(fig)


# ══════════════════════════════════════════════════════════════════════════════
# RUN
# ══════════════════════════════════════════════════════════════════════════════

if not os.path.exists(CSV):
    sys.exit(f"CSV not found: {CSV}")

df = pd.read_csv(CSV)
if df.empty:
    sys.exit("CSV is empty.")

if MODE == "table":
    run_table(df)
elif MODE == "chart":
    run_chart(df)
else:
    sys.exit(f"Unknown MODE: '{MODE}'. Use 'table' or 'chart'.")
