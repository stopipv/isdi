#!/usr/bin/env bash
# Pulls all third party apks that are not present in pkg folder

BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
PKG_DIR="${BASE_DIR}/../dumps/pkgs"
mkdir -p "${PKG_DIR}"
serial_cmd="$1"
adb_cmd="${adb} ${serial_cmd}"
echo "ADB command: ${adb_cmd}"
function pkg_version {
    _pkg="$1"
    # echo "$adb $serial shell dumpsys package $pkg | grep versionName | cut -d '=' -f 2"
    echo $(${adb_cmd} shell dumpsys package "${_pkg}" | grep versionName | cut -d '=' -f 2 | tr -d '\r')
}

hashing_exe=$(${adb_cmd} shell "command -v md5 || command -v md5sum || command -v sha1sum" | tr -d '\r')
echo "Hashing exec found: ${hashing_exe}"

${adb_cmd} shell "mkdir -p /sdcard/apps/"
# pkg_version com.amazon.mShop.android.shopping
# exit 0;
whitelist_patterns=(
    "com.google.*"
    "com.whatsap.*"
    "com.android.*"
    "com.samsung.*"
    "com.sec.*"
)

check_apk() {
    local apk="$1"
    for pattern in "${whitelist_patterns[@]}"; do
        if [[ "$apk" =~ $pattern ]]; then
            return 0  # matched
        fi
    done
    return 1  # no match
}

function pull {
    echo "Clearing the folder"
    ${adb_cmd} pull "/sdcard/apps/" $PKG_DIR
    mv "$PKG_DIR"/apps/* "$PKG_DIR"
    ${adb_cmd} shell "rm -rf /sdcard/apps/"
    ${adb_cmd} shell "mkdir -p /sdcard/apps/"
}

t=0
for i in $(${adb_cmd} shell pm list packages -3 -f | tr -d '\r');
do
    echo "------------------"
    read -ra a <<< "$(echo $i | sed -n 's/^package:\(.*\.apk\)=\(.*\)/\1 \2/p') | tr -d '\r')"
    pkg_path=${a[0]}
    pkg=${a[1]}
    echo "[INFO] pkg_path = ${pkg_path} apk_name = ${pkg}"
    if check_apk "$pkg"; then
        echo "~> Ignoring $pkg"
        continue
    fi
    h=$(${adb_cmd} shell ${hashing_exe} ${pkg_path} | awk '{print substr($1, 1, 6)}' | tr -d '\r')
    echo "[INFO] Hash: $h"
    if [[ -z "$h" ]]; then
        echo "Error: Hashing failed for $pkg_path"
        exit 1
    fi
    version=$(pkg_version "${pkg}")1
    out_pkg_name="${pkg%.apk}__${version}__${h}.apk"
    echo "[INFO] $pkg --> $out_pkg_name"
    if [[ ! -e "${PKG_DIR}/${out_pkg_name}" ]]; then
	    t=$((t+1))
        echo "Copying $pkg_path"
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
