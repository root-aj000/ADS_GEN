# check_csv.py
import pandas as pd
from config.settings import cfg

df = pd.read_csv(cfg.paths.csv_input)

print("First 5 rows - 'keywords' column:")
for i, row in df.head().iterrows():
    kw = str(row.get('img_desc', ''))
    print(f"  Row {i}: '{kw}' (len={len(kw)}, chars={list(kw[:20])})")

# print("\nFirst 5 rows - 'object_detected' column:")
# for i, row in df.head().iterrows():
#     obj = str(row.get('object_detected', ''))
#     print(f"  Row {i}: '{obj}' (len={len(obj)})")