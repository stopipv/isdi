"""Configuration management with XDG Base Directory support"""

import hashlib
import os
import sys
import shutil
from pathlib import Path
from typing import Optional
import secrets

__all__ = ["Config", "get_config", "get_data_dir", "get_config_dir"]

# SHA-256 of the app-info.db release asset. Update it whenever the asset at
# https://github.com/stopipv/isdi/releases/tag/app-info is replaced.
APP_INFO_DB_SHA256 = "87ea193f41b35b94f7136560a8b570a2c97a81ccd45bd0dcac4ce4acaa456f38"


def _private_dir(path: Path) -> None:
    """Create path (and parents) and restrict it to the current user (0700).

    chmod can fail on filesystems without Unix permissions (e.g. Android
    shared storage under Termux); that is not fatal.
    """
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass


def _private_key_file(path: Path, nbytes: int = 32) -> bytes:
    """Return the key stored in path, creating it (0600) if missing."""
    if not path.exists():
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(secrets.token_bytes(nbytes))
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    with open(path, "rb") as f:
        return f.read()


def get_platform_dirs():
    """Get platform-specific directories (XDG-compliant)"""

    # Check if running in Termux
    if os.environ.get("PREFIX"):
        # Termux paths
        return {
            "data": Path.home() / "storage" / "shared" / "isdi",
            "config": Path.home() / ".config" / "isdi",
            "cache": Path.home() / ".cache" / "isdi",
            "local_data": Path.home() / ".local" / "share" / "isdi",
        }

    # Standard XDG paths
    data_home = os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
    config_home = os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
    cache_home = os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")

    return {
        "data": Path(data_home) / "isdi",
        "config": Path(config_home) / "isdi",
        "cache": Path(cache_home) / "isdi",
        "local_data": Path(data_home) / "isdi",
    }


