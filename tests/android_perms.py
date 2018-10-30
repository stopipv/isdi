from rsonlite import simpleparse
from run import run_command, catch_err
import pandas as pd
from itertools import zip_longest
MAP = 'Pixel2.permissions'
DUMPPKG = 'dumppkg'

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
    #cmd = '{cli} shell dumpsys package {app}'
    #app_permissions = catch_err(run_command(cmd, app=appid))
    #print(app_permissions)

    # switch to top method after tests
    package_dump = open(DUMPPKG, 'r').read()
    #print(package_dump)
    sp = simpleparse(package_dump)
    try:
        pkg = [v for k,v in sp['Packages:'].items() if appid in k][0]
    except IndexError as e:
        print(e)
        print('Didn\'t parse correctly. Not sure why.')
        exit(0)

    #print(pkg['install permissions:'])
    install_perms = [k.split(':')[0] for k,v in pkg['install permissions:'].items()]
    requested_perms = pkg['requested permissions:']
    install_date = pkg['firstInstallTime']

    all_perms = list(set(requested_perms) | set(install_perms))

    # need to get 
    # requested permissions:
    # install permissions:
    # runtime permissions:
    
     

    #cmd = '{cli} shell appops get {app}'
    #recently_used = catch_err(run_command(cmd, app=appid))
    #recently_used = recently_used.split("\n")
    #for perm in recently_used:
    #    print(perm.split(";"))
    return all_perms
    
def gather_permissions_labels():
    # FIXME: would probably put in global db?

    cmd = '{cli} shell getprop ro.product.model'
    model = catch_err(run_command(cmd, outf=MAP)).strip().replace(' ','_')
    cmd = '{cli} shell pm list permissions -g -f > {outf}'
    perms = catch_err(run_command(cmd, outf=model+'.permissions'))

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

from rsonlite import simpleparse
import pandas as pd
def permissions_map():
    groupcols = ['group','group_package','group_label','group_description']
    pcols = ['permission','package','label','description','protectionLevel']
    sp = simpleparse(open('Pixel2.permissions','r').read())
    df = pd.DataFrame(columns=groupcols+pcols)
    record = {}
    ungrouped_d = dict.fromkeys(groupcols, 'ungrouped')
    for group in sp[1]:
        record['group'] = group.split(':')[1]
        if record['group'] == '':
            for permission in sp[1][group]:
                record['permission'] = permission.split(':')[1]
                for permission_attr in sp[1][group][permission]:
                    label, val = permission_attr.split(':')
                    record[label.replace('+ ','')] = val
                df.loc[df.shape[0]] = {**record, **ungrouped_d}
        else:
            for group_attr in sp[1][group]:
                if isinstance(group_attr, str):
                    label, val = group_attr.split(':')
                    record['group_'+label.replace('+ ','')] = val
                else:
                    for permission in group_attr:
                        record['permission'] = permission.split(':')[1]
                        for permission_attr in group_attr[permission]:
                            label, val = permission_attr.split(':')
                            record[label.replace('+ ','')] = val
                        df.loc[df.shape[0]] = record
    return df

def _deprecated_map_ungrouped_permissions():
    # TODO: should store this as csv when done and keep it static.

    groupcols = ['group','group_package','group_label','group_description']
    pcols = ['permission','package','label','description','protectionLevel']
    df = pd.DataFrame(columns=groupcols+pcols)
    with open(MAP, 'r') as fh:
        # skip header
        next(fh), next(fh)
        group_record = {}
        record = {}
        ungrouped = False
        ungrouped_d = dict.fromkeys(groupcols, 'ungrouped')
        for line in fh:
            try:
                if 'ungrouped' in line.split(':')[0]:
                    ungrouped = True
                    next(fh)
                if not ungrouped:
                    group_record[groupcols[0]] = line.split(':')[1].strip()
                    for col in groupcols[1:]:
                        group_record[col] = next(fh).split(':')[1].strip()
                    permission = next(fh)
                    while permission != '\n':
                        record[pcols[0]] = permission.split(':')[1].strip()
                        for col in pcols[1:]:
                            record[col] = next(fh).split(':')[1].strip()
                        df.loc[df.shape[0]] = {**group_record, **record}
                        permission = next(fh)
                else:
                    record[pcols[0]] = line.split(':')[1].strip()
                    for col in pcols[1:]:
                        record[col] = next(fh).split(':')[1].strip()
                    df.loc[df.shape[0]] = {**record, **ungrouped_d}
            except StopIteration:
                continue
    return df        

if __name__ == '__main__':
    permsdf = permissions_map()
    permsdf_d = _deprecated_map_ungrouped_permissions()
    
    diff = permsdf == permsdf_d
    print(diff.sum())
    exit()
    app_perms = permissions_used('net.cybrook.trackview')
    permsdf = permissions_map()
    labelsmap = permsdf[permsdf['permission'].isin(app_perms)]
    
    hf_permissions = list(zip(labelsmap.permission, labelsmap.label))
    print('Permissions on app were:')
    for permission in hf_permissions:
        print(permission)
    print('Missing:')
    print(set(app_perms) - set(labelsmap['permission'].tolist()))

def test():
    app_perms = permissions_used('net.cybrook.trackview')
    #gather_permissions_labels()

    
    human_friendly = permsdf[permsdf['label'] != 'null']

    hlabelsmap = human_friendly[human_friendly['permission'].isin(app_perms)]
    labelsmap = permsdf[permsdf['permission'].isin(app_perms)]
    print(hlabelsmap['permission'])
    print(hlabelsmap['label'])
    #print(len(human_friendly))
    #print(len(permsdf))

    #print(len(app_perms))
    #print(app_perms)

    print(set(app_perms) - set(hlabelsmap['permission'].tolist()))
    #print(human_friendly)
    #human_friendly_desc = permsdf[permsdf['description'] != 'null']

