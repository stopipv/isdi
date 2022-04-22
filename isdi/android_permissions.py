"""
Must work completely from the dumps, no interaction with the device is required.
"""

from rsonlite import simpleparse
from runcmd import run_command, catch_err
import pandas as pd
import datetime
import isdi.config
import re
import json

#MAP = config.ANDROID_PERMISSIONS
DUMPPKG = 'dumppkg'


def _parse_time(time_str):
    """
    Parse a time string e.g. (2h13m) into a timedelta object.
    Modified from virhilo's answer at https://stackoverflow.com/a/4628148/851699
    :param time_str: A string identifying a duration.  (eg. 2h13m)
    :return datetime.timedelta: A datetime.timedelta object
        r'^\+((?P<days>[\.\d]+?)d)?((?P<hours>[\.\d]+?)h)?((?P<minutes>[\.\d]+?)m)?((?P<seconds>[\.\d]+?)s)?((?P<milliseconds>[\.\d]+?)ms)?')
    """
    timedelta_re = re.compile(
        r'^.((?P<days>[\.\d]+?)d)?((?P<hours>[\.\d]+?)h)?((?P<minutes>[\.\d]+?)m)?((?P<seconds>[\.\d]+?)s)?((?P<milliseconds>[\.\d]+?)ms)?')
    parts = timedelta_re.match(time_str)
    assert parts is not None, "Could not parse any time information from '{}'."\
        "Examples of valid strings: '+8h', '+2d8h5m20s', '+2m4s'".format(time_str)
    time_params = {name: float(param) for name,
                   param in parts.groupdict().items() if param}
    return datetime.timedelta(**time_params)


s = \
"""VIBRATE: allow; time=+29d3h41m32s800ms ago; duration=+1s13ms
CAMERA: allow; time=+38d23h30m11s6ms ago; duration=+420ms
RECORD_AUDIO: allow; time=+38d23h19m35s283ms ago; duration=+10s237ms
WAKE_LOCK: allow; time=+16m12s788ms ago; duration=+10s67ms
TOAST_WINDOW: allow; time=+38d23h22m57s645ms ago; duration=+4s2ms
READ_EXTERNAL_STORAGE: allow; time=+2h7m13s715ms ago
WRITE_EXTERNAL_STORAGE: allow; time=+2h7m13s715ms ago
RUN_IN_BACKGROUND: allow; time=+15m2s867ms ago"""


def recent_permissions_used(appid):
    cols = ['appId', 'op', 'mode', 'timestamp', 'time_ago', 'duration']
    df = pd.DataFrame([], columns=cols)
    cmd = '{cli} shell appops get {app}'
    recently_used = catch_err(run_command(cmd, app=appid))

    if 'No operations.' in recently_used:
        return df

    record = {'appId': appid}
    now = datetime.datetime.now()
    print(recently_used)
    for permission in recently_used.split('\n')[:-1]:
        permission_attrs = permission.split(';')
        t = permission_attrs[0].split(':')
        if len(t) != 2:    # Could not parse
            continue
        record = {c: '' for c in cols}
        record['op'] = t[0].strip()
        record['mode'] = t[1].strip()
        if len(permission_attrs) == 2:
            tt = permission_attrs[1].split('=')
            if len(tt) != 2:
                continue
            record['timestamp'] = (now - _parse_time(tt[1].strip()))\
                .strftime(config.DATE_STR)
            # TODO: keep time_ago? that leaks when the consultation was.
            record['time_ago'] = tt[1].strip()

        if len(permission_attrs) == 3:
            tt = permission_attrs[2].split('=')
            if len(tt) == 2:
                record['duration'] = tt[1].strip()

        df.loc[df.shape[0]] = record
    return df.sort_values(by=['time_ago']).reset_index(drop=True)


