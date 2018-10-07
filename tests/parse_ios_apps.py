#!/usr/bin/env python3
import json
import plistlib
from functools import reduce
import operator

# load permissions mappings, apps plist
with open('ios_permissions.json', 'r') as fh:
    PERMISSIONS_MAP = json.load(fh)
APPS_PLIST = plistlib.readPlist('iphone_plist.xml')


def _retrieve(dict_, nest):
    '''
        Navigates dictionaries like dict_[nest0][nest1][nest2]...
    '''
    try:
        return reduce(operator.getitem, nest, dict_)
    except KeyError as e:
        return ""

def permissions():
    # get xml dump from ios_dump.sh
    for app in APPS_PLIST:
        party = app["ApplicationType"].lower()
        if party in ['system','user']:
            print(app['CFBundleName'],"("+app['CFBundleIdentifier']+") is a {} app and has permissions:"\
                    .format(party))

            permissions = _retrieve(app, ['Entitlements','com.apple.private.tcc.allow'])
            adjustable_permissions =  _retrieve(app, ['Entitlements','com.apple.private.tcc.allow.overridable'])
            c = _retrieve(app, ['Entitlements','com.apple.private.MobileGestalt.AllowedProtectedKeys'])

            def _print_permissions(permissions, msg):
                for permission in permissions:
                    if permission not in PERMISSIONS_MAP:
                        # add newly-discovered permission
                        with open('ios_permissions.json', 'w') as fh:
                            PERMISSIONS_MAP[permission] = permission[11:]
                            fh.write(json.dumps(PERMISSIONS_MAP))
                        permission = permission[11:]
                    else:
                        print("\t{}: ".format(msg)+str(PERMISSIONS_MAP[permission]))

            _print_permissions(permissions, "Built-in")
            _print_permissions(adjustable_permissions, "Adjustable from settings")

            if c:
                print("\tPII: "+str(c))
        print("")

if __name__ == "__main__":
    permissions()
