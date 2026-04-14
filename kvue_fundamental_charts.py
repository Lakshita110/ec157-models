"""
kvue_fundamental_charts.py
--------------------------
Four KVUE fundamental line charts (May 2024 – Nov 2025):
  1. P/E Multiple
  2. EV/EBITDA Multiple
  3. Revenue TTM ($B)
  4. EBITDA Margin (%)

Source: Sheet1 of PitchBook_Formula_Comps_Model_v2_summary_fixed.xlsx
"""

import os
import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker

# ── Theme (matches csv_to_visual.py) ──────────────────────────────────────────
NAVY       = "#374768"
NAVY_MID   = "#43567f"
STEEL      = "#9bacca"
OFF_WHITE  = "#fafafa"
NEAR_BLACK = "#1b1b1b"

plt.rcParams["figure.facecolor"] = OFF_WHITE
plt.rcParams["axes.facecolor"]   = OFF_WHITE

# ── Load & parse ──────────────────────────────────────────────────────────────
XL_PATH = "PitchBook_Formula_Comps_Model_v2_summary_fixed.xlsx"
raw = pd.read_excel(XL_PATH, sheet_name="Sheet1", header=None)

# Row 3 is the header, data starts row 4; use positional columns to avoid
# duplicate "Date" issue (cols 0-11 map to the fields below)
COL = {
    "date":         0,
    "revenue":      1,
    "net_debt":     2,
    "ebitda_ttm":   3,
    "eps":          5,
    "pe":           9,
    "ev_ebitda":    11,
}

data = raw.iloc[4:, list(COL.values())].copy()
data.columns = list(COL.keys())
data["date"] = pd.to_datetime(data["date"], errors="coerce")
data = data.dropna(subset=["date"]).set_index("date").sort_index()
for col in data.columns:
    data[col] = pd.to_numeric(data[col], errors="coerce")
df = data

# Filter to window
df = df.loc["2023-05-01":"2025-11-30"]

# Derived series
df["Revenue_B"]       = df["revenue"] / 1e9
df["EBITDA_Margin"]   = df["ebitda_ttm"] / df["revenue"] * 100
df["Net_Debt_B"]      = df["net_debt"] / 1e9
df["Net_Debt_EBITDA"] = df["net_debt"] / df["ebitda_ttm"]

# ── Helper ────────────────────────────────────────────────────────────────────
def make_chart(dates, values, title, ylabel, y_fmt, out_name, color=NAVY, figsize=(11, 4.5)):
    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(dates, values, color=color, linewidth=2, zorder=3)
    ax.fill_between(dates, values, values.min() * 0.97,
                    color=color, alpha=0.10, zorder=2)

    ax.set_title(title, fontsize=13, fontweight="bold", color=NEAR_BLACK, pad=10)
    ax.set_ylabel(ylabel, fontsize=10, color=NEAR_BLACK)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(y_fmt))
    ax.set_xlim(dates.min(), dates.max())

    # Force x-axis ticks every 3 months anchored to May 2023 so it always appears
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[5, 8, 11, 2]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(colors=NEAR_BLACK)

    fig.tight_layout()
    os.makedirs("output", exist_ok=True)
    path = f"output/{out_name}"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=OFF_WHITE)
    print(f"Saved {path}")
    plt.close(fig)


# ── Chart 1 – P/E ─────────────────────────────────────────────────────────────
make_chart(
    dates   = df.index,
    values  = df["pe"],
    title   = "Kenvue (KVUE) — Trailing P/E Multiple  |  May 2023 – Nov 2025",
    ylabel  = "P/E (x)",
    y_fmt   = lambda v, _: f"{v:.1f}x",
    out_name= "kvue_pe.png",
    color   = NAVY,
)

# ── Chart 2 – EV/EBITDA ───────────────────────────────────────────────────────
make_chart(
    dates   = df.index,
    values  = df["ev_ebitda"],
    title   = "Kenvue (KVUE) — EV/EBITDA Multiple  |  May 2023 – Nov 2025",
    ylabel  = "EV/EBITDA (x)",
    y_fmt   = lambda v, _: f"{v:.1f}x",
    out_name= "kvue_ev_ebitda.png",
    color   = NAVY_MID,
    figsize = (16, 3.5),
)

# ── Chart 3 – Revenue ─────────────────────────────────────────────────────────
make_chart(
    dates   = df.index,
    values  = df["Revenue_B"],
    title   = "Kenvue (KVUE) — Revenue TTM  |  May 2023 – Nov 2025",
    ylabel  = "Revenue ($B)",
    y_fmt   = lambda v, _: f"${v:.1f}B",
    out_name= "kvue_revenue.png",
    color   = STEEL,
)

# ── Chart 4 – EBITDA Margin ───────────────────────────────────────────────────
make_chart(
    dates   = df.index,
    values  = df["EBITDA_Margin"],
    title   = "Kenvue (KVUE) — EBITDA Margin TTM  |  May 2023 – Nov 2025",
    ylabel  = "EBITDA Margin (%)",
    y_fmt   = lambda v, _: f"{v:.1f}%",
    out_name= "kvue_ebitda_margin.png",
    color   = "#5a8f6a",
)

# ── Chart 5 – Revenue & EBITDA bars ───────────────────────────────────────────
fig, ax1 = plt.subplots(figsize=(12, 5))

dates = df.index
ax1.bar(dates, df["Revenue_B"],      color=NAVY,  alpha=0.75, width=20, label="Revenue TTM")
ax1.bar(dates, df["ebitda_ttm"]/1e9, color=STEEL, alpha=0.85, width=20, label="EBITDA TTM")

ax1.set_ylabel("$B", fontsize=10, color=NEAR_BLACK)
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v:.0f}B"))
ax1.set_xlim(dates.min() - pd.Timedelta(days=20), dates.max() + pd.Timedelta(days=20))
ax1.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[5, 8, 11, 2]))
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
plt.setp(ax1.xaxis.get_majorticklabels(), rotation=30, ha="right")

ax1.set_title("Kenvue (KVUE) — Revenue & EBITDA TTM  |  May 2023 – Nov 2025",
              fontsize=13, fontweight="bold", color=NEAR_BLACK, pad=10)
ax1.legend(loc="upper right", frameon=True, fontsize=9)
ax1.spines["top"].set_visible(False)
ax1.spines["right"].set_visible(False)
fig.tight_layout()
fig.savefig("output/kvue_revenue_ebitda_margin.png", dpi=150, bbox_inches="tight", facecolor=OFF_WHITE)
print("Saved output/kvue_revenue_ebitda_margin.png")
plt.close(fig)

# ── Chart 6 – Revenue bar chart ───────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 5))
ax.bar(df.index, df["Revenue_B"], color=NAVY, alpha=0.85, width=20, zorder=2)

ax.set_title("Kenvue (KVUE) — Revenue TTM  |  May 2023 – Nov 2025",
             fontsize=13, fontweight="bold", color=NEAR_BLACK, pad=10)
ax.set_ylabel("Revenue ($B)", fontsize=10, color=NEAR_BLACK)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v:.1f}B"))
ax.set_xlim(df.index.min() - pd.Timedelta(days=20), df.index.max() + pd.Timedelta(days=20))
ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[5, 8, 11, 2]))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.set_ylim(df["Revenue_B"].min() * 0.97, df["Revenue_B"].max() * 1.03)
fig.tight_layout()
fig.savefig("output/kvue_revenue_bar.png", dpi=150, bbox_inches="tight", facecolor=OFF_WHITE)
print("Saved output/kvue_revenue_bar.png")
plt.close(fig)
