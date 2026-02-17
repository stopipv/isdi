"""Configuration management with XDG Base Directory support"""
import os
import sys
import shutil
from pathlib import Path
from typing import Optional
import secrets

__all__ = ['Config', 'get_config', 'get_data_dir', 'get_config_dir']


def get_platform_dirs():
    """Get platform-specific directories (XDG-compliant)"""
    
    # Check if running in Termux
    if os.environ.get('PREFIX'):
        # Termux paths
        return {
            'data': Path.home() / 'storage' / 'shared' / 'isdi',
            'config': Path.home() / '.config' / 'isdi',
            'cache': Path.home() / '.cache' / 'isdi',
            'local_data': Path.home() / '.local' / 'share' / 'isdi',
        }
    
    # Standard XDG paths
    data_home = os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share')
    config_home = os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')
    cache_home = os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache')
    
    return {
        'data': Path(data_home) / 'isdi',
        'config': Path(config_home) / 'isdi',
        'cache': Path(cache_home) / 'isdi',
        'local_data': Path(data_home) / 'isdi',
    }


class Config:
    """Application configuration"""
    
    def __init__(self, env: str = 'production'):
        self.env = env
        self.dirs = get_platform_dirs()
        
        # Ensure directories exist
        for dir_path in self.dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Setup paths
        self.setup_paths()
        
        # Setup secrets
        self.setup_secrets()
        
        # Basic settings
        self.TEST = env == 'test'
        self.DEBUG = env == 'development'
        
        # App metadata
        self.TITLE = "ISDI - Intimate Surveillance Detection Instrument"
        self.VERSION = "1.0.0"
        self.DEVICE_PRIMARY_USER = "client"  # Default label for device owner
        
        # Platform detection
        import platform
        self.PLATFORM = platform.system().lower()
        if 'microsoft' in platform.release().lower():  # Check for WSL
            self.PLATFORM = "wsl"
        
        # Additional paths for legacy compatibility
        self.STATIC_DATA = str(self.package_data)
        self.ADB_PATH = "adb" + (".exe" if self.PLATFORM in ("wsl", "win32") else "")
        self.DUMP_DIR = str(self.phone_dumps_dir)  # Phone dumps directory
        self.DEV_SUPPORTED = ["android", "ios"]  # Supported device types
        self.SCRIPT_DIR = Path(__file__).parent / "scripts"  # Shell scripts in package
        
        # iOS tools
        if os.environ.get("PREFIX"):
            # Termux: use module-based wrapper with current Python interpreter
            # This ensures the .pyz archive is in the Python path
            self.LIBIMOBILEDEVICE_PATH = f"{sys.executable} -m isdi.scanner.pmd3_wrapper"
        else:
            self.LIBIMOBILEDEVICE_PATH = "pymobiledevice3" if self.PLATFORM != "wsl" else "pymobiledevice3.exe"
        
        # Approved app installers
        self.APPROVED_INSTALLERS = {"com.android.vending", "com.sec.android.preloadinstaller"}
        
        # Error logging
        self.ERROR_LOG = []
        
        # CSV files
        self.SPYWARE_LIST_FILE = self.package_data / 'stalkerware-indicators.csv'
        self.APP_INFO_SQLITE_FILE = f'sqlite:///{self.dirs["cache"]}/app-info.db'
        self.ANDROID_PERMISSIONS_CSV = self.package_data / 'android_permissions.csv'
        self.ANDROID_PERMISSIONS = self.package_data / 'android_permissions.txt'
        self.TEST_APP_LIST = self.package_data / 'android.test.apps_list'

        # Ensure app-info.db exists in cache for runtime lookups
        self._ensure_app_info_db()
        
        # Source files for data_process (creating app-info database)
        self.source_files = {
            "playstore": str(self.package_data / 'android_apps_crawl.csv.gz'),
            "appstore": str(self.package_data / 'ios_apps_crawl.csv.gz'),
            "offstore": str(self.package_data / 'offstore_apks.csv'),
        }
        
        # IOC (Indicators of Compromise)
        self.IOC_PATH = self.package_data / 'stalkerware-indicators'
        self.IOC_FILE = self.IOC_PATH / 'ioc.yaml'
        
        # Date format
        self.DATE_STR = "%Y-%m-%d %H:%M:%S"
        
        # Logging
        import logging
        self.logging = logging.getLogger('isdi')

    
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
        self.scans_dir = self.dirs['data'] / 'scans'
        self.reports_dir = self.dirs['data'] / 'reports'
        self.dumps_dir = self.dirs['data'] / 'dumps'
        self.phone_dumps_dir = self.dirs['data'] / 'phone_dumps'
        
        # Config directory
        self.secrets_dir = self.dirs['config']
        
        # Cache directory
        self.temp_dir = self.dirs['cache'] / 'temp'
        self.logs_dir = self.dirs['cache'] / 'logs'
        
        # Create all directories
        for path in [self.scans_dir, self.reports_dir, self.dumps_dir, 
                     self.phone_dumps_dir, self.temp_dir, self.logs_dir]:
            path.mkdir(parents=True, exist_ok=True)
        
        # Database
        self.database_path = self.dirs['local_data'] / 'database.db'
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Bundled data (read-only, in package)
        self.package_data = Path(__file__).parent / 'data'
        self.stalkerware_path = self.package_data / 'stalkerware'
        
        # Legacy compatibility - point to user data dirs
        self.REPORT_PATH = str(self.reports_dir)
        self.SQL_DB_PATH = f'sqlite:///{self.database_path}'
        self.PHONE_DUMPS_PATH = str(self.phone_dumps_dir)
        self.LOGS_PATH = str(self.logs_dir)
        self.DUMPS_PATH = str(self.dumps_dir)
        
        # App flags file
        self.APP_FLAGS_FILE = self.package_data / 'app-flags.csv'
        if not self.APP_FLAGS_FILE.exists():
            # Fallback to old location temporarily
            old_location = Path(__file__).parent.parent.parent / 'static_data' / 'app-flags.csv'
            if old_location.exists():
                self.APP_FLAGS_FILE = old_location

    def _ensure_app_info_db(self) -> None:
        """Copy bundled app-info.db into cache if missing or empty."""
        try:
            src_db = self.package_data / 'app-info.db'
            dst_db = Path(self.dirs['cache']) / 'app-info.db'
            if not src_db.exists():
                return
            if not dst_db.exists() or dst_db.stat().st_size == 0:
                dst_db.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_db, dst_db)
        except Exception:
            # Avoid failing config init if copy fails
            return
    
    def setup_secrets(self):
        """Setup encryption keys and secrets"""
        # PII encryption key
        self.pii_key_file = self.secrets_dir / 'pii.key'
        if not self.pii_key_file.exists():
            with open(self.pii_key_file, 'wb') as f:
                f.write(secrets.token_bytes(32))
        
        with open(self.pii_key_file, 'rb') as f:
            self.PII_KEY = f.read(32)
        
        # Flask secret
        self.flask_secret_file = self.secrets_dir / 'flask.secret'
        if not self.flask_secret_file.exists():
            with open(self.flask_secret_file, 'wb') as f:
                f.write(secrets.token_bytes(32))
        
        with open(self.flask_secret_file, 'rb') as f:
            self.FLASK_SECRET = f.read()
    
    def set_test_mode(self, enabled: bool = True):
        """Set test mode"""
        self.TEST = enabled
        if enabled:
            self.DEBUG = True
    
    def setup_logger(self):
        """Setup logging"""
        import logging
        log_file = self.logs_dir / 'isdi.log'
        logging.basicConfig(
            level=logging.DEBUG if self.DEBUG else logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    
    @property
    def host(self) -> str:
        return '127.0.0.1' if self.DEBUG else '0.0.0.0'
    
    @property
    def port(self) -> int:
        return 6202 if self.TEST else (6200 if not self.DEBUG else 6201)


# Global config instance
_config: Optional[Config] = None


def get_config(env: str = 'production') -> Config:
    """Get or create global config instance"""
    global _config
    if _config is None:
        _config = Config(env)
    return _config


def get_data_dir() -> Path:
    """Get user data directory"""
    return get_platform_dirs()['data']


def get_config_dir() -> Path:
    """Get config directory"""
    return get_platform_dirs()['config']
