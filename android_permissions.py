from rsonlite import simpleparse
from distutils.util import strtobool
from run import run_command, catch_err
import pandas as pd
import subprocess
import datetime
import config
import re

#MAP = config.ANDROID_PERMISSIONS
DUMPPKG = 'dumppkg'

def _parse_time(time_str):
    """
    Parse a time string e.g. (2h13m) into a timedelta object.
    Modified from virhilo's answer at https://stackoverflow.com/a/4628148/851699
    :param time_str: A string identifying a duration.  (eg. 2h13m)
    :return datetime.timedelta: A datetime.timedelta object
    """
    timedelta_re = re.compile(\
        r'^\+((?P<days>[\.\d]+?)d)?((?P<hours>[\.\d]+?)h)?((?P<minutes>[\.\d]+?)m)?((?P<seconds>[\.\d]+?)s)?((?P<milliseconds>[\.\d]+?)ms)?')
    parts = timedelta_re.match(time_str)
    assert parts is not None, "Could not parse any time information from '{}'."\
          "Examples of valid strings: '+8h', '+2d8h5m20s', '+2m4s'".format(time_str)
    time_params = {name: float(param) for name, param in parts.groupdict().items() if param}
    return datetime.timedelta(**time_params)

s = 'VIBRATE: allow; time=+29d3h41m32s800ms ago; duration=+1s13ms\nCAMERA: allow; time=+38d23h30m11s6ms ago; duration=+420ms\nRECORD_AUDIO: allow; time=+38d23h19m35s283ms ago; duration=+10s237ms\nWAKE_LOCK: allow; time=+16m12s788ms ago; duration=+10s67ms\nTOAST_WINDOW: allow; time=+38d23h22m57s645ms ago; duration=+4s2ms\nREAD_EXTERNAL_STORAGE: allow; time=+2h7m13s715ms ago\nWRITE_EXTERNAL_STORAGE: allow; time=+2h7m13s715ms ago\nRUN_IN_BACKGROUND: allow; time=+15m2s867ms ago'

def recent_permissions_used(appid):
    df = pd.DataFrame(columns=['appId','op','mode','timestamp','time_ago','duration'])
    cmd = '{cli} shell appops get {app}'
    recently_used = catch_err(run_command(cmd, app=appid))

    if 'No operations.' in recently_used:
        return df
    record = {'appId':appid}
    now = datetime.datetime.now()
    for permission in recently_used.split('\n')[:-1]:
        permission_attrs = permission.split(';')
        record['op'] = permission_attrs[0].split(':')[0]
        record['mode'] = permission_attrs[0].split(':')[1].strip()

        if len(permission_attrs) == 2:
            record['timestamp'] = now - _parse_time(permission_attrs[1].split('=')[1].strip())
            # TODO: keep time_ago? that leaks when the consultation was.
            record['time_ago'] = permission_attrs[1].split('=')[1].strip()
        else:
            record['timestamp'] = 'unknown (op)'
            record['time_ago'] = 'unknown (op)'
            record['duration'] = 'unknown (op)'
            df.loc[df.shape[0]] = record
            continue

        # NOTE: can convert this with timestamp + _parse_time('duration')
        if len(permission_attrs) == 3:
            record['duration'] = permission_attrs[2].split('=')[1].strip()
        else:
            record['duration'] = 'unspecified'
        df.loc[df.shape[0]] = record
    return df.sort_values(by=['time_ago']).reset_index(drop=True)

def package_info(appid):
    # FIXME: add check on all permissions, too.
    cmd = "{cli} shell dumpsys package {app} | sed -n -e '/Packages:/,$p'".format(cli='adb',app=appid)
    package_dump = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)\
            .stdout.read().decode('utf-8')#.strip()
    
    cmd = '{cli} shell dumpsys usagestats {app} | grep "App Standby States:" -A 1'\
            .format(cli='adb',app=appid)
    now = datetime.datetime.now()
    #usage_stats = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)\
    #        .stdout.read().decode('utf-8')#.strip()
    
    '''
     App Standby States:
        package=net.cybrook.trackview u=0 bucket=10 reason=u-mb used=+4m41s645ms usedScr=+2m19s198ms lastPred=+19d0h27m2s920ms activeLeft=+55m18s355ms wsLeft=-30d6h13m15s667ms lastJob=-24855d3h14m7s432ms idle=n
        
        totalElapsedTime=+305d6h7m59s376ms
        totalScreenOnTime=+67d8h56m19s585ms
    '''
    
    '''
    # switch to top method after tests
    package_dump = open(DUMPPKG, 'r').read()
    #print(package_dump)
    '''
    try:
        sp = simpleparse(package_dump)
    except AttributeError as e:
        print(package_dump)
        return []

    try:
        #print('THE PACKAGE IS:')
        #print(sp['Packages:'].items())
        # FIXME: TypeError: list indices must be integers or slices, not str
        # FIXME: don't rely on rsonlite to parse correctly? Seems to miss the Packages:.
        # for now, using sed to filter out potential hazards in parsing output.
        pkg = [v for k,v in sp['Packages:'].items() if appid in k][0]
    except IndexError as e:
        print(e)
        print('Didn\'t parse correctly. Not sure why.')
        exit(0)

    #print(pkg['install permissions:'])
    install_perms = [k.split(':')[0] for k,v in pkg['install permissions:'].items()]
    requested_perms = pkg['requested permissions:']

    #usage_stats = filter(None, usage_stats.split('\n')[1].split(' '))
    #usage_stats = dict(item.split('=') for item in usage_stats)
    #print(usage_stats)
    pkg_info = {}
    pkg_info['firstInstallTime'] = pkg['firstInstallTime']
    pkg_info['lastUpdateTime'] = pkg['lastUpdateTime']
    pkg_info['versionCode'] = pkg['versionCode']
    pkg_info['versionName'] = pkg['versionName']
    #pkg_info['used'] = now - _parse_time(usage_stats['used'])
    #pkg_info['usedScr'] = now - _parse_time(usage_stats['usedScr'])
    
    #('User 0:  installed', 'true hidden=false stopped=false notLaunched=false enabled=0\nlastDisabledCaller: com.android.vending\ngids=[3003]\nruntime permissions:')
    #inst_det_key = [v for k,v in pkg.items() if 'User 0:' in k][0]
    #install_details = dict(item.split('=') for item in inst_det_key.strip().split(' ')[1:])
    #install_details = {k:bool(strtobool(install_details[k])) for k in install_details}
    #print(install_details)

    

    all_perms = list(set(requested_perms) | set(install_perms))

    # need to get 
    # requested permissions:
    # install permissions:
    # runtime permissions:

    return all_perms, pkg_info
    
