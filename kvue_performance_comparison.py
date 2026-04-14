"""
kvue_performance_comparison.py
------------------------------
KVUE vs SPY vs XLP rebased to 100 on IPO date (2023-05-04)
Window: May 2023 – Nov 2025
XLP = Consumer Staples Select Sector SPDR (holds PG, KMB, CL, CHD, etc.)
"""

import warnings
warnings.filterwarnings("ignore")

import os
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns

# ── Config ─────────────────────────────────────────────────────────────────────
TICKERS   = ["KVUE", "SPY", "XLP"]
BASE_DATE = pd.Timestamp("2023-05-04")   # IPO date
WIN_START = "2023-05-04"
WIN_END   = "2025-11-30"

CACHE = "performance_comparison_cache.csv"

# ── Download ───────────────────────────────────────────────────────────────────
if os.path.exists(CACHE):
    print(f"Loading cached prices from {CACHE} …")
    raw = pd.read_csv(CACHE, parse_dates=["Date"], index_col="Date")
    missing = [t for t in TICKERS if t not in raw.columns]
    if missing:
        print(f"  Cache missing {missing} — re-downloading …")
        os.remove(CACHE)
        raw = None
else:
    raw = None

if raw is None:
    print("Downloading prices …")
    raw = yf.download(TICKERS, start="2023-04-25", end="2025-12-02", auto_adjust=True)["Close"]
    raw.index = pd.to_datetime(raw.index)
    raw.to_csv(CACHE)
    print(f"  Saved to {CACHE}")

# ── Rebase to 100 on IPO date ──────────────────────────────────────────────────
indexed_all = pd.DataFrame(index=raw.index)
for t in TICKERS:
    first_valid = raw[t].loc[raw.index >= BASE_DATE].dropna()
    if len(first_valid):
        indexed_all[t] = raw[t] / first_valid.iloc[0] * 100
    else:
        indexed_all[t] = np.nan

indexed = indexed_all.loc[WIN_START:WIN_END].copy()
print(f"  {len(indexed)} trading days  ({indexed.index[0].date()} – {indexed.index[-1].date()})")

# ── Events ─────────────────────────────────────────────────────────────────────
ALL_EVENTS = {
    # "2023-08-18": "Exchange offer\ncloses",
    # "2023-08-25": "Added to\nS&P 500",
    # "2025-03-05": "Starboard\nboard seats",
    # "2025-07-14": "CEO fired",
    # "2025-09-05": "RFK autism\nreport",
    # "2025-09-22": "Trump/FDA\nannouncement",
    # "2025-10-03": "Moody's\noutlook cut",
    # "2025-11-02": "KMB deal\nannounced",
}
win_s = pd.Timestamp(WIN_START)
win_e = pd.Timestamp(WIN_END)
events = {
    pd.Timestamp(d): lbl
    for d, lbl in ALL_EVENTS.items()
    if win_s <= pd.Timestamp(d) <= win_e
}

# ── Theme ──────────────────────────────────────────────────────────────────────
BG          = "#fafafa"
C = {
    "KVUE": "#374768",   # dark navy — subject, thick
    "SPY":  "#1b1b1b",   # near-black — broad market
    "XLP":  "#c8963a",   # amber — consumer staples ETF
}
EVENT_COLOR = "#43567f"

sns.set_theme(style="white", font_scale=1.05)
plt.rcParams["figure.facecolor"] = BG
plt.rcParams["axes.facecolor"]   = BG

# ── Chart ──────────────────────────────────────────────────────────────────────
LABELS = {"KVUE": "KVUE", "SPY": "SPY", "XLP": "XLP (Consumer Staples ETF)"}

fig, ax = plt.subplots(figsize=(13, 5))

for t in TICKERS:
    is_kvue = t == "KVUE"
    ax.plot(indexed.index, indexed[t], color=C[t],
            linewidth=2.5 if is_kvue else 1.6,
            alpha=1.0 if is_kvue else 0.75,
            zorder=3 if is_kvue else 2,
            label=LABELS[t])
    valid = indexed[t].dropna()
    ax.annotate(LABELS[t],
                xy=(valid.index[-1], valid.iloc[-1]),
                xytext=(5, 0), textcoords="offset points",
                color=C[t], fontsize=9, fontweight="bold",
                va="center", annotation_clip=False)

ax.axhline(100, color="#9bacca", linewidth=0.8, linestyle=":", alpha=0.8)