class Config:
    """Application configuration"""

    def __init__(self, env: str = "production"):
        self.env = env
        self.dirs = get_platform_dirs()

        # Ensure directories exist and are private to this user
        for dir_path in self.dirs.values():
            _private_dir(dir_path)

        # Setup paths
        self.setup_paths()

        # Setup secrets
        self.setup_secrets()

        # Per-run token required by every web route (see isdi.app). Kept in the
        # environment so the debug reloader's child process uses the same one.
        self.ACCESS_TOKEN = os.environ.get("ISDI_ACCESS_TOKEN") or secrets.token_urlsafe(32)
        os.environ["ISDI_ACCESS_TOKEN"] = self.ACCESS_TOKEN

        # Basic settings
        self.TEST = env == "test"
        self.DEBUG = env == "development"

        # App metadata
        self.TITLE = "ISDi - Stalkerware Scanner"
        self.VERSION = "1.0.0"
        self.DEVICE_PRIMARY_USER = "client"  # Default label for device owner

        # Platform detection
        import platform

        self.PLATFORM = platform.system().lower()
        if "microsoft" in platform.release().lower():  # Check for WSL
            self.PLATFORM = "wsl"

        # Additional paths for legacy compatibility
        self.STATIC_DATA = str(self.package_data)
        self.ADB_PATH = "adb" + (".exe" if self.PLATFORM in ("wsl", "win32") else "")
        # Keep dumps under the legacy dumps path for compatibility.
        self.DUMP_DIR = str(self.dumps_dir)
        self.DEV_SUPPORTED = ["android", "ios"]  # Supported device types
        self.SCRIPT_DIR = Path(__file__).parent / "scripts"  # Shell scripts in package

        # iOS tools: IOS_CLI is an argv prefix, IOS_CLI_ENV the environment
        # to run it with (None means inherit).
        self.IOS_CLI_ENV = None
        if os.environ.get("PREFIX"):
            pyz_path = None
            argv_path = Path(sys.argv[0]).resolve()
            if argv_path.suffix == ".pyz" and argv_path.exists():
                pyz_path = argv_path
            else:
                for entry in sys.path:
                    if entry.endswith(".pyz"):
                        candidate = Path(entry)
                        if candidate.exists():
                            pyz_path = candidate
                            break

            self.IOS_CLI = [sys.executable, "-m", "isdi.scanner.pmd3_wrapper"]
            if pyz_path is not None:
                # Shiv bundles packages under site-packages inside the .pyz
                self.IOS_CLI_ENV = {
                    **os.environ,
                    "PYTHONPATH": f"{pyz_path}/site-packages",
                }
        else:
            self.IOS_CLI = [
                "pymobiledevice3" if self.PLATFORM != "wsl" else "pymobiledevice3.exe"
            ]

        # Approved app installers
        self.APPROVED_INSTALLERS = {
            "com.android.vending",
            "com.sec.android.preloadinstaller",
        }

        # Error logging
        self.ERROR_LOG = []

        # CSV files
        self.SPYWARE_LIST_FILE = self.package_data / "stalkerware-indicators.csv"
        self.APP_INFO_SQLITE_FILE = f'sqlite:///{self.dirs["cache"]}/app-info.db'
        self.ANDROID_PERMISSIONS_CSV = self.package_data / "android_permissions.csv"
        self.ANDROID_PERMISSIONS = self.package_data / "android_permissions.txt"
        self.TEST_APP_LIST = self.package_data / "android.test.apps_list"

        # Ensure app-info.db exists in cache for runtime lookups
        self._ensure_app_info_db()

        # Source files for data_process (creating app-info database)
        self.source_files = {
            "playstore": str(self.package_data / "android_apps_crawl.csv.gz"),
            "appstore": str(self.package_data / "ios_apps_crawl.csv.gz"),
            "offstore": str(self.package_data / "offstore_apks.csv"),
        }

        # IOC (Indicators of Compromise)
        self.IOC_PATH = self.package_data / "stalkerware-indicators"
        self.IOC_FILE = self.IOC_PATH / "ioc.yaml"

        # Date format
        self.DATE_STR = "%Y-%m-%d %H:%M:%S"

        # Logging
        import logging

        self.logging = logging.getLogger("isdi")

    def error(self):
        """Return error message/status"""
        return ""  # Empty error means no error

    def hmac_serial(self, serial: str) -> str:
        """HMAC hash of device serial for privacy"""
        import hmac
        import hashlib

        key = self.PII_KEY
        return hmac.new(key, serial.encode(), hashlib.sha256).hexdigest()

    def setup_paths(self):
        """Setup all application paths"""
        # Data directories
        self.scans_dir = self.dirs["data"] / "scans"
        self.reports_dir = self.dirs["data"] / "reports"
        self.dumps_dir = self.dirs["data"] / "dumps"
        self.phone_dumps_dir = self.dirs["data"] / "phone_dumps"
        # Privacy-checkup screenshots; served only through a token-checked route
        self.screenshots_dir = self.dirs["local_data"] / "screenshots"

        # Config directory
        self.secrets_dir = self.dirs["config"]

        # Cache directory
        self.temp_dir = self.dirs["cache"] / "temp"
        self.logs_dir = self.dirs["cache"] / "logs"

        # Create all directories
        for path in [
            self.scans_dir,
            self.reports_dir,
            self.dumps_dir,
            self.phone_dumps_dir,
            self.screenshots_dir,
            self.temp_dir,
            self.logs_dir,
        ]:
            _private_dir(path)

        # Database
        self.database_path = self.dirs["local_data"] / "database.db"
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        # Bundled data (read-only, in package)
        self.package_data = Path(__file__).parent / "data"
        self.stalkerware_path = self.package_data / "stalkerware"

        # Legacy compatibility - point to user data dirs
        self.REPORT_PATH = str(self.reports_dir)
        self.SQL_DB_PATH = f"sqlite:///{self.database_path}"
        self.PHONE_DUMPS_PATH = str(self.phone_dumps_dir)
        self.LOGS_PATH = str(self.logs_dir)
        self.DUMPS_PATH = str(self.dumps_dir)

        # App flags file
        self.APP_FLAGS_FILE = self.package_data / "app-flags.csv"
        if not self.APP_FLAGS_FILE.exists():
            # Fallback to old location temporarily
            old_location = (
                Path(__file__).parent.parent.parent / "static_data" / "app-flags.csv"
            )
            if old_location.exists():
                self.APP_FLAGS_FILE = old_location

    def _ensure_app_info_db(self) -> None:
        """Download app-info.db from GitHub releases if missing or empty."""
        try:
            import time

            start = time.perf_counter()
            dst_db = Path(self.dirs["cache"]) / "app-info.db"

            # If database exists and has content, skip download
            if dst_db.exists() and dst_db.stat().st_size > 0:
                return

            # Try to download from GitHub releases
            import urllib.request
            import urllib.error

            # github_url = "https://github.com/rchatterjee/isdi/raw/refs/heads/main/static_data/app-info.db"
            github_url = "https://github.com/stopipv/isdi/releases/download/app-info/app-info.db"

            print(f"Downloading app-info.db from GitHub...")
            dst_db.parent.mkdir(parents=True, exist_ok=True)

            # Download to a temp file in the same directory, check the pinned
            # hash, then move it into place, so a partial or tampered download
            # is never used.
            tmp_db = dst_db.with_name(f".app-info.db.{os.getpid()}.tmp")
            try:
                digest = hashlib.sha256()
                with urllib.request.urlopen(github_url, timeout=30) as response:
                    if response.status == 200:
                        with open(tmp_db, "wb") as f:
                            for chunk in iter(lambda: response.read(1 << 20), b""):
                                digest.update(chunk)
                                f.write(chunk)
                        if digest.hexdigest() != APP_INFO_DB_SHA256:
                            print(
                                "Error: downloaded app-info.db does not match the expected "
                                f"SHA-256 ({digest.hexdigest()} != {APP_INFO_DB_SHA256}); "
                                "not using it."
                            )
                            return
                        os.replace(tmp_db, dst_db)
                        print(
                            f"✓ Downloaded app-info.db ({dst_db.stat().st_size} bytes)"
                        )
                        print(
                            f"app-info.db ready in {time.perf_counter() - start:.2f}s"
                        )
                        return
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    print(f"Warning: app-info.db not found in GitHub releases.")
                else:
                    print(f"Warning: Failed to download app-info.db: HTTP {e.code}")
            except Exception as e:
                print(f"Error: Failed to download app-info.db: {e}")
                print("App information database is required for ISDi to function.")
                print("Please check your internet connection and try again.")
                print(f"If the problem persists, manually download from:")
                print(f"  {github_url}")
                print(f"And place it at: {dst_db}")
                print(f"app-info.db download attempt took {time.perf_counter() - start:.2f}s")
            finally:
                tmp_db.unlink(missing_ok=True)

        except Exception as e:
            # Avoid failing config init if download fails
            print(f"Error: Could not download app-info.db: {e}")
            print("App information database is required for full functionality.")
            return

    def setup_secrets(self):
        """Setup encryption keys and secrets"""
        # PII encryption key
        self.pii_key_file = self.secrets_dir / "pii.key"
        self.PII_KEY = _private_key_file(self.pii_key_file)[:32]

        # Flask secret
        self.flask_secret_file = self.secrets_dir / "flask.secret"
        self.FLASK_SECRET = _private_key_file(self.flask_secret_file)

    def set_test_mode(self, enabled: bool = True):
        """Set test mode"""
        self.TEST = enabled
        if enabled:
            self.DEBUG = True

    def setup_logger(self):
        """Setup logging"""
        import logging

        log_file = self.logs_dir / "isdi.log"
        logging.basicConfig(
            level=logging.DEBUG if self.DEBUG else logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
            handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
        )

    @property
    def host(self) -> str:
        # Never listen on other interfaces by default: the web UI can run
        # commands on the connected phone.
        return "127.0.0.1"

    @property
    def port(self) -> int:
        return 6202 if self.TEST else (6200 if not self.DEBUG else 6201)


# Global config instance
_config: Optional[Config] = None


def get_config(env: str = "production") -> Config:
    """Get or create global config instance"""
    global _config
    if _config is None:
        _config = Config(env)
    return _config


def get_data_dir() -> Path:
    """Get user data directory"""
    return get_platform_dirs()["data"]


def get_config_dir() -> Path:
    """Get config directory"""
    return get_platform_dirs()["config"]