def package_info(dumpf, appid):
    # FIXME: add check on all permissions, too.
    # need to get
    # requested permissions:
    # install permissions:
    # runtime permissions:
    cmd = "sed -n -e '/Package \[{appid}\]/,/Package \[/p' '{dumpf}'"\
        .format(appid=appid, dumpf=dumpf.replace('.json', '.txt'))
    print(cmd)
    # TODO: Need to udpate it once the catch_err function is fixed.
    package_dump = run_command(cmd).stdout.read().decode()

    # cmd = '{cli} shell dumpsys usagestats {app} | grep "App Standby States:" -A 1'\
    #     .format(cli=config.ADB_PATH, app=appid)
    # now = datetime.datetime.now()
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
        # FIXME: TypeError: list indices must be integers or slices, not str
        # FIXME: don't rely on rsonlite to parse correctly? Seems to miss the
        # Packages:.  for now, using sed to filter out potential hazards in
        # parsing output.
        if isinstance(sp, list) and len(sp) > 1:
            sp = sp[0]
        _, pkg = sp.popitem()
        if isinstance(pkg, list):
            pkg = pkg[0]
    except (IndexError, AttributeError) as e:
        print(e)
        print(f"Didn't parse correctly. Not sure why.\nsp={sp}")
        return [], {}
    # print("pkg={}".format(json.dumps(pkg, indent=2)))
    install_perms = [k.split(':')[0] for k, v in
                     pkg.get('install permissions:', {}).items()]
    requested_perms = pkg.get('requested permissions:', [])

    #usage_stats = filter(None, usage_stats.split('\n')[1].split(' '))
    #usage_stats = dict(item.split('=') for item in usage_stats)
    # print(usage_stats)
    pkg_info = {}
    pkg_info['firstInstallTime'] = pkg.get('firstInstallTime', '')
    pkg_info['lastUpdateTime'] = pkg.get('lastUpdateTime', '')
    pkg_info['versionCode'] = pkg.get('versionCode', '')
    pkg_info['versionName'] = pkg.get('versionName', '')
    #pkg_info['used'] = now - _parse_time(usage_stats['used'])
    #pkg_info['usedScr'] = now - _parse_time(usage_stats['usedScr'])

    #('User 0:  installed', 'true hidden=false stopped=false notLaunched=false enabled=0\nlastDisabledCaller: com.android.vending\ngids=[3003]\nruntime permissions:')
    #inst_det_key = [v for k,v in pkg.items() if 'User 0:' in k][0]
    #install_details = dict(item.split('=') for item in inst_det_key.strip().split(' ')[1:])
    #install_details = {k:bool(strtobool(install_details[k])) for k in install_details}
    # print(install_details)

    all_perms = list(set(requested_perms) | set(install_perms))

    return all_perms, pkg_info


def gather_permissions_labels():
    # FIXME: would probably put in global db?
    cmd = '{cli} shell getprop ro.product.model'
    model = catch_err(run_command(cmd, outf=MAP)).strip().replace(' ', '_')
    cmd = '{cli} shell pm list permissions -g -f > {outf}'
    #perms = catch_err(run_command(cmd, outf=model+'.permissions'))
    perms = catch_err(
        run_command(
            cmd,
            outf='static_data/android_permissions.txt')
    )


def permissions_map():
    groupcols = ['group', 'group_package', 'group_label', 'group_description']
    pcols = [
        'permission',
        'package',
        'label',
        'description',
        'protectionLevel']
    sp = simpleparse(open('Pixel2.permissions', 'r').read())
    df = pd.DataFrame(columns=groupcols + pcols)
    record = {}
    ungrouped_d = dict.fromkeys(groupcols, 'ungrouped')
    for group in sp[1]:
        record['group'] = group.split(':')[1]
        if record['group'] == '':
            for permission in sp[1][group]:
                record['permission'] = permission.split(':')[1]
                for permission_attr in sp[1][group][permission]:
                    label, val = permission_attr.split(':')
                    record[label.replace('+ ', '')] = val
                df.loc[df.shape[0]] = {**record, **ungrouped_d}
        else:
            for group_attr in sp[1][group]:
                if isinstance(group_attr, str):
                    label, val = group_attr.split(':')
                    record['group_' + label.replace('+ ', '')] = val
                else:
                    for permission in group_attr:
                        record['permission'] = permission.split(':')[1]
                        for permission_attr in group_attr[permission]:
                            label, val = permission_attr.split(':')
                            record[label.replace('+ ', '')] = val
                        df.loc[df.shape[0]] = record
    df.to_csv('static_data/android_permissions.csv')
    return df


