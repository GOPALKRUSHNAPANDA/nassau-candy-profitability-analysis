import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# =====================================================
# PAGE SETUP AND STYLE
# =====================================================
st.set_page_config(page_title="Nassau Candy | Profitability", page_icon="🍬", layout="wide")

NAVY, TEAL, RED, ORANGE, PURPLE, GREY = "#1F3A4D", "#1F6F8B", "#C0392B", "#E67E22", "#6C3483", "#7F8C8D"
FLAG_COLORS = {"Healthy": TEAL, "Repricing": ORANGE, "Cost renegotiation": RED, "Discontinuation review": PURPLE}

st.markdown(f"""
<style>
#MainMenu, footer {{visibility: hidden;}}
.block-container {{padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1400px;}}
.banner {{background: linear-gradient(120deg, {NAVY} 0%, {TEAL} 100%); color: white;
          padding: 26px 32px; border-radius: 14px; margin-bottom: 18px;}}
.banner h1 {{color: white; margin: 0; font-size: 1.9rem; font-weight: 700;}}
.banner p {{margin: 4px 0 0 0; opacity: 0.85; font-size: 0.95rem;}}
.kpi {{background: white; border-radius: 12px; padding: 16px 18px; border-left: 5px solid {TEAL};
       box-shadow: 0 1px 6px rgba(0,0,0,0.07);}}
.kpi-label {{font-size: 0.78rem; color: #6B7C8C; text-transform: uppercase; letter-spacing: 0.06em;}}
.kpi-value {{font-size: 1.65rem; font-weight: 700; color: {NAVY}; margin-top: 2px;}}
.kpi-sub {{font-size: 0.8rem; color: #6B7C8C; margin-top: 2px;}}
.insight {{background: white; border-radius: 12px; padding: 14px 18px; margin-bottom: 10px;
           box-shadow: 0 1px 6px rgba(0,0,0,0.07);}}
.insight.good {{border-left: 5px solid #27AE60;}}
.insight.bad {{border-left: 5px solid {RED};}}
.insight.warn {{border-left: 5px solid {ORANGE};}}
.insight.info {{border-left: 5px solid {TEAL};}}
.insight b {{color: {NAVY};}}
.stTabs [data-baseweb="tab-list"] {{gap: 6px;}}
.stTabs [data-baseweb="tab"] {{background: white; border-radius: 8px 8px 0 0; padding: 10px 18px; font-weight: 600;}}
.stTabs [aria-selected="true"] {{background: {TEAL}; color: white !important;}}
.section-title {{font-size: 1.15rem; font-weight: 700; color: {NAVY}; margin: 6px 0 2px 0;}}
</style>
""", unsafe_allow_html=True)


