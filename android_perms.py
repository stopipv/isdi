from rsonlite import simpleparse
from run import run_command, catch_err
import pandas as pd
from itertools import zip_longest
MAP = 'Pixel2.permissions'
DUMPPKG = 'dumppkg'

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
    df.to_csv('static_data/android_permissions.csv')
    return df

if __name__ == '__main__':
    appid = 'net.cybrook.trackview'
    app_perms = permissions_used(appid)
    permsdf = permissions_map()
    labelsmap = permsdf[permsdf['permission'].isin(app_perms)]
    
    hf_permissions = list(zip(labelsmap.permission, labelsmap.label))

    # FIXME: delete 'null' labels from counting as human readable.
    print("'{}' uses {} app permissions:".format(appid, len(app_perms)))
    print('{} have human readable names:'.format(len(hf_permissions)))
    for permission in hf_permissions:
        print(permission)

    no_hf = set(app_perms) - set(labelsmap['permission'].tolist())
    print("Couldn't find human readable names for {} app permissions:".format(len(no_hf)))
    for x in no_hf:
        print(x)
