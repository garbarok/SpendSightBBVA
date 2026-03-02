"""Debug script to analyze Excel file structure."""
import pandas as pd
import sys

if len(sys.argv) < 2:
    print("Usage: python analyze_file_structure.py <path_to_excel_file>")
    sys.exit(1)

file_path = sys.argv[1]

print(f"Analyzing: {file_path}")
print("=" * 80)

try:
    xls = pd.ExcelFile(file_path)
    print(f"Sheet names: {xls.sheet_names}")
    print()

    # Read first sheet
    df = pd.read_excel(xls, sheet_name=0)

    print(f"Total rows: {len(df)}")
    print(f"Total columns: {len(df.columns)}")
    print()

    print("Column names from Excel:")
    for i, col in enumerate(df.columns):
        print(f"  {i}: '{col}'")
    print()

    print("First 10 rows (raw):")
    print(df.head(10).to_string())
    print()

    print("=" * 80)
    print("Rows 4-10 (where data usually starts):")
    if len(df) > 4:
        print(df.iloc[4:10].to_string())
    print()

    print("=" * 80)
    print("Column data types:")
    print(df.dtypes)

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