def style(fig, height=420):
    fig.update_layout(template="plotly_white", height=height, margin=dict(l=10, r=10, t=45, b=10),
                      font=dict(family="Segoe UI, sans-serif", size=13), legend_title_text="",
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig


def kpi(col, label, value, sub=""):
    col.markdown(f'<div class="kpi"><div class="kpi-label">{label}</div>'
                 f'<div class="kpi-value">{value}</div><div class="kpi-sub">{sub}</div></div>',
                 unsafe_allow_html=True)


def insight(kind, text):
    st.markdown(f'<div class="insight {kind}">{text}</div>', unsafe_allow_html=True)


def title(text):
    st.markdown(f'<div class="section-title">{text}</div>', unsafe_allow_html=True)


def money(x):
    return f"${x:,.0f}"


# =====================================================
# DATA
# =====================================================
@st.cache_data
def load_data():
    return pd.read_csv("outputs/clean_data.csv", parse_dates=["Order Date"])


df = load_data()

# =====================================================
# SIDEBAR FILTERS
# =====================================================
st.sidebar.markdown("## 🍬 Filters")
min_d, max_d = df["Order Date"].min().date(), df["Order Date"].max().date()
date_range = st.sidebar.date_input("Date range", (min_d, max_d), min_value=min_d, max_value=max_d)
divisions = st.sidebar.multiselect("Division", sorted(df["Division"].unique()),
                                   default=sorted(df["Division"].unique()))
if "Region" in df.columns:
    regions = st.sidebar.multiselect("Region", sorted(df["Region"].dropna().unique()),
                                     default=sorted(df["Region"].dropna().unique()))
else:
    regions = None

overall_all = df["Gross Profit"].sum() / df["Sales"].sum() * 100
threshold = st.sidebar.slider("Margin threshold (%)", 0.0, 100.0, float(round(overall_all, 1)), 0.5,
                              help="Products below this margin are flagged as risks.")
search = st.sidebar.text_input("Search product", placeholder="e.g. wonka")
st.sidebar.markdown("---")
st.sidebar.caption("Nassau Candy Distributor\nProduct Line Profitability Analysis")

if len(date_range) != 2:
    st.info("Please pick both a start date and an end date.")
    st.stop()

f = df[(df["Order Date"].dt.date >= date_range[0]) & (df["Order Date"].dt.date <= date_range[1])]
f = f[f["Division"].isin(divisions)]
if regions is not None:
    f = f[f["Region"].isin(regions)]
if search:
    f = f[f["Product Name"].str.contains(search, case=False, na=False)]
if f.empty:
    st.warning("No data for the selected filters. Try widening them.")
    st.stop()

# =====================================================
# CALCULATIONS
# =====================================================
prod = (f.groupby(["Product Name", "Division"])
          .agg({"Sales": "sum", "Units": "sum", "Gross Profit": "sum", "Cost": "sum"}).reset_index())
prod["Gross Margin %"] = prod["Gross Profit"] / prod["Sales"] * 100
prod["Profit per Unit"] = prod["Gross Profit"] / prod["Units"]
prod["Cost % of Sales"] = prod["Cost"] / prod["Sales"] * 100
prod["Revenue Contribution %"] = prod["Sales"] / prod["Sales"].sum() * 100
prod["Profit Contribution %"] = prod["Gross Profit"] / prod["Gross Profit"].sum() * 100

f = f.assign(Month=f["Order Date"].dt.to_period("M").dt.to_timestamp())
mp = f.groupby(["Product Name", "Month"]).agg({"Sales": "sum", "Gross Profit": "sum"}).reset_index()
mp["Margin"] = mp["Gross Profit"] / mp["Sales"] * 100
prod = prod.merge(mp.groupby("Product Name")["Margin"].std().rename("Margin Volatility"),
                  on="Product Name", how="left").fillna({"Margin Volatility": 0})

med_s, med_p = prod["Sales"].median(), prod["Gross Profit"].median()
low = prod["Gross Margin %"] < threshold
prod["Action Flag"] = np.select(
    [low & (prod["Sales"] < med_s) & (prod["Gross Profit"] < med_p), low & (prod["Sales"] >= med_s), low],
    ["Discontinuation review", "Cost renegotiation", "Repricing"], default="Healthy")

total_sales, total_profit = f["Sales"].sum(), f["Gross Profit"].sum()
total_units = f["Units"].sum()
margin = total_profit / total_sales * 100


def pareto(col):
    t = prod.sort_values(col, ascending=False).reset_index(drop=True)
    t["Cum %"] = t[col].cumsum() / t[col].sum() * 100
    return t, int((t["Cum %"] < 80).sum() + 1)


# =====================================================
# HEADER AND KPI CARDS
# =====================================================
st.markdown(f"""
<div class="banner">
  <h1>🍬 Nassau Candy: Product Line Profitability</h1>
  <p>Which products truly drive profit, which divisions lag, and where to act.
     Showing {date_range[0]:%d %b %Y} to {date_range[1]:%d %b %Y} | {len(prod)} products | {len(f):,} orders</p>
</div>
""", unsafe_allow_html=True)

c1, c2, c3, c4, c5 = st.columns(5)
kpi(c1, "Total Sales", money(total_sales), f"{len(f):,} orders")
kpi(c2, "Gross Profit", money(total_profit), f"Cost {money(f['Cost'].sum())}")
diff = margin - threshold
kpi(c3, "Gross Margin", f"{margin:.1f}%", f"{'▲' if diff >= 0 else '▼'} {abs(diff):.1f} pts vs threshold")
kpi(c4, "Units Sold", f"{total_units:,.0f}", f"{money(total_sales / total_units)} avg price/unit")
kpi(c5, "Profit per Unit", f"${total_profit / total_units:.2f}", f"{(prod['Action Flag'] != 'Healthy').sum()} products flagged")
st.write("")

tab0, tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["💡 Insights", "📦 Products", "🏭 Divisions", "💰 Cost vs Margin", "📊 Concentration", "📈 Trends", "🗂 Data"])

