"""
kvue_q3_2025_slide.py

Render operating performance charts for Kenvue showing:
    - Organic sales growth by quarter
    - Adjusted EPS by quarter
    - Q3 2025 peer organic sales growth comparison

Outputs:
    - output/kvue_q3_2025_operating_performance.png
    - output/kvue_q3_2025_peer_sales.png
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns


DATA = {
    "quarters": ["Q1 '24", "Q2 '24", "Q3 '24", "Q4 '24", "Q1 '25", "Q2 '25", "Q3 '25"],
    "organic_sales_growth": [0.019, 0.015, 0.009, 0.017, -0.012, -0.042, -0.044],
    "adj_eps": [0.28, 0.32, 0.28, 0.26, 0.24, 0.29, 0.28],
}

PEER_DATA = {
    "companies": ["Kenvue", "Church\n& Dwight", "Kimberly-\nClark", "P&G", "Colgate-\nPalmolive"],
    "organic_sales_growth_q3_2025": [-0.044, 0.034, 0.032, 0.025, 0.024],
}

BG = "#fafafa"
COLORS = {
    "navy": "#374768",
    "steel": "#9bacca",
    "line": "#43567f",
    "positive": "#5a8f6a",
    "negative": "#b85450",
    "ink": "#1b1b1b",
    "grid": "#d8deea",
}


def pct_fmt(value: float) -> str:
    return f"{value * 100:.1f}%"


def money_fmt(value: float) -> str:
    return f"${value:.2f}"


def apply_theme() -> None:
    sns.set_theme(style="white", font_scale=1.05)
    plt.rcParams["figure.facecolor"] = BG
    plt.rcParams["axes.facecolor"] = BG


def build_chart(output_path: str | Path = "output/kvue_q3_2025_operating_performance.png") -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    quarters = DATA["quarters"]
    sales_growth = np.array(DATA["organic_sales_growth"])
    adj_eps = np.array(DATA["adj_eps"])
    x = np.arange(len(quarters))

    apply_theme()

    fig, ax = plt.subplots(figsize=(13, 5.5))
    ax2 = ax.twinx()

    bar_colors = [
        COLORS["positive"] if value >= 0 else COLORS["negative"]
        for value in sales_growth
    ]
    ax.bar(x, sales_growth, width=0.62, color=bar_colors, alpha=0.9, zorder=2)
    ax.axhline(0, color=COLORS["steel"], linewidth=1.0, linestyle=":", alpha=0.9, zorder=1)

    ax2.plot(x, adj_eps, color=COLORS["navy"], linewidth=2.3, marker="o", markersize=6, zorder=4)
    ax2.fill_between(x, adj_eps, adj_eps.min() - 0.015, color=COLORS["navy"], alpha=0.12, zorder=3)

    for idx, value in enumerate(sales_growth):
        offset = 0.003 if value >= 0 else -0.004
        va = "bottom" if value >= 0 else "top"
        ax.text(idx, value + offset, pct_fmt(value), ha="center", va=va, fontsize=10, color=COLORS["ink"])

    for idx, value in enumerate(adj_eps):
        ax2.annotate(
            money_fmt(value),
            xy=(idx, value),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center",
            color=COLORS["navy"],
            fontsize=9.5,
            fontweight="bold",
        )

    ax.set_title(
        "Kenvue Quarterly Organic Sales Growth and Adjusted EPS",
        fontsize=13,
        fontweight="bold",
        color=COLORS["ink"],
    )
    ax.set_xticks(x)
    ax.set_xticklabels(quarters)
    ax.set_ylabel("Organic Sales Growth", color=COLORS["ink"])
    ax2.set_ylabel("Adjusted EPS", color=COLORS["navy"])

    ax.set_ylim(-0.06, 0.05)
    ax.set_yticks([-0.06, -0.03, 0.00, 0.03])
    ax.set_yticklabels(["-6%", "-3%", "0%", "3%"])

    ax2.set_ylim(adj_eps.min() - 0.03, adj_eps.max() + 0.03)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda value, _: f"${value:.2f}"))

    ax.grid(axis="y", color=COLORS["grid"], linewidth=0.8, alpha=0.9)
    ax.set_axisbelow(True)

    legend_handles = [
        plt.Rectangle((0, 0), 1, 1, color=COLORS["steel"], alpha=0.9, label="Organic Sales Growth"),
        plt.Line2D([0], [0], color=COLORS["navy"], linewidth=2.3, marker="o", label="Adjusted EPS"),
    ]
    ax.legend(handles=legend_handles, loc="upper right", frameon=True, fontsize=9)

    sns.despine(ax=ax, right=False)
    ax.spines["left"].set_color(COLORS["steel"])
    ax2.spines["right"].set_color(COLORS["steel"])

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


def build_peer_chart(output_path: str | Path = "output/kvue_q3_2025_peer_sales.png") -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    companies = PEER_DATA["companies"]
    sales_growth = np.array(PEER_DATA["organic_sales_growth_q3_2025"])
    x = np.arange(len(companies))

    apply_theme()

    fig, ax = plt.subplots(figsize=(11.5, 5.5))

    bar_colors = [
        COLORS["navy"] if idx == 0 else COLORS["steel"]
        for idx in range(len(companies))
    ]
    ax.bar(x, sales_growth, width=0.62, color=bar_colors, alpha=0.95, zorder=2)
    ax.axhline(0, color=COLORS["line"], linewidth=1.0, linestyle=":", alpha=0.9, zorder=1)

    for idx, value in enumerate(sales_growth):
        offset = 0.003 if value >= 0 else -0.004
        va = "bottom" if value >= 0 else "top"
        label_color = COLORS["navy"] if idx == 0 else COLORS["ink"]
        ax.text(idx, value + offset, pct_fmt(value), ha="center", va=va, fontsize=10, color=label_color)

    ax.set_title(
        "Q3 2025 Organic Sales Growth vs. Peers",
        fontsize=13,
        fontweight="bold",
        color=COLORS["ink"],
    )
    ax.set_xticks(x)
    ax.set_xticklabels(companies)
    ax.set_ylabel("Organic Sales Growth", color=COLORS["ink"])
    ax.set_ylim(-0.06, 0.05)
    ax.set_yticks([-0.06, -0.03, 0.00, 0.03])
    ax.set_yticklabels(["-6%", "-3%", "0%", "3%"])

    ax.grid(axis="y", color=COLORS["grid"], linewidth=0.8, alpha=0.9)
    ax.set_axisbelow(True)

    ax.annotate(
        "KVUE",
        xy=(x[0], sales_growth[0]),
        xytext=(-10, -28),
        textcoords="offset points",
        ha="center",
        color=COLORS["navy"],
        fontsize=9.5,
        fontweight="bold",
    )

    sns.despine(ax=ax)
    ax.spines["left"].set_color(COLORS["steel"])
    ax.spines["bottom"].set_color(COLORS["steel"])

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


if __name__ == "__main__":
    operating_out = build_chart()
    peer_out = build_peer_chart()
    print(f"Wrote {operating_out.resolve()}")
    print(f"Wrote {peer_out.resolve()}")
