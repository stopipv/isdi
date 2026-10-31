"""Point ISDi's config, data and cache dirs at a temporary directory.

This runs before any test imports isdi, so tests never read or write the
user's real database, keys or dumps. An existing app-info.db in the real
cache is linked in to avoid a 47 MB download on every run.
"""

import os
import tempfile
from pathlib import Path

_real_cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "isdi"
_tmp = Path(tempfile.mkdtemp(prefix="isdi-tests-"))
for name in ("XDG_DATA_HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME"):
    os.environ[name] = str(_tmp / name.lower())

_real_db = _real_cache / "app-info.db"
if _real_db.exists():
    test_cache = _tmp / "xdg_cache_home" / "isdi"
    test_cache.mkdir(parents=True)
    (test_cache / "app-info.db").symlink_to(_real_db)

os.environ.pop("PREFIX", None)  # not Termux
os.environ.pop("ISDI_ACCESS_TOKEN", None)
