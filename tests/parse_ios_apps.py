#!/usr/bin/env python3
from plistlib import readPlist
from functools import reduce
import operator
import json

path = "serial/"
# load permissions mappings and apps plist
with open("ios_permissions.json", "r") as fh:
    PERMISSIONS_MAP = json.load(fh)
with open("ios_device_identifiers.json", "r") as fh:
    MODEL_MAKE_MAP = json.load(fh)
with open(path + "ios_jailbroken.log", "r") as fh:
    JAILBROKEN_LOG = fh.readlines()
APPS_PLIST = readPlist(path + "ios_apps.plist")
DEVICE_INFO = readPlist(path + "ios_info.xml")


def _retrieve(dict_, nest):
    """
    Navigates dictionaries like dict_[nest0][nest1][nest2]...
    gracefully.
    """
    try:
        return reduce(operator.getitem, nest, dict_)
    except KeyError as e:
        return ""


def _check_unseen_permissions(permissions):
    for permission in permissions:
        if permission not in PERMISSIONS_MAP:
            print(
                "Have not seen " + str(permission) + " before. Making note of this..."
            )
            permission_human_readable = permission.replace("kTCCService", "")
            with open("ios_permissions.json", "w") as fh:
                PERMISSIONS_MAP[permission] = permission_human_readable
                fh.write(json.dumps(PERMISSIONS_MAP))
            print("Noted.")
        # print('\t'+msg+": "+str(PERMISSIONS_MAP[permission])+"\tReason: "+app.get(permission,'system app'))


def get_permissions(app):
    """
    Returns a list of tuples (permission, developer-provided reason for permission).
    Could modify this function to include whether or not the permission can be adjusted
    in Settings.
    """
    system_permissions = _retrieve(app, ["Entitlements", "com.apple.private.tcc.allow"])
    adjustable_system_permissions = _retrieve(
        app, ["Entitlements", "com.apple.private.tcc.allow.overridable"]
    )
    third_party_permissions = list(set(app) & set(PERMISSIONS_MAP))
    _check_unseen_permissions(
        list(system_permissions) + list(adjustable_system_permissions)
    )

    # (permission used, developer reason for requesting the permission)
    all_permissions = list(
        set(
            map(
                lambda x: (
                    PERMISSIONS_MAP[x],
                    app.get(x, "permission granted by system"),
                ),
                list(
                    set(system_permissions)
                    | set(adjustable_system_permissions)
                    | set(third_party_permissions)
                ),
            )
        )
    )
    pii = _retrieve(
        app, ["Entitlements", "com.apple.private.MobileGestalt.AllowedProtectedKeys"]
    )
    # print("\tPII: "+str(pii))

    return all_permissions


# Get dumps by running ios_scan.sh first.
def parse_dump():
    dotapps = []
    perms_c = 0
    for app in APPS_PLIST:
        dotapps.append(app["Path"].split("/")[-1])
        party = app["ApplicationType"].lower()
        if party in ["system", "user"]:
            print(
                app["CFBundleName"],
                "("
                + app["CFBundleIdentifier"]
                + ") is a {} app and has permissions:".format(party),
            )

            permissions = get_permissions(app)
            for permission in permissions:
                perms_c += 1
                print("\t" + str(permission[0]) + "\tReason: " + permission[1])
            print("")

    # determine make and version
    try:
        make = MODEL_MAKE_MAP[DEVICE_INFO["ProductType"]]
    except KeyError as e:
        make = (
            DEVICE_INFO["DeviceClass"]
            + " (Model "
            + DEVICE_INFO["ModelNumber"]
            + DEVICE_INFO["RegionInfo"]
            + ")"
        )
    print(
        "Your device, an "
        + make
        + ", is running version "
        + DEVICE_INFO["ProductVersion"]
    )

    """ Summary of jailbroken detection: checks for commonly installed jailbreak apps, 
        tries to mount root filesystem (AFC2, by default on iOS 7 and lower,
        tries to SSH into the phone (FIXME). iproxy 2222 22 `idevice_id -l` says
        "waiting for connection" perpertually if not work. says "accepted connection" on next line if it does.
        https://twitter.com/bellis1000/status/807527492810665984?lang=en
    """
    # add to jailbroken log
    # FIXME: load from private data blacklist. More to be added.
    for app in [
        "Cydia.app",
        "blackra1n.app",
        "FakeCarrier.app",
        "Icy.app",
        "IntelliScreen.app",
        "MxTube.app",
        "RockApp.app",
        "SBSettings.app",
        "WinterBoard.app",
    ]:
        if app in dotapps:
            with open(JAILBROKEN_LOG, "a") as fh:
                fh.write("{} was found on the device.\n".format(app))

    # check for jailbroken status
    if (
        "Your device needs to be jailbroken and have the AFC2 service installed.\n"
        in JAILBROKEN_LOG
    ):
        print("Filesystem not rooted. Highly unlikely to be jailbroken.")
    else:
        print("Filesystem has been rooted. This device is jailbroken.")
    print(perms_c)


if __name__ == "__main__":
    # Get dumps by running ios_scan.sh first.
    parse_dump()