# =====================================================
# TAB 0: INSIGHTS
# =====================================================
with tab0:
    left, right = st.columns([3, 2])
    with left:
        title("Automatic insights for the current filters")
        top = prod.sort_values("Gross Profit", ascending=False).iloc[0]
        worst = prod.sort_values("Gross Margin %").iloc[0]
        best = prod.sort_values("Gross Margin %", ascending=False).iloc[0]
        tp, n80 = pareto("Gross Profit")
        topdiv = f.groupby("Division")["Sales"].sum().sort_values(ascending=False)
        insight("good", f"<b>Top profit driver:</b> {top['Product Name']} earns {money(top['Gross Profit'])} "
                        f"({top['Profit Contribution %']:.1f}% of total profit).")
        insight("good", f"<b>Best margin:</b> {best['Product Name']} at {best['Gross Margin %']:.1f}%.")
        insight("bad", f"<b>Weakest margin:</b> {worst['Product Name']} at {worst['Gross Margin %']:.1f}% "
                       f"(cost takes {worst['Cost % of Sales']:.0f}% of its sales).")
        insight("warn", f"<b>Concentration:</b> {n80} of {len(prod)} products ({n80 / len(prod) * 100:.0f}%) "
                        f"generate 80% of profit.")
        insight("warn", f"<b>Division dependency:</b> {topdiv.index[0]} provides "
                        f"{topdiv.iloc[0] / topdiv.sum() * 100:.1f}% of revenue.")
        n_flag = int((prod["Action Flag"] != "Healthy").sum())
        insight("info", f"<b>Margin risk:</b> {n_flag} product(s) are below the {threshold:.1f}% threshold. "
                        f"See the Cost vs Margin tab for the action list.")
    with right:
        title("Margin vs threshold")
        gauge = go.Figure(go.Indicator(
            mode="gauge+number", value=margin, number={"suffix": "%", "valueformat": ".1f"},
            gauge={"axis": {"range": [0, 100]}, "bar": {"color": TEAL},
                   "steps": [{"range": [0, threshold], "color": "#F5C6C0"},
                             {"range": [threshold, 100], "color": "#D5EBE1"}],
                   "threshold": {"line": {"color": RED, "width": 4}, "value": threshold}}))
        st.plotly_chart(style(gauge, 300), use_container_width=True)
        st.caption("Red line = your margin threshold. Green zone = above threshold.")

    title("Where the money comes from (size = sales, color = margin)")
    tm = px.treemap(prod, path=["Division", "Product Name"], values="Sales", color="Gross Margin %",
                    color_continuous_scale="RdYlGn", color_continuous_midpoint=threshold)
    st.plotly_chart(style(tm, 450), use_container_width=True)

# =====================================================
# TAB 1: PRODUCTS
# =====================================================
with tab1:
    title("Product margin leaderboard")
    lb = prod.sort_values("Gross Margin %", ascending=True)
    fig = px.bar(lb, x="Gross Margin %", y="Product Name", orientation="h",
                 color=np.where(lb["Gross Margin %"] < threshold, "Below threshold", "At or above threshold"),
                 color_discrete_map={"Below threshold": RED, "At or above threshold": TEAL},
                 text=lb["Gross Margin %"].round(1).astype(str) + "%")
    fig.add_vline(x=threshold, line_dash="dash", line_color=GREY)
    fig.update_traces(textposition="outside")
    st.plotly_chart(style(fig, max(380, 32 * len(lb) + 120)), use_container_width=True)

    a, b = st.columns(2)
    with a:
        title("Profit contribution")
        pc = prod.sort_values("Profit Contribution %", ascending=False)
        st.plotly_chart(style(px.bar(pc, x="Product Name", y="Profit Contribution %", color="Division",
                                     color_discrete_sequence=[TEAL, ORANGE, PURPLE])), use_container_width=True)
    with b:
        title("Profit per unit")
        pu = prod.sort_values("Profit per Unit", ascending=False)
        st.plotly_chart(style(px.bar(pu, x="Product Name", y="Profit per Unit", color="Division",
                                     color_discrete_sequence=[TEAL, ORANGE, PURPLE])), use_container_width=True)

    title("Product table")
    show = prod.sort_values("Gross Profit", ascending=False).round(2)
    st.dataframe(show, use_container_width=True, hide_index=True,
                 column_config={"Gross Margin %": st.column_config.ProgressColumn(
                     "Gross Margin %", min_value=0, max_value=100, format="%.1f%%")})

