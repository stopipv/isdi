import pandas as pd

#df = pd.read_csv('../static_data/app-flags.csv', index_col='appId', encoding='latin1', error_bad_lines="skip")
df = pd.read_csv('../static_data/app-flags.csv', encoding='latin1', error_bad_lines="skip")
df2 = df.groupby(df['appId']).agg({'flag':' AND '.join})

def flags_filter(d):
    print(d['human'].str.contains('1', regex=True))
    # check human flag too.
    if d.shape[0] > 1:
        print('')
        #print(d['human'].str.contains('1', regex=True).any())

df.groupby(df['appId']).apply(flags_filter)

print(df['human'].unique())

#print(df2)
#print(df2['flag'].unique())

#df3 = df2.groupby(df2['flag'].str.contains('AND'))#['flag'].apply(lambda x: 'hi')
#print(df3)
