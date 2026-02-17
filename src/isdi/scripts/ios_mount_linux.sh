#!/usr/bin/env bash
#
# mount-iphone.sh
# This script attempts to mount or unmount the first connected ipod/iphone.
# Usage: ./mount-iphone.sh [mount | umount | echo_serial]
# It should be dash-friendly
#
# Written by Mohamed Ahmed, Dec 2010
#
# Refactored and extended by David Emerson, Feb 2012
# Refactored yet again by Sam Havron, Oct 2018 (with usbmuxd)
# 2017-04-04   DaveSp   In case more than one Apple device is attached via USB,
#                       "awk '/iSerial" now only matches when a serial number is
#                       present.
#
# You can configure send_msg to use either a console echo, or notify-send.
# notify-send is part of the debian package, libnotify-bin
# The apple pictures in /usr/share/pixmaps are part of the gnome-desktop-data package
#
# uncomment the following if you want to see the mount command used:
# show_mount_cmd=1

# you can uncomment this line to see all the commands sh executes:
# set -x

show_msg ()
{
  # notify-send -t 4000 -u normal "mount-iphone" "$1" -i "/usr/share/pixmaps/apple-$2.png"
  echo "$1" >&2
}

get_device_ids ()
{
  # get the Apple vendor id (idVendor) from lsusb
  idVendor=$(lsusb -v 2>/dev/null | awk '/idVendor.*Apple/{print $2; exit}')
  [ -z "$idVendor" ] && { show_msg "Cannot find any Apple device" "red"; exit 1; }
  # get the device serial number (iSerial)
  iSerial=$(lsusb -v -d $idVendor: 2>/dev/null | awk '/iSerial\s+\S+\s+\S/{print $3; exit}')
  [ -z "$iSerial" ] && { show_msg "Cannot find serial number of Apple device $idVendor" "red"; exit 1; }
}

is_mounted ()
{
  gvfs-mount mount -l | grep -i "mount.*$1" >/dev/null
}

mount_iphone ()
{
  # comments out the udev rule that exits usbmuxd when the last device is removed
  # FIXME: binaries not install daemon and other files?
  sudo sed -i '/s*ACTION=="remove", RUN+="\/usr\/local\/sbin\/usbmuxd -x"/ s|^|#|' \
    /lib/udev/rules.d/39-usbmuxd.rules
  # sudo usbmuxd -f may also help. (https://bbs.archlinux.org/viewtopic.php?id=229475)
  if sudo usbmuxd -u -U usbmux && is_mounted $1; then
    show_msg "mounted iphone with serial $1" "green"
  else
    show_msg "iphone mount failed" "red"
    exit 1
  fi
}

# not tested with usbmuxd mounting strategy. doesn't appear to work?
unmount_iphone ()
{
  ## now gvfs unmount the device
  [ -z $show_mount_cmd ] || echo gvfs-mount mount -u afc://$1/ >&2
  if gvfs-mount mount -u /run/user/`id -u $USER`/gvfs/afc:host=$1*; then
    show_msg "unmounted iphone with serial $1" "red"
  else
    show_msg "iphone umount failed" "red"
    exit 1
  fi
}

case $1 in
  mount)
    get_device_ids
    is_mounted $iSerial && { show_msg "$iSerial is already mounted" 'green'; exit; }
    show_msg "not mounted. mounting..."
    mount_iphone $iSerial
    ;;
  umount|unmount)
    get_device_ids
    is_mounted || { show_msg "$iSerial is not mounted" 'red'; exit; }
    unmount_iphone $iSerial
    ;;
  echo_serial)
    get_device_ids
    echo $iSerial
    ;;
  '')
    get_device_ids
    is_mounted $iSerial && show_msg "$iSerial is mounted" 'green' || show_msg "$iSerial is not mounted" 'red'
    ;;
  *)
    echo "Usage: $0 [mount | umount | echo_serial]"
    echo "(Not sure un-mounting works with usbmuxd...)"
    exit 1
    ;;
esac

exit 0
