#!/bin/bash

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

echo "Check the dylibs via otool -L <file> and add the rules here."
if [[ $platform == 'darwin' ]]; then
    for f in "${DIR}"/../static_data/libimobiledevice-darwin/*
    do
    echo "Patching $f..."
	for i in "${dylibs[@]}"; do
	    install_name_tool -change $i @executable_path/${i##*/} "$f"
	done
    done
elif [[ $platform == 'linux' ]]; then
  echo "Run this on a Mac (or figure out how to get equivalent of install_name_tool)"
  echo "Consider patchelf: https://nixos.org/patchelf.html (source at https://github.com/NixOS/patchelf)"
fi