def all_permissions(dumpf, appid):
    '''
        Returns a tuple of human-friendly permissions (including recently used), non human-friendly app ops,
        non human-friendly permissions, and summary stats.
    '''
    app_perms, pkg_info = package_info(dumpf, appid)
    # print("--->>> all_permissions\n", app_perms)
    recent_permissions = recent_permissions_used(appid)

    permissions = pd.read_csv(config.ANDROID_PERMISSIONS_CSV)
    permissions['label'] = permissions.apply(
        lambda x: (x['permission'].rsplit('.', 1)[-1] if x['label'] == 'null'
                   else x['label']),
        axis=1
    )
    app_permissions_tbl = permissions[permissions['permission'].isin(
        app_perms)].reset_index(drop=True)
    app_permissions_tbl['permission_abbrv'] = app_permissions_tbl\
        .permission.str.rsplit('.', 1).str[-1]

    # TODO: really 'unknown'?
    hf_recent_permissions = pd.merge(
        recent_permissions, app_permissions_tbl,
        left_on='op', right_on='permission_abbrv',
        how='right').fillna('Unknown permission')

    no_hf_recent_permissions = recent_permissions[
        ~recent_permissions['op'].isin(app_permissions_tbl['permission_abbrv'])
    ]
    no_hf = set(app_perms) - set(app_permissions_tbl['permission'].tolist())

    stats = {'total_permissions': len(app_perms),
             'hf_permissions': app_permissions_tbl.shape[0],
             'recent_permissions': recent_permissions.shape[0],
             'not_hf_ops': no_hf_recent_permissions.shape[0],
             'not_hf_permissions': len(no_hf)}
    return hf_recent_permissions, no_hf_recent_permissions, \
        no_hf, {**stats, **pkg_info}


if __name__ == '__main__':
    import sys

    print(package_info('./phone_dumps/83c6500a47585595f72d654829cab29edd2c4f5253e6c05d5576cf04661fd6eb_android.txt', 'net.cybrook.trackview'))
    exit()

    appid = sys.argv[1]
    app_perms, pkg_info = package_info(appid)

    print(app_perms, pkg_info)
    exit()
    recent_permissions = recent_permissions_used(appid)

    # permissions = permissions_map()
    permissions = pd.read_csv(config.ANDROID_PERMISSIONS)
    app_permissions_tbl = permissions[permissions['permission'].isin(
        app_perms)].reset_index(drop=True)
    hf_app_permissions = list(
        zip(app_permissions_tbl.permission, app_permissions_tbl.label))

    # FIXME: delete 'null' labels from counting as human readable.
    print("'{}' uses {} app permissions:".format(appid, len(app_perms)))
    print('{} have human-readable names, and {} were recently used:'
          .format(app_permissions_tbl.shape[0], recent_permissions.shape[0]))
    # for permission in hf_app_permissions:
    #    print(permission)

    app_permissions_tbl['permission_abbrv'] = app_permissions_tbl['permission']\
        .apply(lambda x: x.rsplit('.', 1)[-1])

    # TODO: really 'unknown'?
    hf_recent_permissions = pd.merge(
        recent_permissions,
        app_permissions_tbl,
        left_on='op',
        right_on='permission_abbrv',
        how='right').fillna('unknown')
    # print(hf_recent_permissions.columns)
    # print(hf_recent_permissions.shape)
    #print(hf_recent_permissions.op == hf_recent_permissions.permission_abbrv)
    # print(hf_recent_permissions[['label','op','permission']])
    # print(hf_recent_permissions[['label','timestamp','time_ago','permission']])

    #print(hf_recent_permissions[['label','description','timestamp','time_ago', 'duration']])
    print(hf_recent_permissions[['label', 'permission_abbrv', 'timestamp']])

    no_hf_recent_permissions = recent_permissions[~recent_permissions['op'].isin(
        app_permissions_tbl['permission_abbrv'])]
    print("\nCouldn't find human-friendly descriptions for {} recently used app operations:"
          .format(no_hf_recent_permissions.shape[0]))

    print(no_hf_recent_permissions[[
          'op', 'timestamp', 'time_ago', 'duration']])

    no_hf = set(app_perms) - set(app_permissions_tbl['permission'].tolist())
    print("\nCouldn't find human-friendly descriptions for {} app permissions:".format(len(no_hf)))
    for x in no_hf:
        hf = x.split('.')[-1]
        hf = hf[:1] + hf[1:].lower().replace('_', ' ')
        print("\t" + str(x) + " (" + str(hf) + ")")

