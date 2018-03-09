adb backup -f $1.db $1
dd if=$1.db bs=24 skip=1 |  zlib-flate -uncompress > backup.tar
tar -xf backup.tar
