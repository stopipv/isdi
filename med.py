import pandas as pd
import sqlite3
conn1 = sqlite3.connect('./data/fieldstudy.db')
conn2 = sqlite3.connect('../../alpha_scanner/phone_scanner/data/fieldstudy.db')
app_counts = pd.read_sql('select count(*) from app_info where scanid in (1, 2, 3, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92) group by scanid;', conn1)

# september consult from alpha scanner
app_counts_alphasc = pd.read_sql('select count(*) from app_info where scanid in (310,311,312,313) group by scanid;', conn2)

app_counts = app_counts.append(app_counts_alphasc)
print(app_counts.median(axis=0))
