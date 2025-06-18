#!/usr/bin/env bash
set -euo pipefail

# Pulls all third party apks that are not present in pkg folder 

BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
PKG_DIR="${BASE_DIR}/../dumps/pkgs"
mkdir -p "${PKG_DIR}"
serial_cmd="$1"
serial=${serial_cmd:3}
adb_cmd="${adb} ${serial_cmd}"
function pkg_version {
    _pkg="$1"
    # echo "$adb $serial shell dumpsys package $pkg | grep versionName | cut -d '=' -f 2"
    echo $(${adb_cmd} shell dumpsys package "${_pkg}" | grep versionName | cut -d '=' -f 2)
}

function hashing_exe {
    if [[ $(${adb_cmd} shell command -v md5) ]]; then
	echo "md5"
    elif [[ $(${adb_cmd} shell command -v md5sum) ]]; then 
	echo "md5sum"
    elif [[ $(${adb_cmd} shell command -v sha1sum) ]]; then
	echo "sha1sum"
    fi
}
echo $(hashing_exe)

${adb_cmd} shell "mkdir -p /sdcard/apps/"
# pkg_version com.amazon.mShop.android.shopping
# exit 0;

function pull {
    echo "Clearing the folder"
    ${adb_cmd} pull "/sdcard/apps/" $PKG_DIR
    if [[ -e "$PKG_DIR/apps/* " ]]; then
        mv "$PKG_DIR"/apps/* "$PKG_DIR"
    fi
    ${adb_cmd} shell "rm -rf /sdcard/apps/"
    ${adb_cmd} shell "mkdir -p /sdcard/apps/"
}

t=0
for i in $(${adb_cmd} shell pm list packages -3 -f | tr -d '\r'); 
do
    a=(${i//=/ })
    pkg_path=${a[0]//*:}
    echo "pkg_path = ${pkg_path}"
    pkg="$(echo ${a[1]} | tr -d '\r')"
    ignore=$(python $BASE_DIR/ignore.py "$pkg")
    if [[ "$ignore" == "1" ]]; then
        echo "Ignoring $pkg"
        continue
    fi
    h=$(${adb_cmd} shell $(hashing_exe) $pkg_path | awk '{print $1}')
    # version=$(pkg_version "${pkg}")
    # out_pkg_name="${pkg}__${version}__${h}.apk"
    out_pkg_name="${pkg}__${h}.apk"
    echo "sssss $pkg $out_pkg_name"
    if [[ ! -e "${PKG_DIR}/${pkg}__${h}.apk}" ]]; then 
	t=$((t+1))
        echo ${adb_cmd} shell "cp $pkg_path /sdcard/apps/${out_pkg_name}"
        ${adb_cmd} shell "cp $pkg_path /sdcard/apps/${out_pkg_name}"
    else
        echo "Already exists: ${out_pkg_name}"
    fi
    if [[ t -gt 10 ]]; then
	pull
        t=0
    fi
done
pull

${adb_cmd} shell "rm -rf /sdcard/apps/"
