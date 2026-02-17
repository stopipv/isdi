#!/usr/bin/env python3
"""Termux wrapper for pymobiledevice3 with usbmux patches."""

import sys
import socket

import pymobiledevice3.osu.os_utils as os_utils_module
import pymobiledevice3.usbmux as usbmux_module


def _fake_is_wsl():
    return False


os_utils_module.is_wsl = _fake_is_wsl

_original_create = usbmux_module.MuxConnection.create_usbmux_socket


@staticmethod
def patched_create_usbmux_socket(usbmux_address=None):
    socket_path = "/data/data/com.termux/files/usr/var/run/usbmuxd"
    if usbmux_address is None:
        return usbmux_module.SafeStreamSocket(socket_path, socket.AF_UNIX)
    return _original_create(usbmux_address)


usbmux_module.MuxConnection.create_usbmux_socket = patched_create_usbmux_socket


def main() -> int:
    from pymobiledevice3.__main__ import main as pmd3_main

    return pmd3_main()


if __name__ == "__main__":
    sys.exit(main())
