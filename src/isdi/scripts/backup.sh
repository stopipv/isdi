#!/usr/bin/env bash

# Adb creates a backup of an app and then creates a folder containing
# All the data stored in that folder. 
# This works only for apps that do not disallow backup.
adb backup -f $1.ab $1
dd if=$1.ab bs=24 skip=1 |  zlib-flate -uncompress > backup.tar
tar -xf backup.tar
rm -rf $1.ab backup.tar
