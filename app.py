import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

st.set_page_config(page_title="Nassau Candy Profitability", layout="wide")

@st.cache_data
def load_data():
    return pd.read_csv("outputs/clean_data.csv", parse_dates=["Order Date"])

df = load_data()

# ---------------- Sidebar filters ----------------
st.sidebar.title("Filters")
min_d, max_d = df["Order Date"].min().date(), df["Order Date"].max().date()
date_range = st.sidebar.date_input("Date range", (min_d, max_d), min_value=min_d, max_value=max_d)
divisions = st.sidebar.multiselect("Division", sorted(df["Division"].unique()),
                                   default=sorted(df["Division"].unique()))
overall = df["Gross Profit"].sum() / df["Sales"].sum() * 100
threshold = st.sidebar.slider("Margin threshold (%)", 0.0, 100.0, float(round(overall, 1)), 0.5)
search = st.sidebar.text_input("Product search")

if len(date_range) != 2:
    st.info("Please pick both a start and an end date.")
    st.stop()

f = df[(df["Order Date"].dt.date >= date_range[0]) & (df["Order Date"].dt.date <= date_range[1])]
f = f[f["Division"].isin(divisions)]
if search:
    f = f[f["Product Name"].str.contains(search, case=False, na=False)]
if f.empty:
    st.warning("No data for the selected filters.")
    st.stop()

# ---------------- Product table ----------------
prod = (f.groupby(["Product Name", "Division"])
          .agg({"Sales": "sum", "Units": "sum", "Gross Profit": "sum", "Cost": "sum"}).reset_index())
prod["Gross Margin %"] = prod["Gross Profit"] / prod["Sales"] * 100
prod["Profit per Unit"] = prod["Gross Profit"] / prod["Units"]
prod["Revenue Contribution %"] = prod["Sales"] / prod["Sales"].sum() * 100
prod["Profit Contribution %"] = prod["Gross Profit"] / prod["Gross Profit"].sum() * 100

tmp = f.assign(Month=f["Order Date"].dt.to_period("M").astype(str))
m = tmp.groupby(["Product Name", "Month"]).agg({"Sales": "sum", "Gross Profit": "sum"}).reset_index()
m["Margin"] = m["Gross Profit"] / m["Sales"] * 100
prod = prod.merge(m.groupby("Product Name")["Margin"].std().rename("Margin Volatility"),
                  on="Product Name", how="left").fillna({"Margin Volatility": 0})

med_s, med_p = prod["Sales"].median(), prod["Gross Profit"].median()
low = prod["Gross Margin %"] < threshold
prod["Action Flag"] = np.select(
    [low & (prod["Sales"] < med_s) & (prod["Gross Profit"] < med_p),
     low & (prod["Sales"] >= med_s), low],
    ["Discontinuation review", "Cost renegotiation", "Repricing"], default="Healthy")

# ---------------- Header and KPIs ----------------
st.title("Nassau Candy: Product Line Profitability Dashboard")
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Sales", f"${f['Sales'].sum():,.0f}")
k2.metric("Gross Profit", f"${f['Gross Profit'].sum():,.0f}")
k3.metric("Gross Margin", f"{f['Gross Profit'].sum() / f['Sales'].sum() * 100:.1f}%")
k4.metric("Units Sold", f"{f['Units'].sum():,.0f}")
k5.metric("Profit per Unit", f"${f['Gross Profit'].sum() / f['Units'].sum():.2f}")

tab1, tab2, tab3, tab4 = st.tabs(["Product Overview", "Division Performance",
                                  "Cost vs Margin", "Profit Concentration"])

# ---------------- Tab 1 ----------------
with tab1:
    st.subheader("Product margin leaderboard")
    lb = prod.sort_values("Gross Margin %", ascending=True)
    fig = px.bar(lb, x="Gross Margin %", y="Product Name", orientation="h",
                 color=np.where(lb["Gross Margin %"] < threshold, "Below threshold", "OK"),
                 color_discrete_map={"Below threshold": "#c0392b", "OK": "#2f6f8f"})
    fig.update_layout(legend_title_text="", height=500)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Profit contribution")
    pc = prod.sort_values("Profit Contribution %", ascending=False)
    st.plotly_chart(px.bar(pc, x="Product Name", y="Profit Contribution %", color="Division"),
                    use_container_width=True)

    st.subheader("Product table")
    st.dataframe(prod.sort_values("Gross Profit", ascending=False).round(2), use_container_width=True)

# ---------------- Tab 2 ----------------
with tab2:
    div = f.groupby("Division").agg({"Sales": "sum", "Gross Profit": "sum"}).reset_index()
    div["Gross Margin %"] = div["Gross Profit"] / div["Sales"] * 100
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Revenue vs profit")
        st.plotly_chart(px.bar(div.melt("Division", ["Sales", "Gross Profit"]),
                               x="Division", y="value", color="variable", barmode="group"),
                        use_container_width=True)
    with c2:
        st.subheader("Margin distribution (orders)")
        box = f.assign(**{"Order Margin %": f["Gross Profit"] / f["Sales"] * 100})
        st.plotly_chart(px.box(box, x="Division", y="Order Margin %", points=False),
                        use_container_width=True)
    st.dataframe(div.round(2), use_container_width=True)

# ---------------- Tab 3 ----------------
with tab3:
    st.subheader("Cost vs sales (points below the line are profitable)")
    fig = px.scatter(prod, x="Sales", y="Cost", size="Units", color="Action Flag",
                     hover_name="Product Name",
                     color_discrete_map={"Healthy": "#2f6f8f", "Repricing": "#e67e22",
                                         "Cost renegotiation": "#c0392b",
                                         "Discontinuation review": "#6c3483"})
    lim = max(prod["Sales"].max(), prod["Cost"].max())
    fig.add_trace(go.Scatter(x=[0, lim], y=[0, lim], mode="lines",
                             line=dict(dash="dash", color="gray"), name="Break-even"))
    st.plotly_chart(fig, use_container_width=True)
    st.subheader("Margin risk flags")
    st.dataframe(prod[prod["Action Flag"] != "Healthy"]
                 [["Product Name", "Division", "Sales", "Gross Profit", "Gross Margin %", "Action Flag"]]
                 .sort_values("Gross Margin %").round(2), use_container_width=True)

# ---------------- Tab 4 ----------------
with tab4:
    def pareto(col):
        t = prod.sort_values(col, ascending=False).reset_index(drop=True)
        t["Cum %"] = t[col].cumsum() / t[col].sum() * 100
        return t, int((t["Cum %"] < 80).sum() + 1)

    for col, label in [("Sales", "Revenue"), ("Gross Profit", "Profit")]:
        t, n80 = pareto(col)
        st.subheader(f"Pareto: {label}")
        a, b, c = st.columns(3)
        a.metric("Products for 80%", f"{n80} of {len(t)}")
        b.metric("Share of products", f"{n80 / len(t) * 100:.0f}%")
        c.metric("Top product share", f"{t[col].iloc[0] / t[col].sum() * 100:.1f}%")
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=t["Product Name"], y=t[col], name=label, marker_color="#2f6f8f"))
        fig.add_trace(go.Scatter(x=t["Product Name"], y=t["Cum %"], name="Cumulative %",
                                 mode="lines+markers", line=dict(color="#c0392b")), secondary_y=True)
        fig.add_hline(y=80, line_dash="dash", line_color="gray", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)