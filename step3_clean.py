import os
import re
import pandas as pd
import numpy as np

# ---------- 1. Load the raw file ----------
data_folder = "data"
files = [f for f in os.listdir(data_folder) if f.lower().endswith((".csv", ".xlsx", ".xls"))]
if not files:
    raise SystemExit("No dataset found in the 'data' folder.")

file_path = os.path.join(data_folder, files[0])
if file_path.lower().endswith(".csv"):
    try:
        df = pd.read_csv(file_path)
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, encoding="latin-1")
else:
    df = pd.read_excel(file_path)

log = []  # cleaning report
log.append(("Rows in raw file", len(df)))

# ---------- 2. Standardize column names ----------
df.columns = [re.sub(r"\s+", " ", str(c)).strip() for c in df.columns]

name_map = {
    "row id": "Row ID", "order id": "Order ID", "order date": "Order Date",
    "ship date": "Ship Date", "ship mode": "Ship Mode", "customer id": "Customer ID",
    "country/region": "Country/Region", "city": "City", "state/province": "State/Province",
    "postal code": "Postal Code", "division": "Division", "region": "Region",
    "product id": "Product ID", "product name": "Product Name", "sales": "Sales",
    "units": "Units", "gross profit": "Gross Profit", "cost": "Cost",
}
df = df.rename(columns={c: name_map[c.lower()] for c in df.columns if c.lower() in name_map})

required = ["Order Date", "Division", "Product Name", "Sales", "Units", "Gross Profit", "Cost"]
missing_cols = [c for c in required if c not in df.columns]
if missing_cols:
    raise SystemExit(f"These required columns were not found: {missing_cols}\nYour columns: {list(df.columns)}")

# ---------- 3. Fix data types ----------
for col in ["Sales", "Units", "Gross Profit", "Cost"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce", dayfirst=True)
if "Ship Date" in df.columns:
    df["Ship Date"] = pd.to_datetime(df["Ship Date"], errors="coerce", dayfirst=True)

# ---------- 4. Standardize text labels ----------
def clean_text(s):
    return re.sub(r"\s+", " ", str(s)).strip()

for col in ["Division", "Region", "Ship Mode", "Product Name", "State/Province", "City"]:
    if col in df.columns:
        df[col] = df[col].astype(str).map(clean_text)

df["Division"] = df["Division"].str.title()
df["Product Name"] = df["Product Name"].str.replace(r"\s*-\s*", " - ", regex=True)

# ---------- 5. Remove duplicates ----------
before = len(df)
df = df.drop_duplicates()
log.append(("Duplicate rows removed", before - len(df)))

# ---------- 6. Remove invalid rows ----------
before = len(df)
df = df.dropna(subset=["Order Date"])
log.append(("Rows removed: invalid/missing Order Date", before - len(df)))

before = len(df)
df = df.dropna(subset=["Sales", "Cost", "Gross Profit"])
log.append(("Rows removed: missing Sales/Cost/Profit", before - len(df)))

before = len(df)
df = df[df["Sales"] > 0]
log.append(("Rows removed: zero or negative Sales", before - len(df)))

before = len(df)
df = df[df["Cost"] >= 0]
log.append(("Rows removed: negative Cost", before - len(df)))

# ---------- 7. Handle missing / invalid Units ----------
df.loc[df["Units"] <= 0, "Units"] = np.nan
missing_units = int(df["Units"].isna().sum())
product_median_units = df.groupby("Product Name")["Units"].transform("median")
df["Units"] = df["Units"].fillna(product_median_units)
log.append(("Missing/invalid Units filled with product median", missing_units))

before = len(df)
df = df.dropna(subset=["Units"])
log.append(("Rows removed: Units still missing", before - len(df)))

# ---------- 8. Check Gross Profit = Sales - Cost ----------
mismatch = (df["Gross Profit"] - (df["Sales"] - df["Cost"])).abs() > 0.05
log.append(("Rows where Gross Profit != Sales - Cost (kept, for review)", int(mismatch.sum())))

# ---------- 9. Save ----------
os.makedirs("outputs", exist_ok=True)
df = df.reset_index(drop=True)
df.to_csv("outputs/clean_data.csv", index=False)
log.append(("Rows in clean file", len(df)))
pd.DataFrame(log, columns=["Step", "Rows"]).to_csv("outputs/cleaning_log.csv", index=False)

# ---------- 10. Report ----------
print("\n========== CLEANING REPORT ==========")
for label, value in log:
    print(f"{label}: {value}")

print("\nDate range:", df["Order Date"].min().date(), "to", df["Order Date"].max().date())
print("Divisions:", sorted(df["Division"].unique()))
print("Products:", df["Product Name"].nunique())
print("\nTotal Sales:", round(df["Sales"].sum(), 2))
print("Total Gross Profit:", round(df["Gross Profit"].sum(), 2))
print("\nSaved: outputs/clean_data.csv and outputs/cleaning_log.csv")