"""
ISDI - Intimate Surveillance Detection Instrument
A privacy and security scanner for mobile devices
"""

import sys
import types

__version__ = "1.0.2"
__author__ = "ISDI Contributors"

from isdi.config import get_config, get_data_dir, get_config_dir

__all__ = ["get_config", "get_data_dir", "get_config_dir", "__version__"]
