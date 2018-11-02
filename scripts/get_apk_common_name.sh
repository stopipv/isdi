#!/usr/bin/env bash
function android_pull_apk() {
    if [ -z "$1" ]; then
        echo "You must pass a package to this function!"
        echo "Ex.: android_pull_apk \"com.android.contacts\""
        return 1
    fi

    if [ -z "$(adb shell pm list packages | grep $1)" ]; then
        echo "You are typed a invalid package!"
        return 1
    fi

    apk_path="`adb shell pm path $1 | sed -e 's/package://g' | tr '\n' ' ' | tr -d '[:space:]'`"
    apk_name="`adb shell basename ${apk_path} | tr '\n' ' ' | tr -d '[:space:]'`"

    #destination="$HOME/Documents/Android/APKs"
    #mkdir -p "$destination"
    adb pull ${apk_path} .
    mv base.apk $1.apk
}

#android_pull_apk $1
#aapt d badging $1.apk | grep 'application: label' | sed -n "s/.*label\='\([^']*\)'.*/\1/p"
#rm $1.apk

adb push aapt-x86 /data/local/tmp
for pkg in `adb shell pm list packages -f | awk -F= '{sub("package:","");print $1}'`
do
  adb shell "/data/local/tmp/aapt-x86 d badging $pkg" | grep 'application: label' | sed -n "s/.*label\='\([^']*\)'.*/\1/p"
  #aapt d badging $pkg | awk -F: '
  #    $1 == "application-label" {print $2}'
done
adb shell rm /data/local/tmp/aapt-x86

function android_get_apk_name() {
  for pkg in `adb shell pm list packages -f | awk -F= '{sub("package:","");print $1}'`
  do
    adb pull ${pkg} apk.apk
    aapt d badging apk.apk | grep 'application: label' | sed -n "s/.*label\='\([^']*\)'.*/\1/p"
    #aapt d badging $pkg | awk -F: '
    #    $1 == "application-label" {print $2}'
    rm apk.apk
  done
}

# https://github.com/Calsign/APDE/tree/master/APDE/src/main/assets/aapt-binaries
