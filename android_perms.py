from run import run_command, catch_err
import pandas as pd
from itertools import zip_longest
MAP = 'outf.permissions'

'''
def match_keys(d, keys, only_last=False):
    ret = []
    # print(keys)
    # print(keys)
    for sk in keys.split('//'):
        sk = re.compile(sk)
        for k, v in d.items():
            if sk.match(k):
                ret.append(k)
                d = d[k]
                break
    if only_last:
        return 'key=NOTFOUND' if not ret else ret[-1]
    else:
        return ret

def extract(d, lkeys):
    for k in lkeys:
        d = d.get(k, {})
    return d

def split_equalto_delim(k):
    return k.split('=', 1)

package = extract(
            d,
            match_keys(d, '^package$//^Packages//^Package \[{}\].*'.format(appid))
        )
        res = dict(
            split_equalto_delim(match_keys(package, v, only_last=True))
            for v in ['userId', 'firstInstallTime', 'lastUpdateTime']
        )
'''

def permissions_used(appid):
    # FIXME: add check on all permissions, too.
    cmd = '{cli} shell dumpsys package {app}'
    app_permissions = catch_err(run_command(cmd, app=appid))
    print(app_permissions)

    # need to get 
    # requested permissions:
    # install permissions:
    # runtime permissions:
    
    cmd = '{cli} shell appops get {app}'
    recently_used = catch_err(run_command(cmd, app=appid))
    recently_used = recently_used.split("\n")
    for perm in recently_used:
        print(perm.split(";"))

def gather_permissions_labels():
    # FIXME: would probably put in global db?
    cmd = '{cli} shell pm list permissions -f > {outf}'
    perms = catch_err(run_command(cmd, outf=MAP))

def map_permissions():
    cols = ['permission','package','label','description','protectionLevel']
    df = pd.DataFrame(columns=cols)
    with open(MAP, 'r') as fh:
        # skip header
        next(fh), next(fh)
        record = {}
        for line in fh:
            record[cols[0]] = line.split(':')[1].strip()
            for col in cols[1:]:
                record[col] = next(fh).split(':')[1].strip()
            df.loc[df.shape[0]] = record
    return df

if __name__ == '__main__':
    app_perms = permissions_used('net.cybrook.trackview')
    #gather_permissions_labels()

    #permsdf = map_permissions()
    #human_friendly = permsdf[permsdf['label'] != 'null']
    #human_friendly_desc = permsdf[permsdf['description'] != 'null']
