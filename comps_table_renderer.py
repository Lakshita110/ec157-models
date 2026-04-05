"""
simple_workbook_builder.py
--------------------------
Reads comps_model.xlsx and renders two
presentation-ready table images using the slide theme.

Table 1 — Trading Multiples
  EV/EBITDA (NTM) and Forward P/E for Kenvue + 4 US peers at 3 dates.
  Bottom rows show peer median and KVUE discount.

Table 2 — Financial Performance
  Revenue TTM and EBITDA TTM (in $M) for Kenvue + 4 US peers at 3 dates.

Outputs: output/table_multiples.png, output/table_financials.png
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import font_manager

# ── Theme ──────────────────────────────────────────────────────────────────────
NAVY        = "#374768"
NAVY_MID    = "#43567f"
STEEL       = "#9bacca"
LIGHT_BLUE  = "#c2cde5"
OFF_WHITE   = "#fafafa"
NEAR_BLACK  = "#1b1b1b"
ROW_ALT     = "#f0f4f9"
DISC_NEG    = "#c0392b"
DISC_POS    = "#27ae60"

_available = {f.name for f in font_manager.fontManager.ttflist}
for _font in ["Poppins", "Didact Gothic", "Arial", "Helvetica"]:
    if _font in _available:
        plt.rcParams["font.family"] = _font
        break

# ── Load workbook ──────────────────────────────────────────────────────────────
WORKBOOK = "comps_model.xlsx"
SHEETS   = {
    "IPO (May '23)":           "IPO_2023_05_04",
    "1-yr Post-IPO (May '24)": "Post1Y_2024_05_04",
    "Pre-Deal (Oct '25)":      "PreDeal_2025_10_31",
}
SNAP_LABELS = list(SHEETS.keys())

COMPANIES = ["Kenvue", "Procter & Gamble", "Kimberly-Clark",
             "Colgate-Palmolive", "Church & Dwight"]
PEERS     = COMPANIES[1:]

def load_sheet(sheet_name):
    df = pd.read_excel(WORKBOOK, sheet_name=sheet_name, header=None)
    # Row 3 = header, rows 4+ = data
    df.columns = df.iloc[3]
    df = df.iloc[4:].reset_index(drop=True)
    df = df[df["Company"].notna()].copy()
    df["Company"] = df["Company"].str.strip()
    return df

sheets = {label: load_sheet(sheet) for label, sheet in SHEETS.items()}

# Summary sheet for pre-computed multiples
summ = pd.read_excel(WORKBOOK, sheet_name="Summary", header=None)
summ.columns = summ.iloc[0]
summ = summ.iloc[1:9].reset_index(drop=True)
summ.columns = ["Company", "IPO EV/NTM", "1Y EV/NTM", "PreDeal EV/NTM",
                "IPO P/NTM", "1Y P/NTM", "PreDeal P/NTM"]
summ["Company"] = summ["Company"].str.strip()
summ = summ[summ["Company"].isin(COMPANIES)].set_index("Company")

# ── Helper: draw a table ───────────────────────────────────────────────────────
def draw_table(col_data, col_headers, group_headers,
               row_labels, row_types,   # type: 'kvue','peer','median','disc'
               title, subtitle, footnote,
               group_sizes,             # list of ints matching col_headers groups
               out_path,
               col_widths=None):
    """
    col_data    : list of lists [row][col]
    row_types   : list of strings per row
    group_sizes : widths of each metric group (for spanning header)
    """
    n_rows = len(col_data)
    n_cols = len(col_headers) + 1   # +1 for row label column

    # Default column widths
    if col_widths is None:
        col_widths = [3.0] + [1.1] * len(col_headers)

    total_w    = sum(col_widths)
    ROW_H      = 0.50
    N_HDR_ROWS = 2   # group header + date sub-header

    fig_w = total_w + 0.3
    fig_h = (n_rows + N_HDR_ROWS) * ROW_H + 1.0  # +1 for title/footer

    fig = plt.figure(figsize=(fig_w, fig_h))
    fig.patch.set_facecolor(OFF_WHITE)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

    L, R = 0.02, 0.98
    TOP  = 0.82
    BOT  = 0.06
    row_h = (TOP - BOT) / (n_rows + N_HDR_ROWS)

    # Cumulative x boundaries
    x_b = [L]
    for w in col_widths:
        x_b.append(x_b[-1] + w / total_w * (R - L))

    def cx(c):   return (x_b[c] + x_b[c + 1]) / 2
    def rect(c, top, h, fc, ec="#dddddd", lw=0.4, zorder=1):
        ax.add_patch(plt.Rectangle(
            (x_b[c], top - h), x_b[c+1] - x_b[c], h,
            transform=ax.transAxes, facecolor=fc,
            edgecolor=ec, linewidth=lw, clip_on=False, zorder=zorder))
    def txt(x, y, s, color=NEAR_BLACK, size=8, weight="normal",
            ha="center", va="center"):
        ax.text(x, y, s, transform=ax.transAxes,
                ha=ha, va=va, fontsize=size, color=color,
                fontweight=weight, clip_on=False, zorder=5,
                linespacing=1.25)

    # ── Title & subtitle ──────────────────────────────────────────────────────
    ax.text(0.5, 0.95, title, transform=ax.transAxes, ha="center",
            fontsize=10.5, fontweight="bold", color=NAVY, zorder=5)
    ax.text(0.5, 0.90, subtitle, transform=ax.transAxes, ha="center",
            fontsize=7.5, color=STEEL, style="italic", zorder=5)

    # ── Group header row ──────────────────────────────────────────────────────
    hr1_top = TOP
    hr1_bot = TOP - row_h
    for c in range(n_cols):
        rect(c, hr1_top, row_h, NAVY, NAVY, 0)

    # Draw group spans
    col_cursor = 1   # start after row-label column
    for g_label, g_size in group_headers:
        x_left  = x_b[col_cursor]
        x_right = x_b[col_cursor + g_size]
        mid_x   = (x_left + x_right) / 2
        txt(mid_x, (hr1_top + hr1_bot) / 2, g_label,
            color=OFF_WHITE, size=9, weight="bold")
        # Vertical divider between groups
        if col_cursor + g_size < n_cols:
            ax.plot([x_b[col_cursor + g_size]] * 2,
                    [hr1_bot, hr1_top],
                    transform=ax.transAxes,
                    color=STEEL, lw=0.8, zorder=6)
        col_cursor += g_size

    # ── Sub-header row ────────────────────────────────────────────────────────
    hr2_top = hr1_bot
    hr2_bot = hr2_top - row_h
    for c in range(n_cols):
        rect(c, hr2_top, row_h, NAVY_MID, NAVY_MID, 0)
    txt(cx(0), (hr2_top + hr2_bot) / 2, "", color=OFF_WHITE)
    for ci, h in enumerate(col_headers):
        txt(cx(ci + 1), (hr2_top + hr2_bot) / 2,
            h, color=OFF_WHITE, size=7.5, weight="bold")

    # ── Data rows ─────────────────────────────────────────────────────────────
    col_cursor = 1
    sep_x = []   # x positions for group separator lines
    for _, g_size in group_headers:
        sep_x.append(x_b[col_cursor])
        col_cursor += g_size

    for ri, (label, rtype, vals) in enumerate(
            zip(row_labels, row_types, col_data)):
        rt = hr2_bot - ri * row_h
        rb = rt - row_h

        bg  = {
            "kvue":   NAVY,
            "peer":   OFF_WHITE if ri % 2 == 0 else ROW_ALT,
            "median": STEEL,
            "disc":   LIGHT_BLUE,
        }[rtype]
        tc  = OFF_WHITE if rtype == "kvue" else NEAR_BLACK
        wt  = "bold" if rtype in ("kvue", "median", "disc") else "normal"

        for c in range(n_cols):
            rect(c, rt, row_h, bg, ec="#dddddd", lw=0.4)

        # Vertical group separators (drawn on top of cell borders)
        for sx in sep_x:
            ax.plot([sx, sx], [rb, rt], transform=ax.transAxes,
                    color="#888888", lw=0.8, zorder=6)

        # Row label
        ax.text(x_b[0] + 0.007, (rt + rb) / 2, label,
                transform=ax.transAxes,
                ha="left", va="center", fontsize=8,
                color=tc, fontweight=wt, clip_on=False, zorder=5)

        # Data cells
        for ci, val in enumerate(vals):
            cell_color = tc
            if rtype == "disc" and isinstance(val, str) and val != "—":
                cell_color = DISC_NEG if val.startswith("-") else DISC_POS
            txt(cx(ci + 1), (rt + rb) / 2, str(val),
                color=cell_color, size=8.5, weight=wt)

    # ── Outer border ─────────────────────────────────────────────────────────
    table_bot = hr2_bot - n_rows * row_h
    ax.add_patch(plt.Rectangle(
        (L, table_bot), R - L, TOP - table_bot,
        transform=ax.transAxes, facecolor="none",
        edgecolor=NAVY_MID, linewidth=1.2, clip_on=False, zorder=7))

    # ── Footer ────────────────────────────────────────────────────────────────
    ax.text(0.5, 0.025, footnote, transform=ax.transAxes,
            ha="center", va="bottom", fontsize=6.5, color=STEEL,
            style="italic", zorder=5)

    os.makedirs("output", exist_ok=True)
    fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor=OFF_WHITE)
    print(f"Saved {out_path}")
    plt.close(fig)


# ══════════════════════════════════════════════════════════════════════════════
# Table 1 — Trading Multiples
# ══════════════════════════════════════════════════════════════════════════════
ev_cols  = ["IPO EV/NTM", "1Y EV/NTM", "PreDeal EV/NTM"]
pe_cols  = ["IPO P/NTM",  "1Y P/NTM",  "PreDeal P/NTM"]

def fmt_mult(v):
    try:
        return f"{float(v):.1f}×"
    except:
        return "—"

def disc_fmt(kvue, med):
    try:
        pct = (float(kvue) / float(med) - 1) * 100
        return f"{pct:+.0f}%"
    except:
        return "—"

col_headers_m = ["IPO\nMay '23", "1-yr\nMay '24", "Pre-Deal\nOct '25",
                 "IPO\nMay '23", "1-yr\nMay '24", "Pre-Deal\nOct '25"]

row_labels_m, row_types_m, col_data_m = [], [], []

peer_ev_vals = {c: [] for c in ev_cols}
peer_pe_vals = {c: [] for c in pe_cols}

for co in COMPANIES:
    rtype = "kvue" if co == "Kenvue" else "peer"
    row   = summ.loc[co]
    ev_v  = [fmt_mult(row[c]) for c in ev_cols]
    pe_v  = [fmt_mult(row[c]) for c in pe_cols]
    col_data_m.append(ev_v + pe_v)
    row_labels_m.append(co)
    row_types_m.append(rtype)
    if co != "Kenvue":
        for c in ev_cols: peer_ev_vals[c].append(float(row[c]))
        for c in pe_cols: peer_pe_vals[c].append(float(row[c]))

# Peer median
med_ev = [f"{np.median(peer_ev_vals[c]):.1f}×" for c in ev_cols]
med_pe = [f"{np.median(peer_pe_vals[c]):.1f}×" for c in pe_cols]
col_data_m.append(med_ev + med_pe)
row_labels_m.append("Peer Median")
row_types_m.append("median")

# KVUE discount
kvue_row = summ.loc["Kenvue"]
med_ev_f = [np.median(peer_ev_vals[c]) for c in ev_cols]
med_pe_f = [np.median(peer_pe_vals[c]) for c in pe_cols]
disc_ev  = [disc_fmt(kvue_row[c], m) for c, m in zip(ev_cols, med_ev_f)]
disc_pe  = [disc_fmt(kvue_row[c], m) for c, m in zip(pe_cols, med_pe_f)]
col_data_m.append(disc_ev + disc_pe)
row_labels_m.append("KVUE vs. Peer Median")
row_types_m.append("disc")

draw_table(
    col_data     = col_data_m,
    col_headers  = col_headers_m,
    group_headers= [("EV / EBITDA (NTM)", 3), ("Forward P / E", 3)],
    row_labels   = row_labels_m,
    row_types    = row_types_m,
    title        = "Kenvue vs. US Consumer-Health Peers  —  Trading Multiples",
    subtitle     = "EV/EBITDA and Forward P/E at three snapshot dates  |  Source: PitchBook",
    footnote     = "NTM = next twelve months.  Peer Median excludes Kenvue.  "
                   "Discount = KVUE multiple / Peer Median − 1.",
    group_sizes  = [3, 3],
    out_path     = "output/table_multiples.png",
    col_widths   = [2.8] + [1.05] * 6,
)


# ══════════════════════════════════════════════════════════════════════════════
# Table 2 — Financial Performance
# ══════════════════════════════════════════════════════════════════════════════
def fmt_rev(v):
    """Format revenue in $M with commas."""
    try:
        return f"${float(v)/1e6:,.0f}M"
    except:
        return "—"

def fmt_ebitda(v):
    try:
        return f"${float(v)/1e6:,.0f}M"
    except:
        return "—"

def fmt_margin(ebitda, revenue):
    try:
        return f"{float(ebitda)/float(revenue)*100:.1f}%"
    except:
        return "—"

def fmt_eps(v):
    try:
        return f"${float(v):.2f}"
    except:
        return "—"

# Sub-headers: Rev | EBITDA | Margin per period
col_headers_f = []
for lbl in SNAP_LABELS:
    short = {"IPO (May '23)": "May '23",
             "1-yr Post-IPO (May '24)": "May '24",
             "Pre-Deal (Oct '25)": "Oct '25"}[lbl]
    col_headers_f += [f"Revenue\n{short}", f"EBITDA\n{short}", f"Margin\n{short}"]

row_labels_f, row_types_f, col_data_f = [], [], []

for co in COMPANIES:
    rtype = "kvue" if co == "Kenvue" else "peer"
    vals  = []
    for lbl in SNAP_LABELS:
        df = sheets[lbl]
        row = df[df["Company"] == co]
        if row.empty:
            vals += ["—", "—", "—"]
            continue
        row = row.iloc[0]
        rev    = row.get("Revenue TTM", np.nan)
        ebitda = row.get("EBITDA TTM",  np.nan)
        vals  += [fmt_rev(rev), fmt_ebitda(ebitda), fmt_margin(ebitda, rev)]
    col_data_f.append(vals)
    row_labels_f.append(co)
    row_types_f.append(rtype)

draw_table(
    col_data     = col_data_f,
    col_headers  = col_headers_f,
    group_headers= [("IPO  —  May 2023", 3),
                    ("1-yr Post-IPO  —  May 2024", 3),
                    ("Pre-Deal  —  Oct 2025", 3)],
    row_labels   = row_labels_f,
    row_types    = row_types_f,
    title        = "Kenvue vs. US Consumer-Health Peers  —  Financial Performance",
    subtitle     = "Revenue and EBITDA (TTM) across three snapshot dates  |  Source: PitchBook",
    footnote     = "Revenue and EBITDA shown in USD millions (TTM = trailing twelve months).  "
                   "Margin = EBITDA / Revenue.",
    group_sizes  = [3, 3, 3],
    out_path     = "output/table_financials.png",
    col_widths   = [2.8] + [1.15] * 9,
)
