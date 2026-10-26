import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

os.makedirs("outputs/charts", exist_ok=True)
plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False})

df = pd.read_csv("outputs/clean_data.csv", parse_dates=["Order Date"])

# =====================================================
# 1. PRODUCT-LEVEL METRICS
# =====================================================
prod = (df.groupby(["Product Name", "Division"])
          .agg({"Sales": "sum", "Units": "sum", "Gross Profit": "sum", "Cost": "sum"})
          .reset_index())

prod["Gross Margin %"] = prod["Gross Profit"] / prod["Sales"] * 100
prod["Profit per Unit"] = prod["Gross Profit"] / prod["Units"]
prod["Cost % of Sales"] = prod["Cost"] / prod["Sales"] * 100
prod["Revenue Contribution %"] = prod["Sales"] / prod["Sales"].sum() * 100
prod["Profit Contribution %"] = prod["Gross Profit"] / prod["Gross Profit"].sum() * 100

# Margin volatility = how much monthly margin jumps around (standard deviation)
df["Month"] = df["Order Date"].dt.to_period("M")
monthly = (df.groupby(["Product Name", "Month"])
             .agg({"Sales": "sum", "Gross Profit": "sum"}).reset_index())
monthly["Margin"] = monthly["Gross Profit"] / monthly["Sales"] * 100
vol = monthly.groupby("Product Name")["Margin"].std().rename("Margin Volatility")
prod = prod.merge(vol, on="Product Name", how="left").fillna({"Margin Volatility": 0})

# =====================================================
# 2. PRODUCT CLASSIFICATION
# =====================================================
med_sales = prod["Sales"].median()
med_profit = prod["Gross Profit"].median()
overall_margin = prod["Gross Profit"].sum() / prod["Sales"].sum() * 100

def classify(r):
    if r["Gross Profit"] >= med_profit and r["Gross Margin %"] >= overall_margin:
        return "High profit / High margin"
    if r["Sales"] >= med_sales and r["Gross Margin %"] < overall_margin:
        return "High sales / Low margin"
    if r["Sales"] < med_sales and r["Gross Profit"] < med_profit:
        return "Low sales / Low profit"
    return "Average"

prod["Category"] = prod.apply(classify, axis=1)

# =====================================================
# 3. COST STRUCTURE FLAGS
# =====================================================
low_margin = prod["Gross Margin %"] < overall_margin
prod["Action Flag"] = np.select(
    [low_margin & (prod["Sales"] < med_sales) & (prod["Gross Profit"] < med_profit),
     low_margin & (prod["Sales"] >= med_sales),
     low_margin],
    ["Discontinuation review", "Cost renegotiation", "Repricing"],
    default="Healthy")

# =====================================================
# 4. DIVISION-LEVEL ANALYSIS
# =====================================================
div = (df.groupby("Division")
         .agg({"Sales": "sum", "Gross Profit": "sum", "Cost": "sum", "Units": "sum"})
         .reset_index())
div["Gross Margin %"] = div["Gross Profit"] / div["Sales"] * 100
div["Revenue Share %"] = div["Sales"] / div["Sales"].sum() * 100
div["Profit Share %"] = div["Gross Profit"] / div["Gross Profit"].sum() * 100
div["Profit - Revenue Share (pp)"] = div["Profit Share %"] - div["Revenue Share %"]
avg_prod_margin = prod.groupby("Division")["Gross Margin %"].mean().rename("Avg Product Margin %")
div = div.merge(avg_prod_margin, on="Division")

# =====================================================
# 5. PARETO ANALYSIS
# =====================================================
def pareto(table, col):
    t = table.sort_values(col, ascending=False).reset_index(drop=True)
    t["Cumulative %"] = t[col].cumsum() / t[col].sum() * 100
    n80 = int((t["Cumulative %"] < 80).sum() + 1)
    return t, n80

rev_p, n80_rev = pareto(prod, "Sales")
prof_p, n80_prof = pareto(prod, "Gross Profit")
n_prod = len(prod)

# =====================================================
# 6. SAVE TABLES
# =====================================================
prod.sort_values("Gross Profit", ascending=False).round(2).to_csv("outputs/product_metrics.csv", index=False)
div.round(2).to_csv("outputs/division_metrics.csv", index=False)

# =====================================================
# 7. CHARTS
# =====================================================
# 7a. Top products by profit
t = prod.sort_values("Gross Profit").tail(15)
plt.figure(figsize=(9, 6))
plt.barh(t["Product Name"], t["Gross Profit"], color="#2f6f8f")
plt.title("Gross Profit by Product"); plt.xlabel("Gross Profit")
plt.tight_layout(); plt.savefig("outputs/charts/01_profit_by_product.png"); plt.close()

# 7b. Margin leaderboard
t = prod.sort_values("Gross Margin %")
colors = ["#c0392b" if m < overall_margin else "#2f6f8f" for m in t["Gross Margin %"]]
plt.figure(figsize=(9, 6))
plt.barh(t["Product Name"], t["Gross Margin %"], color=colors)
plt.axvline(overall_margin, color="gray", ls="--", label=f"Overall margin {overall_margin:.1f}%")
plt.title("Gross Margin % by Product (red = below overall)"); plt.xlabel("Gross Margin %"); plt.legend()
plt.tight_layout(); plt.savefig("outputs/charts/02_margin_by_product.png"); plt.close()

