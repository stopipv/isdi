import pandas as pd
import config
import dataset

def create_app_flags_file():
    dlist = []
    for k, v in config.source_files.items():
        d = pd.read_csv(v, index_col='appId')
        if k == 'offstore':
            d['relevant'] = 'y'
        elif (('relevant' not in d.columns) or (d.relevant.count() < len(d) * 0.5)) \
                and ('ml_score' in d.columns):
            ## TODO: Remove this or set 0.5 to 0.2 or something
            print("---->  Relevant column is missing or unpopulated... recreating")
            d['relevant'] = ((d['ml_score'] > 0.4) | d.get('relevant', pd.Series([])).fillna(False))\
                .apply(lambda x: 'y' if x else 'n')
        print('done reading: {} (l={})'.format(k, len(d)))
        d = d.query('relevant == "y"')
        r = pd.DataFrame(columns=['store', 'flag', 'title'], index=d.index)
        r['title'] = d['title']
        r['store'] = k
        r['flag'] = 'dual-use' if k != 'offstore' else 'spyware'
        dlist.append(r)
    fulld = pd.concat(dlist)
    spyware = pd.read_csv(config.spyware_list_file, index_col='appId')
    fulld.loc[spyware.index, 'flag'] = 'spyware'
    fulld.to_csv(config.APP_FLAGS_FILE)


def create_app_info_dict():
    dlist = []
    conn = dataset.connect(config.APP_INFO_SQLITE_FILE)
    for k, v in config.source_files.items():
        d = pd.read_csv(v, index_col='appId')

        d['store'] = k
        if 'permissions' not in d.columns:
            print(d.columns)
            d.assign(permissions=["<not recorded>"]*len(d))
        d.columns = d.columns.str.lower().str.replace(' ', '-').str.replace('-', '_')
        dlist.append(d)
    pd.concat(dlist).to_sql('apps', conn.engine, if_exists='replace')
    conn.engine.execute('create index idx_appId on apps(appId)')

if __name__ == "__main__":
    create_app_flags_file()
    create_app_info_dict()