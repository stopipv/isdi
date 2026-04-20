# ISDI Refactoring Guide
## From Messy Script to Professional Python Package

## Current Problems 🔴

1. **Entry point confusion**: `isdi` script mixed with package code
2. **Data pollution**: Write files (`data/`, `dumps/`, `logs/`) mixed with source
3. **Config chaos**: Hardcoded paths in `config.py`
4. **No standard structure**: Not pip-installable, hard to package
5. **Import issues**: Can't use as library, only as script
6. **Testing difficulties**: Hard to test with absolute paths everywhere

## Proposed New Structure 🟢

```
isdi/
├── pyproject.toml          # Modern Python packaging (PEP 517/518)
├── setup.py                # Backwards compatibility
├── README.md
├── LICENSE
├── CHANGELOG.md
├── .gitignore
│
├── src/
│   └── isdi/               # Main package
│       ├── __init__.py     # Package init, version
│       ├── __main__.py     # Entry point for `python -m isdi`
│       ├── cli.py          # CLI interface (uses Click/Typer)
│       ├── config.py       # Config management (XDG paths)
│       ├── app.py          # Flask app factory
│       │
│       ├── scanner/        # Core scanning logic (renamed from phone_scanner)
│       │   ├── __init__.py
│       │   ├── android.py
│       │   ├── ios.py
│       │   ├── blocklist.py
│       │   ├── permissions.py
│       │   └── privacy_scan.py
│       │
│       ├── web/            # Flask views/routes
│       │   ├── __init__.py
│       │   ├── routes.py
│       │   ├── forms.py
│       │   └── models.py
│       │
│       └── data/           # Bundled reference data (read-only)
│           ├── permissions.json
│           ├── stalkerware/
│           └── device_ids.json
│
├── tests/                  # Test suite
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_scanner.py
│   └── test_web.py
│
├── scripts/                # Utility scripts (optional)
│   ├── android_scan.sh
│   └── ios_scan.sh
│
└── docs/                   # Documentation
    ├── installation.md
    ├── usage.md
    └── api.md
```

## User Data Structure (XDG-compliant)

```
# Linux/Mac
~/.local/share/isdi/        # XDG_DATA_HOME
  ├── scans/                # Scan results
  ├── reports/              # Generated reports
  └── database.db           # SQLite DB

~/.config/isdi/             # XDG_CONFIG_HOME
  ├── config.yaml           # User configuration
  └── secrets.key           # PII encryption key

~/.cache/isdi/              # XDG_CACHE_HOME
  └── temp/                 # Temporary files

# Android/Termux
~/storage/shared/isdi/      # Accessible to user
  ├── scans/
  └── reports/

~/.local/share/isdi/        # Hidden data
  ├── config/
  └── database.db
```

## Step-by-Step Refactoring Plan

### Phase 1: Structure Setup ⭐ START HERE

**Create new directory structure**
```bash
mkdir -p src/isdi/scanner src/isdi/web src/isdi/data tests docs scripts
```

**Move files systematically**
```bash
# Core package files
mv phone_scanner/* src/isdi/scanner/
mv web/* src/isdi/web/
mv static_data/* src/isdi/data/
mv stalkerware-indicators src/isdi/data/stalkerware

# Tests
mv tests/* tests/  # Keep structure

# Scripts
mv scripts/*.sh scripts/  # Keep as-is

# Templates and static files
mkdir -p src/isdi/web/templates src/isdi/web/static
mv templates/* src/isdi/web/templates/
mv webstatic/* src/isdi/web/static/
```

### Phase 2: Modern Packaging Configuration

**Create `pyproject.toml`**
```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "isdi"
version = "1.0.0"
description = "Intimate Surveillance Detection Instrument - Phone privacy scanner"
readme = "README.md"
requires-python = ">=3.8"
license = {text = "GPL-3.0"}
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]
keywords = ["privacy", "security", "stalkerware", "phone-scanner"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: End Users/Desktop",
    "Topic :: Security",
    "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

dependencies = [
    "flask>=3.0",
    "flask-sqlalchemy>=3.0",
    "flask-migrate>=4.0",
    "flask-wtf>=1.2",
    "wtforms-alchemy>=0.19",
    "pymobiledevice3>=4.0",
    "pandas>=2.0",
    "click>=8.0",
    "pyyaml>=6.0",
    "cryptography>=40.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "black>=23.0",
    "ruff>=0.1.0",
    "mypy>=1.0",
]
termux = [
    "pymobiledevice3>=4.0",
]
full = [
    "isdi[dev,termux]",
]

[project.scripts]
isdi = "isdi.cli:main"

[project.urls]
Homepage = "https://github.com/yourusername/isdi"
Documentation = "https://isdi.readthedocs.io"
Repository = "https://github.com/yourusername/isdi"
Changelog = "https://github.com/yourusername/isdi/blob/main/CHANGELOG.md"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
isdi = [
    "data/**/*",
    "web/templates/**/*",
    "web/static/**/*",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v --cov=isdi --cov-report=html --cov-report=term"

[tool.black]
line-length = 100
target-version = ['py38', 'py39', 'py310', 'py311', 'py312']

[tool.ruff]
line-length = 100
target-version = "py38"
```