# Event lines
label_fracs = [0.95, 0.82, 0.68, 0.54, 0.40, 0.88, 0.74, 0.60]
for i, (d, lbl) in enumerate(events.items()):
    ax.axvline(d, color=EVENT_COLOR, linewidth=0.9, linestyle="--", alpha=0.55, zorder=1)
    ax.text(d, label_fracs[i % len(label_fracs)], lbl,
            fontsize=7, color=EVENT_COLOR, ha="center", va="top",
            transform=ax.get_xaxis_transform(),
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.8))

ax.set_title(
    "KVUE vs S&P 500 (SPY) vs Consumer Staples ETF (XLP) — Rebased to 100 on IPO Date (May 2023)",
    fontsize=12, fontweight="bold",
)
ax.set_ylabel("Indexed Price (Base = 100 on May 4, 2023)")
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}"))
ax.set_xlim(indexed.index[0], indexed.index[-1] + pd.Timedelta(days=50))

ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[5, 8, 11, 2]))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right")

sns.despine(ax=ax)
fig.tight_layout()
os.makedirs("output", exist_ok=True)
fig.savefig("output/kvue_performance_comparison.png", dpi=150, bbox_inches="tight")
print("Saved output/kvue_performance_comparison.png")

# ── Zoom chart: Aug–Nov 2025, rebased to 100 on Aug 1 2025 ───────────────────
ZOOM_START = pd.Timestamp("2025-08-01")
ZOOM_END   = pd.Timestamp("2025-11-30")

zoom_all = pd.DataFrame(index=raw.index)
for t in TICKERS:
    first_valid = raw[t].loc[raw.index >= ZOOM_START].dropna()
    if len(first_valid):
        zoom_all[t] = raw[t] / first_valid.iloc[0] * 100
    else:
        zoom_all[t] = np.nan
zoom = zoom_all.loc[ZOOM_START:ZOOM_END].copy()

ZOOM_EVENTS = {
    pd.Timestamp("2025-09-05"):  "RFK autism\nreport",
    pd.Timestamp("2025-09-22"):  "Trump/FDA\nannouncement",
    pd.Timestamp("2025-10-03"):  "Moody's\noutlook cut",
    pd.Timestamp("2025-11-02"):  "KMB deal\nannounced",
}

fig2, ax2 = plt.subplots(figsize=(16, 3.5))

for t in TICKERS:
    is_kvue = t == "KVUE"
    ax2.plot(zoom.index, zoom[t], color=C[t],
             linewidth=2.5 if is_kvue else 1.6,
             alpha=1.0 if is_kvue else 0.75,
             zorder=3 if is_kvue else 2)
    valid = zoom[t].dropna()
    ax2.annotate(LABELS[t],
                 xy=(valid.index[-1], valid.iloc[-1]),
                 xytext=(5, 0), textcoords="offset points",
                 color=C[t], fontsize=9, fontweight="bold",
                 va="center", annotation_clip=False)

ax2.axhline(100, color="#9bacca", linewidth=0.8, linestyle=":", alpha=0.8)

label_fracs = [0.92, 0.75, 0.58, 0.88]
for i, (d, lbl) in enumerate(ZOOM_EVENTS.items()):
    ax2.axvline(d, color=EVENT_COLOR, linewidth=0.9, linestyle="--", alpha=0.55, zorder=1)
    ax2.text(d, label_fracs[i % len(label_fracs)], lbl,
             fontsize=7, color=EVENT_COLOR, ha="center", va="top",
             transform=ax2.get_xaxis_transform(),
             bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.8))

ax2.set_title(
    "KVUE vs SPY vs XLP — Rebased to 100 on Aug 1, 2025  |  Aug – Nov 2025",
    fontsize=12, fontweight="bold",
)
ax2.set_ylabel("Indexed Price\n(Base = 100)", fontsize=9)
ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}"))
ax2.set_xlim(zoom.index[0], zoom.index[-1] + pd.Timedelta(days=40))

ax2.xaxis.set_major_locator(mdates.MonthLocator())
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
plt.setp(ax2.xaxis.get_majorticklabels(), rotation=30, ha="right")

sns.despine(ax=ax2)
fig2.tight_layout()
fig2.savefig("output/kvue_zoom_aug_nov_2025.png", dpi=150, bbox_inches="tight")
print("Saved output/kvue_zoom_aug_nov_2025.png")
plt.show()