# =====================================================
# TAB 2: DIVISIONS
# =====================================================
with tab2:
    div = f.groupby("Division").agg({"Sales": "sum", "Gross Profit": "sum", "Cost": "sum"}).reset_index()
    div["Gross Margin %"] = div["Gross Profit"] / div["Sales"] * 100
    div["Revenue Share %"] = div["Sales"] / div["Sales"].sum() * 100
    div["Profit Share %"] = div["Gross Profit"] / div["Gross Profit"].sum() * 100

    a, b = st.columns(2)
    with a:
        title("Revenue vs profit")
        st.plotly_chart(style(px.bar(div.melt("Division", ["Sales", "Gross Profit"]), x="Division", y="value",
                                     color="variable", barmode="group",
                                     color_discrete_map={"Sales": GREY, "Gross Profit": TEAL})),
                        use_container_width=True)
    with b:
        title("Revenue share vs profit share")
        sh = div.melt("Division", ["Revenue Share %", "Profit Share %"])
        st.plotly_chart(style(px.bar(sh, x="Division", y="value", color="variable", barmode="group",
                                     color_discrete_map={"Revenue Share %": GREY, "Profit Share %": TEAL})),
                        use_container_width=True)
    a, b = st.columns(2)
    with a:
        title("Order margin distribution")
        box = f.assign(**{"Order Margin %": f["Gross Profit"] / f["Sales"] * 100})
        st.plotly_chart(style(px.box(box, x="Division", y="Order Margin %", color="Division", points=False,
                                     color_discrete_sequence=[TEAL, ORANGE, PURPLE])), use_container_width=True)
    with b:
        title("Division margin")
        st.plotly_chart(style(px.bar(div.sort_values("Gross Margin %"), x="Gross Margin %", y="Division",
                                     orientation="h", color="Gross Margin %", color_continuous_scale="RdYlGn",
                                     text=div.sort_values("Gross Margin %")["Gross Margin %"].round(1))),
                        use_container_width=True)
    st.dataframe(div.round(2), use_container_width=True, hide_index=True)

# =====================================================
# TAB 3: COST VS MARGIN
# =====================================================
with tab3:
    title("Cost vs sales (points below the dashed line are profitable)")
    fig = px.scatter(prod, x="Sales", y="Cost", size="Units", color="Action Flag", hover_name="Product Name",
                     color_discrete_map=FLAG_COLORS, size_max=45)
    lim = max(prod["Sales"].max(), prod["Cost"].max())
    fig.add_trace(go.Scatter(x=[0, lim], y=[0, lim], mode="lines", name="Break-even",
                             line=dict(dash="dash", color=GREY)))
    st.plotly_chart(style(fig, 480), use_container_width=True)

    a, b = st.columns([2, 3])
    with a:
        title("Flags summary")
        cnt = prod["Action Flag"].value_counts().reset_index()
        cnt.columns = ["Flag", "Products"]
        st.plotly_chart(style(px.pie(cnt, names="Flag", values="Products", hole=0.55, color="Flag",
                                     color_discrete_map=FLAG_COLORS), 340), use_container_width=True)
    with b:
        title("Margin risk list")
        risk = prod[prod["Action Flag"] != "Healthy"].sort_values("Gross Margin %")
        if risk.empty:
            st.success("No products are below the selected margin threshold.")
        else:
            st.dataframe(risk[["Product Name", "Division", "Sales", "Gross Profit", "Gross Margin %", "Action Flag"]]
                         .round(2), use_container_width=True, hide_index=True)