### Phase 3: Smart Configuration Management

**Create `src/isdi/config.py` (NEW VERSION)**

```python
"""Configuration management with XDG Base Directory support"""
import os
import sys
from pathlib import Path
from typing import Optional
import secrets
import yaml

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
        
        # Load user config
        self.config_file = self.dirs['config'] / 'config.yaml'
        self.settings = self._load_config()
        
        # Setup paths
        self.setup_paths()
        
        # Setup secrets
        self.setup_secrets()
    
    def _load_config(self) -> dict:
        """Load configuration from file"""
        if self.config_file.exists():
            with open(self.config_file) as f:
                return yaml.safe_load(f) or {}
        
        # Create default config
        default_config = {
            'debug': False,
            'host': '127.0.0.1',
            'port': 6200,
            'database': str(self.dirs['local_data'] / 'database.db'),
        }
        
        # Save default config
        with open(self.config_file, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)
        
        return default_config
    
    def setup_paths(self):
        """Setup all application paths"""
        # Data directories
        self.scans_dir = self.dirs['data'] / 'scans'
        self.reports_dir = self.dirs['data'] / 'reports'
        self.dumps_dir = self.dirs['data'] / 'dumps'
        
        # Config directory
        self.secrets_dir = self.dirs['config']
        
        # Cache directory
        self.temp_dir = self.dirs['cache'] / 'temp'
        self.logs_dir = self.dirs['cache'] / 'logs'
        
        #  Create all directories
        for path in [self.scans_dir, self.reports_dir, self.dumps_dir, 
                     self.temp_dir, self.logs_dir]:
            path.mkdir(parents=True, exist_ok=True)
        
        # Database
        self.database_path = Path(self.settings.get('database', 
                                                     self.dirs['local_data'] / 'database.db'))
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Bundled data (read-only, in package)
        self.package_data = Path(__file__).parent / 'data'
        self.stalkerware_db = self.package_data / 'stalkerware'
        self.permissions_data = self.package_data / 'permissions.json'
    
    def setup_secrets(self):
        """Setup encryption keys and secrets"""
        # PII encryption key
        self.pii_key_file = self.secrets_dir / 'pii.key'
        if not self.pii_key_file.exists():
            with open(self.pii_key_file, 'wb') as f:
                f.write(secrets.token_bytes(32))
        
        with open(self.pii_key_file, 'rb') as f:
            self.pii_key = f.read(32)
        
        # Flask secret
        self.flask_secret_file = self.secrets_dir / 'flask.secret'
        if not self.flask_secret_file.exists():
            with open(self.flask_secret_file, 'wb') as f:
                f.write(secrets.token_bytes(32))
        
        with open(self.flask_secret_file, 'rb') as f:
            self.flask_secret = f.read()
    
    @property
    def debug(self) -> bool:
        return self.env == 'development' or self.settings.get('debug', False)
    
    @property
    def host(self) -> str:
        return '0.0.0.0' if not self.debug else self.settings.get('host', '127.0.0.1')
    
    @property
    def port(self) -> int:
        return self.settings.get('port', 6202 if self.debug else 6200)


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
```

### Phase 4: Clean Entry Points

**Create `src/isdi/__main__.py`**

```python
"""Entry point for python -m isdi"""
from isdi.cli import main

if __name__ == '__main__':
    main()
```

**Create `src/isdi/cli.py`**

