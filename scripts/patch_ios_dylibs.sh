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
    echo "Check the dylibs via otool -L <file> and add the rules here."
    dylibs=(
      /usr/local/Cellar/libimobiledevice/HEAD-b34e343_3/lib/libimobiledevice.6.dylib
      /usr/local/opt/libimobiledevice/lib/libimobiledevice.6.dylib 
      /usr/local/opt/usbmuxd/lib/libusbmuxd.4.dylib 
      /usr/local/opt/usbmuxd/lib/libusbmuxd.4.dylib 
      /usr/local/opt/libplist/lib/libplist.3.dylib 
      /usr/local/opt/libzip/lib/libzip.5.dylib 
      /usr/local/lib/libosxfuse.2.dylib 
      /usr/local/opt/libplist/lib/libplist++.3.dylib 
      /usr/local/Cellar/libplist/2.0.0_1/lib/libplist.3.dylib 
      /usr/local/opt/libusb/lib/libusb-1.0.0.dylib 
      /usr/local/opt/libzip/lib/libzip.5.dylib 
    )

    for f in "${DIR}"/../static_data/libimobiledevice-darwin/*; do
      echo "Patching $f..."
      for i in "${dylibs[@]}"; do
        install_name_tool -change $i @executable_path/${i##*/} "$f"
      done
    done

elif [[ $platform == 'linux' ]]; then
  for f in "${DIR}"/../static_data/libimobiledevice-linux/*; do
    echo "Patching $f..."
    patchelf --set-rpath '$ORIGIN':/usr/lib:/lib:/usr/local/lib "$f" > /dev/null 2>&1
  done
fi
