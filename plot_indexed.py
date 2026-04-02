import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

df = pd.read_csv("stock_data.csv", parse_dates=["Date"], index_col="Date")

# Index to 100 at first observation
indexed = df.div(df.iloc[0]) * 100

fig, ax = plt.subplots(figsize=(12, 6))

colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
for col, color in zip(indexed.columns, colors):
    ax.plot(indexed.index, indexed[col], label=col, linewidth=1.5, color=color)

ax.axhline(100, color="black", linewidth=0.8, linestyle="--", alpha=0.5)
ax.set_title("Indexed Stock Prices (Base = 100 on 2023-05-04)", fontsize=14)
ax.set_xlabel("Date")
ax.set_ylabel("Index (Base = 100)")
ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f"))
ax.legend(loc="upper left", framealpha=0.9)
ax.grid(True, alpha=0.3)
fig.tight_layout()

plt.savefig("indexed_chart.png", dpi=150)
print("Saved indexed_chart.png")
plt.show()
