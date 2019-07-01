# coding: utf-8
import pandas as pd
import sqlite3
conn1 = sqlite3.connect('./data/fieldstudy.db')
conn2 = sqlite3.connect('../../alpha_scanner/phone_scanner/data/fieldstudy.db')
#app_counts = pd.read_sql('select count(*) from app_info group by scanid;', conn1)
app_counts = pd.read_sql('select count(*) from app_info A, scan_res S where A.scanid=S.id group by A.scanid;', conn1)

# september consult from alpha scanner
app_counts_alphasc = pd.read_sql('select count(*) from app_info where scanid in (310,311,312,313) group by scanid;', conn2)

app_counts = app_counts.append(app_counts_alphasc)
print(app_counts.median(axis=0))
