#!/usr/bin/env python3
from plistlib import readPlist
from functools import reduce
import operator
import json

# load permissions mappings and apps plist
with open('ios_permissions.json', 'r') as fh:
    PERMISSIONS_MAP = json.load(fh)
APPS_PLIST = readPlist('iphone_plist.plist')

def _retrieve(dict_, nest):
    '''
        Navigates dictionaries like dict_[nest0][nest1][nest2]...
        gracefully.
    '''
    try:
        return reduce(operator.getitem, nest, dict_)
    except KeyError as e:
        return ""

def _check_unseen_permissions(permissions):
    for permission in permissions:
        if permission not in PERMISSIONS_MAP:
            print('Have not seen '+str(permission)+' before. Making note of this...')
            permission_human_readable = permission.replace('kTCCService','')
            with open('ios_permissions.json', 'w') as fh:
                PERMISSIONS_MAP[permission] = permission_human_readable
                fh.write(json.dumps(PERMISSIONS_MAP))
            print('Noted.')
        #print('\t'+msg+": "+str(PERMISSIONS_MAP[permission])+"\tReason: "+app.get(permission,'system app'))

def get_permissions(app):
    '''
        Returns a list of tuples (permission, developer-provided reason for permission).
        Could modify this function to include whether or not the permission can be adjusted
        in Settings.
    '''
    system_permissions = _retrieve(app, ['Entitlements','com.apple.private.tcc.allow'])
    adjustable_system_permissions =  _retrieve(app, ['Entitlements','com.apple.private.tcc.allow.overridable'])
    third_party_permissions = list(set(app) & set(PERMISSIONS_MAP))
    _check_unseen_permissions(list(system_permissions)+list(adjustable_system_permissions))
    
    # (permission used, developer reason for requesting the permission)
    all_permissions = list(set(map(lambda x: \
            (PERMISSIONS_MAP[x], app.get(x, "permission granted by system")),\
            list(set(system_permissions) | \
            set(adjustable_system_permissions) | set(third_party_permissions)))))
    pii = _retrieve(app, ['Entitlements','com.apple.private.MobileGestalt.AllowedProtectedKeys'])
    #print("\tPII: "+str(pii))

    return all_permissions

def parse_dump():
    # get plist dump from ios_dump.sh
    for app in APPS_PLIST:
        party = app["ApplicationType"].lower()
        if party in ['system','user']:
            print(app['CFBundleName'],"("+app['CFBundleIdentifier']+") is a {} app and has permissions:"\
                    .format(party))

            permissions = get_permissions(app)
            for permission in permissions:
                print("\t"+str(permission[0])+"\tReason: "+permission[1])
            print("")

if __name__ == "__main__":
    parse_dump()
