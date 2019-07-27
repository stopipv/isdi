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
    for f in "${DIR}"/../static_data/libimobiledevice-darwin/*
    do
      echo "Patching $f..."
      install_name_tool -change /usr/local/Cellar/libimobiledevice/HEAD-b34e343_3/lib/libimobiledevice.6.dylib @executable_path/libimobiledevice.6.dylib "$f"
      install_name_tool -change /usr/local/opt/libimobiledevice/lib/libimobiledevice.6.dylib @executable_path/libimobiledevice.6.dylib "$f"
      install_name_tool -change /usr/local/opt/usbmuxd/lib/libusbmuxd.4.dylib @executable_path/libusbmuxd.4.dylib "$f"
      install_name_tool -change /usr/local/opt/usbmuxd/lib/libusbmuxd.4.dylib @executable_path/libusbmuxd.4.dylib "$f"
      install_name_tool -change /usr/local/opt/libplist/lib/libplist.3.dylib @executable_path/libplist.3.dylib "$f"
      install_name_tool -change /usr/local/opt/libzip/lib/libzip.5.dylib @executable_path/libzip.5.dylib "$f"
      install_name_tool -change /usr/local/lib/libosxfuse.2.dylib @executable_path/libosxfuse.2.dylib "$f"
      install_name_tool -change /usr/local/opt/libplist/lib/libplist++.3.dylib @executable_path/libplist++.3.dylib "$f"
      install_name_tool -change /usr/local/Cellar/libplist/2.0.0_1/lib/libplist.3.dylib @executable_path/libplist.3.dylib "$f"
      install_name_tool -change /usr/local/opt/libusb/lib/libusb-1.0.0.dylib @executable_path/libusb-1.0.0.dylib "$f"
      install_name_tool -change /usr/local/opt/libzip/lib/libzip.5.dylib @executable_path/libzip.5.dylib "$f"
    done
elif [[ $platform == 'linux' ]]; then
  echo "Run this on a Mac (or figure out how to get equivalent of install_name_tool)"
  echo "Consider patchelf: https://nixos.org/patchelf.html (source at https://github.com/NixOS/patchelf)"
fi
