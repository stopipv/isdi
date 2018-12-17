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
function hashing_exe {
    if [[ $(command -v md5) ]]; then
	echo "md5"
    elif [[ $(command -v md5sum) ]]; then 
	echo "md5sum"
    elif [[ $(command -v sha1sum) ]]; then
	echo "sha1sum"
    fi
}

mkdir -p pkgs/
"$adb" shell "mkdir -p /sdcard/apps/"
# pkg_version com.amazon.mShop.android.shopping
# exit 0;
function pull {
    echo "Clearing the folder"
    "$adb" pull "/sdcard/apps/" $PKG_DIR
    mv "$PKG_DIR"/apps/* "$PKG_DIR"
    "$adb" shell "rm -rf /sdcard/apps/"
    "$adb" shell "mkdir -p /sdcard/apps/"
}

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
    h=$("$adb" shell $(hashing_exe) $pkg_path | awk '{print $1}')
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
	pull
        t=0
    fi
done
pull

"$adb" shell "rm -rf /sdcard/apps/"