# 7c. Division revenue vs profit
x = np.arange(len(div)); w = 0.38
plt.figure(figsize=(7, 5))
plt.bar(x - w/2, div["Sales"], w, label="Sales", color="#7f8c8d")
plt.bar(x + w/2, div["Gross Profit"], w, label="Gross Profit", color="#2f6f8f")
plt.xticks(x, div["Division"]); plt.title("Revenue vs Profit by Division"); plt.legend()
plt.tight_layout(); plt.savefig("outputs/charts/03_division_revenue_vs_profit.png"); plt.close()

# 7d. Margin distribution by division
df["Order Margin %"] = df["Gross Profit"] / df["Sales"] * 100
groups = [df.loc[df["Division"] == d, "Order Margin %"] for d in div["Division"]]
plt.figure(figsize=(7, 5))
plt.boxplot(groups, showfliers=False)
plt.xticks(range(1, len(div) + 1), div["Division"])
plt.title("Order Margin % Distribution by Division"); plt.ylabel("Margin %")
plt.tight_layout(); plt.savefig("outputs/charts/04_margin_distribution_division.png"); plt.close()

# 7e. Cost vs Sales scatter
plt.figure(figsize=(9, 6))
plt.scatter(prod["Sales"], prod["Cost"], s=prod["Units"] / prod["Units"].max() * 400 + 30, color="#2f6f8f", alpha=0.7)
for _, r in prod.iterrows():
    plt.annotate(r["Product Name"], (r["Sales"], r["Cost"]), fontsize=6, xytext=(3, 3), textcoords="offset points")
lim = max(prod["Sales"].max(), prod["Cost"].max())
plt.plot([0, lim], [0, lim], "r--", lw=1, label="Break-even (Cost = Sales)")
plt.xlabel("Total Sales"); plt.ylabel("Total Cost"); plt.title("Cost vs Sales by Product"); plt.legend()
plt.tight_layout(); plt.savefig("outputs/charts/05_cost_vs_sales.png"); plt.close()

# 7f. Pareto charts
for data, col, n80, name, fn in [(rev_p, "Sales", n80_rev, "Revenue", "06_pareto_revenue.png"),
                                  (prof_p, "Gross Profit", n80_prof, "Profit", "07_pareto_profit.png")]:
    fig, ax = plt.subplots(figsize=(10, 5))
    positions = range(len(data))
    ax.bar(positions, data[col], color="#2f6f8f")
    ax.set_xticks(list(positions))
    ax.set_xticklabels(data["Product Name"])
    plt.setp(ax.get_xticklabels(), rotation=75, ha="right", fontsize=7)
    ax2 = ax.twinx()
    ax2.plot(positions, data["Cumulative %"], color="#c0392b", marker="o", ms=3)
    ax2.axhline(80, color="gray", ls="--"); ax2.set_ylim(0, 105)
    ax2.spines["right"].set_visible(True)
    ax.set_title(f"Pareto: {name} ({n80} of {n_prod} products make 80%)")
    plt.tight_layout(); plt.savefig(f"outputs/charts/{fn}"); plt.close()

# =====================================================
# 8. PRINT SUMMARY (copy this and send it to me)
# =====================================================
pd.set_option("display.width", 200); pd.set_option("display.max_columns", 20)
print("\n===== OVERALL =====")
print(f"Total Sales: {prod['Sales'].sum():,.2f} | Total Profit: {prod['Gross Profit'].sum():,.2f} | Margin: {overall_margin:.2f}%")
print("\n===== TOP 5 PRODUCTS BY PROFIT =====")
print(prod.sort_values("Gross Profit", ascending=False)[["Product Name", "Sales", "Gross Profit", "Gross Margin %"]].head(5).round(2).to_string(index=False))
print("\n===== BOTTOM 5 PRODUCTS BY MARGIN =====")
print(prod.sort_values("Gross Margin %")[["Product Name", "Sales", "Gross Profit", "Gross Margin %"]].head(5).round(2).to_string(index=False))
print("\n===== DIVISIONS =====")
print(div.round(2).to_string(index=False))
print("\n===== PARETO =====")
print(f"Products giving 80% of revenue: {n80_rev} of {n_prod} ({n80_rev/n_prod*100:.0f}%)")
print(f"Products giving 80% of profit : {n80_prof} of {n_prod} ({n80_prof/n_prod*100:.0f}%)")
print(f"Top product share of profit: {prof_p['Gross Profit'].iloc[0]/prof_p['Gross Profit'].sum()*100:.1f}%")
print("\n===== CATEGORIES =====")
print(prod.groupby("Category")["Product Name"].apply(list).to_string())
print("\n===== ACTION FLAGS =====")
print(prod.groupby("Action Flag")["Product Name"].apply(list).to_string())
print("\nCharts saved in outputs/charts/ | Tables saved in outputs/")