# =====================================================
# TAB 4: CONCENTRATION
# =====================================================
with tab4:
    for col, label in [("Sales", "Revenue"), ("Gross Profit", "Profit")]:
        t, n80 = pareto(col)
        title(f"Pareto: {label}")
        a, b, c = st.columns(3)
        kpi(a, "Products for 80%", f"{n80} of {len(t)}", f"{n80 / len(t) * 100:.0f}% of the range")
        kpi(b, "Top product share", f"{t[col].iloc[0] / t[col].sum() * 100:.1f}%", t["Product Name"].iloc[0])
        top3 = t[col].head(3).sum() / t[col].sum() * 100
        kpi(c, "Top 3 products", f"{top3:.1f}%", "of total " + label.lower())
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=t["Product Name"], y=t[col], name=label, marker_color=TEAL))
        fig.add_trace(go.Scatter(x=t["Product Name"], y=t["Cum %"], name="Cumulative %", mode="lines+markers",
                                 line=dict(color=RED)), secondary_y=True)
        fig.add_hline(y=80, line_dash="dash", line_color=GREY, secondary_y=True)
        fig.update_yaxes(range=[0, 105], secondary_y=True)
        st.plotly_chart(style(fig, 420), use_container_width=True)
        if n80 / len(t) < 0.4:
            st.warning(f"Dependency risk: only {n80 / len(t) * 100:.0f}% of products generate 80% of {label.lower()}.")

# =====================================================
# TAB 5: TRENDS
# =====================================================
with tab5:
    title("Monthly sales, profit and margin")
    mo = f.groupby("Month").agg({"Sales": "sum", "Gross Profit": "sum"}).reset_index()
    mo["Margin %"] = mo["Gross Profit"] / mo["Sales"] * 100
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=mo["Month"], y=mo["Sales"], name="Sales", marker_color="#B8C4CE"))
    fig.add_trace(go.Bar(x=mo["Month"], y=mo["Gross Profit"], name="Gross Profit", marker_color=TEAL))
    fig.add_trace(go.Scatter(x=mo["Month"], y=mo["Margin %"], name="Margin %", mode="lines+markers",
                             line=dict(color=RED)), secondary_y=True)
    fig.update_layout(barmode="group")
    st.plotly_chart(style(fig, 430), use_container_width=True)

    title("Margin heatmap: division by month")
    hm = f.groupby(["Division", "Month"]).agg({"Sales": "sum", "Gross Profit": "sum"}).reset_index()
    hm["Margin %"] = hm["Gross Profit"] / hm["Sales"] * 100
    piv = hm.pivot(index="Division", columns="Month", values="Margin %")
    piv.columns = [c.strftime("%b %Y") for c in piv.columns]
    st.plotly_chart(style(px.imshow(piv, color_continuous_scale="RdYlGn", aspect="auto"), 300),
                    use_container_width=True)

    if "Region" in f.columns:
        a, b = st.columns(2)
        with a:
            title("Performance by region")
            rg = f.groupby("Region").agg({"Sales": "sum", "Gross Profit": "sum"}).reset_index()
            st.plotly_chart(style(px.bar(rg.melt("Region", ["Sales", "Gross Profit"]), x="Region", y="value",
                                         color="variable", barmode="group",
                                         color_discrete_map={"Sales": GREY, "Gross Profit": TEAL})),
                            use_container_width=True)
        with b:
            if "State/Province" in f.columns:
                title("Top 10 states by profit")
                stt = (f.groupby("State/Province")["Gross Profit"].sum().sort_values(ascending=False)
                        .head(10).reset_index().sort_values("Gross Profit"))
                st.plotly_chart(style(px.bar(stt, x="Gross Profit", y="State/Province", orientation="h",
                                             color_discrete_sequence=[TEAL])), use_container_width=True)

# =====================================================
# TAB 6: DATA
# =====================================================
with tab6:
    title("Download results")
    d1, d2 = st.columns(2)
    d1.download_button("⬇ Product metrics (CSV)", prod.round(2).to_csv(index=False).encode("utf-8"),
                       "product_metrics_filtered.csv", "text/csv")
    d2.download_button("⬇ Filtered orders (CSV)", f.drop(columns=["Month"]).to_csv(index=False).encode("utf-8"),
                       "filtered_orders.csv", "text/csv")
    title("Filtered order data (first 500 rows)")
    st.dataframe(f.drop(columns=["Month"]).head(500), use_container_width=True, hide_index=True)

st.caption("Gross profit = Sales − Cost. Flags compare each product's margin with the threshold set in the sidebar.")