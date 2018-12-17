#!/usr/bin/env bash
# Pulls all third party apks that are not present in pkg folder 

BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
PKG_DIR="${BASE_DIR}/../dumps/pkgs"
mkdir -p "${PKG_DIR}"
serial="$1"

function pkg_version {
    _pkg="$1"
    # echo "$adb $serial shell dumpsys package $pkg | grep versionName | cut -d '=' -f 2"
    echo $("$adb" $serial shell dumpsys package "${_pkg}" | grep versionName | cut -d '=' -f 2)
}

mkdir -p pkgs/
"$adb" shell "mkdir -p /sdcard/apps/"
# pkg_version com.amazon.mShop.android.shopping
# exit 0;
t=0
for i in $("$adb" shell pm list packages -3 -f | tr -d '\r'); 
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
    h=$("$adb" shell sha1sum $pkg_path | awk '{print $1}')
    # version=$(pkg_version "${pkg}")
    # out_pkg_name="${pkg}__${version}__${h}.apk"
    out_pkg_name="${pkg}__${h}.apk"
    echo "sssss $pkg $out_pkg_name"
    if [[ ! -e "${PKG_DIR}/${out_pkg_name}" ]]; then 
	t=$((t+1))
        echo "$adb" shell "cp $pkg_path /sdcard/apps/${out_pkg_name}"
        "$adb" shell "cp $pkg_path /sdcard/apps/${out_pkg_name}"
    else
        echo "Already exists: ${out_pkg_name}"
    fi
    if [[ t -gt 10 ]]; then
        echo "Clearing the folder"
        "$adb" pull "/sdcard/apps/" $PKG_DIR
        mv "$PKG_DIR"/apps/* "$PKG_DIR"
        "$adb" shell "rm -rf /sdcard/apps/"
        "$adb" shell "mkdir -p /sdcard/apps/"
        t=0
    fi
done

"$adb" shell "rm -rf /sdcard/apps/"
