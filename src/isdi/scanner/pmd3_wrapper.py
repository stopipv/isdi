"""Termux wrapper for pymobiledevice3 with usbmux patches.

This module patches pymobiledevice3 for Termux/Android compatibility and can be
invoked as: python3 -m isdi.scanner.pmd3_wrapper <args>
"""

import sys
import socket

import pymobiledevice3.osu.os_utils as os_utils_module
import pymobiledevice3.usbmux as usbmux_module


def _fake_is_wsl():
    """Prevent pymobiledevice3 from detecting WSL incorrectly."""
    return False


# Patch: Prevent WSL detection
os_utils_module.is_wsl = _fake_is_wsl

# Store original method
_original_create = usbmux_module.MuxConnection.create_usbmux_socket


@staticmethod
def patched_create_usbmux_socket(usbmux_address=None):
    """Patch: Force use of Termux usbmux socket path."""
    socket_path = "/data/data/com.termux/files/usr/var/run/usbmuxd"
    if usbmux_address is None:
        return usbmux_module.SafeStreamSocket(socket_path, socket.AF_UNIX)
    return _original_create(usbmux_address)


# Apply usbmux patch
usbmux_module.MuxConnection.create_usbmux_socket = patched_create_usbmux_socket


def main():
    """Entry point: call pymobiledevice3 with patches applied."""
    from pymobiledevice3.__main__ import main as pmd3_main
    return pmd3_main()


if __name__ == "__main__":
    sys.exit(main())
