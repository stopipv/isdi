#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
platform='unknown'
unamestr=`uname`
if [[ "$unamestr" == 'Linux' ]]; then
   platform='linux'
elif [[ "$unamestr" == 'Darwin' ]]; then
    platform='darwin'
elif [[ "$unamestr" == 'FreeBSD' ]]; then
   platform='freebsd'
fi

if [[ $platform == 'darwin' ]]; then
    for f in ${DIR}/../static_data/libimobiledevice-darwin/*idevice*
    do

      echo "Patching $f..."
      install_name_tool -change /usr/local/Cellar/libimobiledevice/HEAD-b34e343_3/lib/libimobiledevice.6.dylib @executable_path/libimobiledevice.6.dylib $f
      install_name_tool -change /usr/local/opt/usbmuxd/lib/libusbmuxd.4.dylib @executable_path/libusbmuxd.4.dylib $f

    done
      f=${DIR}/../static_data/libimobiledevice-darwin/ifuse
      echo "Patching $f..."
      install_name_tool -change /usr/local/Cellar/libimobiledevice/HEAD-b34e343_3/lib/libimobiledevice.6.dylib @executable_path/libimobiledevice.6.dylib $f
      install_name_tool -change /usr/local/opt/usbmuxd/lib/libusbmuxd.4.dylib @executable_path/libusbmuxd.4.dylib $f
elif [[ $platform == 'linux' ]]; then
  echo "Run this on a Mac (or figure out how to get equivalent of install_name_tool)"
fi



