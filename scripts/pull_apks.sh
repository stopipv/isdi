#!/usr/bin/env bash
# Pulls all third party apks that are not present in pkg folder 

BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
PKG_DIR="${BASE_DIR}/../pkgs"
mkdir -p "${PKG_DIR}"

function pkg_version {
    pkg=$1
    echo $(adb shell dumpsys package "$pkg" | grep versionName | cut -d '=' -f 2)
}

mkdir -p pkgs/
adb shell "mkdir -p /sdcard/apps/"

for i in $(adb shell pm list packages -3 -f); 
do 
    a=(${i//=/ })
    pkg_path=${a[0]//*:}
    echo "pkg_path = ${pkg_path}"
    pkg=${a[1]}
    out_pkg_name="$pkg-$(pkg_version $pkg).apk"
    echo $out_pkg_name
    if [[ ! -e "${PKG_DIR}/${pkg_version_name}" ]]; then 
        adb shell "cp $pkg_path /sdcard/apps/${out_pkg_name}"
    fi
done
adb pull "/sdcard/apps/" .
adb shell "rm -rf /sdcard/apps/"
