import os
import pandas as pd

data_folder = "data"
files = [f for f in os.listdir(data_folder) if f.lower().endswith((".csv", ".xlsx", ".xls"))]

if not files:
    raise SystemExit("No dataset found in the 'data' folder. Copy your CSV/Excel file there first.")

file_path = os.path.join(data_folder, files[0])
print("Loading file:", file_path)

if file_path.lower().endswith(".csv"):
    try:
        df = pd.read_csv(file_path)
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, encoding="latin-1")
else:
    df = pd.read_excel(file_path)

print("\n=== SIZE ===")
print("Rows:", df.shape[0], "| Columns:", df.shape[1])

print("\n=== COLUMN NAMES ===")
print(list(df.columns))

print("\n=== FIRST 5 ROWS ===")
print(df.head().to_string())

print("\n=== DATA TYPES ===")
print(df.dtypes)

print("\n=== MISSING VALUES (per column) ===")
print(df.isnull().sum())

print("\n=== DUPLICATE ROWS ===")
print(df.duplicated().sum())

print("\n=== NUMBER SUMMARY ===")
print(df.describe().to_string())

print("\n=== UNIQUE VALUES ===")
for col in ["Division", "Region", "Ship Mode", "Product Name"]:
    if col in df.columns:
        print(f"\n{col} ({df[col].nunique()} unique):")
        print(df[col].value_counts().head(20))