```python
"""Command-line interface for ISDI"""
import sys
import webbrowser
from threading import Timer
from pathlib import Path

import click
from isdi.config import get_config
from isdi.app import create_app


@click.group()
@click.version_option()
def cli():
    """ISDI - Intimate Surveillance Detection Instrument"""
    pass


@cli.command()
@click.option('--host', default=None, help='Host to bind to')
@click.option('--port', type=int, default=None, help='Port to bind to')
@click.option('--debug/--no-debug', default=False, help='Enable debug mode')
@click.option('--no-browser', is_flag=True, help='Do not open browser')
def run(host, port, debug, no_browser):
    """Run the ISDI web server"""
    
    env = 'development' if debug else 'production'
    config = get_config(env)
    
    # Override from command line
    if host:
        config.settings['host'] = host
    if port:
        config.settings['port'] = port
    
    app = create_app(config)
    
    # Open browser after short delay
    if not no_browser and not debug:
        def open_browser():
            webbrowser.open(f'http://{config.host}:{config.port}')
        Timer(1.5, open_browser).start()
    
    click.echo(f'🔍 Starting ISDI on http://{config.host}:{config.port}')
    click.echo(f'📁 Data directory: {config.dirs["data"]}')
    click.echo(f'📊 Database: {config.database_path}')
    
    app.run(
        host=config.host,
        port=config.port,
        debug=config.debug,
        use_reloader=config.debug
    )


@cli.command()
def info():
    """Show configuration information"""
    config = get_config()
    
    click.echo('ISDI Configuration:')
    click.echo(f'  Environment: {config.env}')
    click.echo(f'  Data directory: {config.dirs["data"]}')
    click.echo(f'  Config directory: {config.dirs["config"]}')
    click.echo(f'  Cache directory: {config.dirs["cache"]}')
    click.echo(f'  Database: {config.database_path}')
    click.echo(f'  Scans: {config.scans_dir}')
    click.echo(f'  Reports: {config.reports_dir}')
    click.echo(f'  Logs: {config.logs_dir}')


@cli.command()
@click.option('--device-type', type=click.Choice(['android', 'ios']), required=True)
@click.option('--output', type=click.Path(), help='Output file path')
def scan(device_type, output):
    """Scan a connected device"""
    click.echo(f'Scanning {device_type} device...')
    # Implement scanning logic
    pass


@cli.command()
@click.confirmation_option(prompt='Are you sure you want to reset all data?')
def reset():
    """Reset all user data"""
    import shutil
    config = get_config()
    
    for dir_path in [config.scans_dir, config.reports_dir, config.dumps_dir]:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            dir_path.mkdir(parents=True)
    
    if config.database_path.exists():
        config.database_path.unlink()
    
    click.echo('✓ All data has been reset')


def main():
    """Main entry point"""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo('\n👋 Goodbye!')
        sys.exit(0)
    except Exception as e:
        click.echo(f'❌ Error: {e}', err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
```

**Create `src/isdi/app.py`** (Flask app factory)

```python
"""Flask application factory"""
from flask import Flask
from isdi.config import Config
from isdi.web import init_routes
from isdi.scanner import db


def create_app(config: Config = None) -> Flask:
    """Create and configure Flask application"""
    from isdi.config import get_config
    
    if config is None:
        config = get_config()
    
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent / 'web' / 'templates'),
        static_folder=str(Path(__file__).parent / 'web' / 'static'),
    )
    
    # Configuration
    app.config['SECRET_KEY'] = config.flask_secret
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{config.database_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database
    db.init_app(app)
    
    # Register routes
    init_routes(app)
    
    return app
```

### Phase 5: Update Git Ignore

**Create `.gitignore`**

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
ENV/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# User data (DO NOT COMMIT!)
data/
dumps/
reports/
logs/
phone_dumps/
*.db
*.log
*.key
*.secret

# OS
.DS_Store
Thumbs.db
```

## Migration Steps (Detailed)

### Step 1: Backup Everything
```bash
cp -r isdi isdi.backup
cd isdi
```

### Step 2: Create New Structure
```bash
# Run the refactoring script (I'll create this)
python3 refactor_project.py
```

### Step 3: Install in Development Mode
```bash
pip install -e ".[dev]"
```

### Step 4: Test
```bash
# Run as module
python -m isdi run --debug

# Or use entry point
isdi run --debug

# Run tests
pytest
```

### Step 5: Package for Distribution

**For PyPI:**
```bash
python -m build
twine upload dist/*
```

**For Termux (using new structure):**
```bash
# Much simpler now!
pip install shiv
shiv -o isdi.pyz -e isdi.cli:main -c isdi .
```

## Benefits of This Refactoring ✨

1. **Standard Structure**: Follows PEP 517/518, universally recognized
2. **Pip Installable**: `pip install isdi` or `pip install -e .`
3. **Clean Separation**: Code vs data vs user files
4. **XDG Compliant**: Respects user directory standards
5. **Easy Testing**: Proper test structure with fixtures
6. **Multiple Entry Points**: CLI, module, or as library
7. **Trivial Packaging**: One command for pip, shiv, or APK
8. **Better Imports**: `from isdi.scanner import AndroidScanner`
9. **Version Management**: Single source of truth in `pyproject.toml`
10. **Documentation Ready**: Standard structure for Sphinx/MkDocs

## Next Steps

Would you like me to:
1. **Create the refactoring script** that automates the migration?
2. **Refactor specific modules** (scanner, web, config) one by one?
3. **Focus on packaging** first to get Termux working ASAP?
4. **Set up the new structure** and we migrate incrementally?

Let me know which approach you prefer!
