"""
kvue_price_chart.py
-------------------
Chart 1: KVUE absolute price (USD) with key events
Chart 2: KVUE + consumer-health peers + SPY rebased to 100 on 2024-05-01 with same events
Window: 2024-05-01 – 2025-11-30
"""

import warnings
warnings.filterwarnings("ignore")

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import seaborn as sns

# ── Data ───────────────────────────────────────────────────────────────────────
TICKERS    = ["KVUE", "PG", "KMB", "CL", "CHD", "SPY"]
WIN_START  = "2024-05-04"
WIN_END    = "2025-12-31"

CACHE = "peer_price_cache.csv"
import os
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
prices = raw.loc[WIN_START:WIN_END].copy()
print(f"  {len(prices)} trading days  ({prices.index[0].date()} – {prices.index[-1].date()})")

# ── Events ─────────────────────────────────────────────────────────────────────
ALL_EVENTS = {
    "2023-08-18": "Exchange offer closes",
    "2023-08-25": "Added to S&P 500",
    "2025-03-05": "Starboard\nboard seats",
    "2025-07-14": "CEO fired",
    "2025-09-05": "RFK autism\nreport",
    "2025-09-22": "Trump/FDA\nannouncement",
    "2025-10-03": "Moody's\noutlook cut",
    "2025-11-02": "KMB deal\nannounced",
}

# Only keep events that fall within the window
win_s = pd.Timestamp(WIN_START)
win_e = pd.Timestamp(WIN_END)
events = {
    pd.Timestamp(d): lbl
    for d, lbl in ALL_EVENTS.items()
    if win_s <= pd.Timestamp(d) <= win_e
}

# Slide theme palette: #1b1b1b #fafafa #374768 #43567f #9bacca #c2cde5
BG          = "#fafafa"
C = {
    "KVUE": "#374768",   # dark navy (theme)  — subject, thick
    "KMB":  "#c8963a",   # amber/gold         — eventual acquirer
    "PG":   "#5a8f6a",   # sage green         — large-cap staples
    "CL":   "#b85450",   # muted coral-red    — healthcare reference
    "CHD":  "#9bacca",   # steel blue (theme) — sector benchmark
    "SPY":  "#1b1b1b",   # near-black (theme) — broad market
}
EVENT_COLOR = "#43567f"

sns.set_theme(style="white", font_scale=1.05)
plt.rcParams["figure.facecolor"] = BG
plt.rcParams["axes.facecolor"]   = BG


# ══════════════════════════════════════════════════════════════════════════════
# Chart 1 – KVUE absolute price
# ══════════════════════════════════════════════════════════════════════════════
fig1, ax1 = plt.subplots(figsize=(13, 5))

ax1.plot(prices.index, prices["KVUE"], color=C["KVUE"], linewidth=2, zorder=3)
ax1.fill_between(prices.index, prices["KVUE"], prices["KVUE"].min() * 0.98,
                 color=C["KVUE"], alpha=0.12, zorder=2)

# Event lines – stagger label heights to avoid overlap
ymin, ymax = prices["KVUE"].min(), prices["KVUE"].max()
yspan = ymax - ymin
label_heights = [0.95, 0.82, 0.70, 0.58, 0.46, 0.85, 0.72]  # cycle
for i, (d, lbl) in enumerate(events.items()):
    ax1.axvline(d, color=EVENT_COLOR, linewidth=0.9, linestyle="--", alpha=0.65, zorder=1)
    y_pos = ymin + yspan * label_heights[i % len(label_heights)]
    ax1.text(d, y_pos, lbl, fontsize=7.5, color=EVENT_COLOR,
             ha="center", va="top", rotation=0,
             bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.8))

ax1.set_title(
    "Kenvue (KVUE) — Share Price  |  May 2023 – Nov 2025",
    fontsize=13, fontweight="bold",
)
ax1.set_ylabel("Share Price (USD)")
ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:.2f}"))
ax1.set_xlim(prices.index[0], prices.index[-1])

ax1.xaxis.set_major_locator(mdates.MonthLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
plt.setp(ax1.xaxis.get_majorticklabels(), rotation=30, ha="right")
sns.despine(ax=ax1)
fig1.tight_layout()
import os; os.makedirs("output", exist_ok=True)
fig1.savefig("output/kvue_price.png", dpi=150, bbox_inches="tight")
print("Saved kvue_price.png")


# ══════════════════════════════════════════════════════════════════════════════
# Chart 2 – Indexed comparison (base = 100 on KVUE IPO date 2023-05-04)
# ══════════════════════════════════════════════════════════════════════════════
# Rebase each ticker from its own price on the IPO date (first valid day >= it)
BASE_DATE = pd.Timestamp("2023-05-04")
indexed   = pd.DataFrame(index=prices.index)
for t in TICKERS:
    first_valid = prices[t].loc[prices.index >= BASE_DATE].dropna()
    if len(first_valid):
        indexed[t] = prices[t] / first_valid.iloc[0] * 100
    else:
        indexed[t] = np.nan

fig2, ax2 = plt.subplots(figsize=(13, 5))

for t in TICKERS:
    is_kvue = t == "KVUE"
    ax2.plot(indexed.index, indexed[t], color=C[t],
             linewidth=2.5 if is_kvue else 1.5,
             label=t, zorder=3 if is_kvue else 2,
             alpha=1.0 if is_kvue else 0.7)
    # Inline label
    valid = indexed[t].dropna()
    ax2.annotate(t, xy=(valid.index[-1], valid.iloc[-1]),
                 xytext=(5, 0), textcoords="offset points",
                 color=C[t], fontsize=9.5, fontweight="bold",
                 va="center", annotation_clip=False)

ax2.axhline(100, color="#9bacca", linewidth=0.8, linestyle=":", alpha=0.8)

# Event lines – staggered label heights (in axes fraction)
label_fracs = [0.92, 0.78, 0.64, 0.50, 0.36, 0.84, 0.70]
for i, (d, lbl) in enumerate(events.items()):
    ax2.axvline(d, color=EVENT_COLOR, linewidth=0.9, linestyle="--", alpha=0.55, zorder=1)
    ax2.text(d, label_fracs[i % len(label_fracs)], lbl,
             fontsize=7, color=EVENT_COLOR, ha="center", va="top",
             transform=ax2.get_xaxis_transform(),
             bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.8))

ax2.set_title(
    "KVUE vs Consumer-Health Peers & S&P 500 — Rebased to 100 on 2023-05-04 (IPO)",
    fontsize=13, fontweight="bold",
)
ax2.set_ylabel("Indexed Price (Base = 100)")
ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}"))
ax2.set_xlim(prices.index[0], prices.index[-1] + pd.Timedelta(days=35))

ax2.xaxis.set_major_locator(mdates.MonthLocator())
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
plt.setp(ax2.xaxis.get_majorticklabels(), rotation=30, ha="right")
ax2.legend(loc="upper left", frameon=True, fontsize=9)
sns.despine(ax=ax2)
fig2.tight_layout()
fig2.savefig("output/kvue_comparison.png", dpi=150, bbox_inches="tight")
print("Saved kvue_comparison.png")

plt.show()
exit(0)