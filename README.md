# Product Line Profitability & Margin Performance Analysis: Nassau Candy Distributor

An end-to-end data analytics project that finds which product lines and divisions truly drive profit for Nassau Candy Distributor, and where pricing, sourcing or portfolio decisions are needed.

## Key Findings
- Total sales **$141,784**, gross profit **$93,443**, overall gross margin **65.9%**.
- **5 of 15 products (33%)** generate 80% of both revenue and profit; the Chocolate division provides about 93% of revenue (a dependency risk).
- **Kazookles** has the weakest margin (7.7%).
- The **Other** division earns 44.8% margin versus 67.5% for Chocolate.

## Deliverables
| Deliverable | Location |
|---|---|
| Research paper (EDA, insights, recommendations) | `outputs/Nassau_Profitability_Research_Paper.docx` |
| Executive summary | `outputs/Executive_Summary.docx` |
| Interactive dashboard | `app.py` (Streamlit) |
| Charts and tables | `outputs/charts/`, `outputs/*.csv` |

## Project Structure
```
├── data/                 raw dataset
├── outputs/              cleaned data, tables, charts, reports
├── step2_explore.py      data exploration
├── step3_clean.py        data cleaning and validation
├── step4_analysis.py     metrics, Pareto, cost diagnostics, charts
├── step7_report.py       generates the Word reports
├── app.py                Streamlit dashboard
└── requirements.txt
```

## How to Run
```bash
python -m venv venv
venv\Scripts\activate          # Windows (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt

python step3_clean.py          # clean the data
python step4_analysis.py       # analysis and charts
python step7_report.py         # Word reports
streamlit run app.py           # dashboard
```

## Methodology
1. **Cleaning:** standardised labels, removed duplicates and invalid sales/cost/profit rows, filled missing units with product medians.
2. **Metrics:** Gross Margin %, Profit per Unit, Revenue and Profit Contribution, Margin Volatility.
3. **Analysis:** product ranking and grouping, division comparison, Pareto (80/20), cost-vs-sales diagnostics with action flags (repricing, cost renegotiation, discontinuation review).
4. **Dashboard:** insights, products, divisions, cost vs margin, concentration, trends and data tabs, with date range, division and region filters, a margin threshold slider and product search.

## Limitations
Only gross profit is available (no shipping, marketing or overhead costs). Some products have very small sales, so their margins should be read with caution.

## Author
Gopal Krushna Panda, B.Tech CSE, Centurion University of Technology and Management
[LinkedIn](https://www.linkedin.com/in/gopal-krushna-panda-878457364) | [GitHub](https://github.com/GOPALKRUSHNAPANDA)git add .**Live dashboard:**https://t4mu2kwpcnihi5qb7g2djj.streamlit.app/
git status