def gather_permissions_labels():
    # FIXME: would probably put in global db?
    cmd = '{cli} shell getprop ro.product.model'
    model = catch_err(run_command(cmd, outf=MAP)).strip().replace(' ','_')
    cmd = '{cli} shell pm list permissions -g -f > {outf}'
    #perms = catch_err(run_command(cmd, outf=model+'.permissions'))
    perms = catch_err(run_command(cmd, outf='static_data/android_permissions.txt'))

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

def all_permissions(appid):
    '''
        Returns a tuple of human-friendly permissions (including recently used), non human-friendly app ops,
        non human-friendly permissions, and summary stats.
    '''
    app_perms, pkg_info = package_info(appid)
    recent_permissions = recent_permissions_used(appid)

    permissions = pd.read_csv(config.ANDROID_PERMISSIONS)
    app_permissions_tbl = permissions[permissions['permission'].isin(app_perms)].reset_index(drop=True)

    app_permissions_tbl['permission_abbrv'] = app_permissions_tbl['permission']\
            .apply(lambda x: x.split('.')[-1])

    # TODO: really 'unknown'?
    hf_recent_permissions = pd.merge(recent_permissions, app_permissions_tbl, \
            left_on='op', right_on='permission_abbrv', how='right').fillna('unknown')

    no_hf_recent_permissions = recent_permissions[~recent_permissions['op'].isin(app_permissions_tbl['permission_abbrv'])]
    no_hf = set(app_perms) - set(app_permissions_tbl['permission'].tolist())

    stats = {'total_permissions':len(app_perms), 
            'hf_permissions':app_permissions_tbl.shape[0],
            'recent_permissions':recent_permissions.shape[0],
            'not_hf_ops':no_hf_recent_permissions.shape[0],
            'not_hf_permissions':len(no_hf)}
    return hf_recent_permissions, no_hf_recent_permissions, \
            no_hf, {**stats, **pkg_info}

if __name__ == '__main__':
    import sys
    appid = sys.argv[1]
    app_perms, pkg_info = package_info(appid)
    recent_permissions = recent_permissions_used(appid)

    #permissions = permissions_map()
    permissions = pd.read_csv(config.ANDROID_PERMISSIONS)
    app_permissions_tbl = permissions[permissions['permission'].isin(app_perms)].reset_index(drop=True)
    hf_app_permissions = list(zip(app_permissions_tbl.permission, app_permissions_tbl.label))

    # FIXME: delete 'null' labels from counting as human readable.
    print("'{}' uses {} app permissions:".format(appid, len(app_perms)))
    print('{} have human-readable names, and {} were recently used:'\
            .format(app_permissions_tbl.shape[0], recent_permissions.shape[0]))
    #for permission in hf_app_permissions:
    #    print(permission)

    app_permissions_tbl['permission_abbrv'] = app_permissions_tbl['permission']\
            .apply(lambda x: x.split('.')[-1])

    # TODO: really 'unknown'?
    hf_recent_permissions = pd.merge(recent_permissions, app_permissions_tbl, \
            left_on='op', right_on='permission_abbrv', how='right').fillna('unknown')
    #print(hf_recent_permissions.columns)
    #print(hf_recent_permissions.shape)
    #print(hf_recent_permissions.op == hf_recent_permissions.permission_abbrv)
    #print(hf_recent_permissions[['label','op','permission']])
    #print(hf_recent_permissions[['label','timestamp','time_ago','permission']])
    
    #print(hf_recent_permissions[['label','description','timestamp','time_ago', 'duration']])
    print(hf_recent_permissions[['label','permission_abbrv','timestamp']])

    no_hf_recent_permissions = recent_permissions[~recent_permissions['op'].isin(app_permissions_tbl['permission_abbrv'])]
    print("\nCouldn't find human-friendly descriptions for {} recently used app operations:"\
            .format(no_hf_recent_permissions.shape[0]))

    print(no_hf_recent_permissions[['op','timestamp','time_ago','duration']])

    no_hf = set(app_perms) - set(app_permissions_tbl['permission'].tolist())
    print("\nCouldn't find human-friendly descriptions for {} app permissions:".format(len(no_hf)))
    for x in no_hf:
        hf = x.split('.')[-1]
        hf = hf[:1] + hf[1:].lower().replace('_',' ')
        print("\t"+str(x)+" ("+str(hf)+")")
