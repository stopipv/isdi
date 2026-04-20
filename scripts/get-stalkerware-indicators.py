#!/usr/bin/env python3
"""
Fetch stalkerware indicators from AssoEchap/stalkerware-indicators
and update the app-flags.csv file with the latest package names.
"""

import csv
import sys
from pathlib import Path
from urllib.request import urlretrieve
from collections import defaultdict

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install with: pip install pyyaml")
    sys.exit(1)


# GitHub raw URL for the latest ioc.yaml file
IOC_URL = "https://raw.githubusercontent.com/AssoEchap/stalkerware-indicators/master/ioc.yaml"

# Paths relative to project root
PROJECT_ROOT = Path(__file__).parent.parent
APP_FLAGS_CSV = PROJECT_ROOT / "src" / "isdi" / "data" / "app-flags.csv"
TEMP_IOC_FILE = PROJECT_ROOT / "ioc.yaml.tmp"


def fetch_ioc_yaml():
    """Download the latest ioc.yaml file from GitHub."""
    print(f"Fetching IOC data from {IOC_URL}...")
    try:
        urlretrieve(IOC_URL, TEMP_IOC_FILE)
        print(f"✓ Downloaded to {TEMP_IOC_FILE}")
        return True
    except Exception as e:
        print(f"✗ Error downloading IOC file: {e}")
        return False


def parse_ioc_yaml():
    """Parse the ioc.yaml file and extract stalkerware package names."""
    print(f"Parsing {TEMP_IOC_FILE}...")
    
    try:
        with open(TEMP_IOC_FILE, 'r') as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"✗ Error parsing YAML: {e}")
        return {}
    
    stalkerware_packages = {}
    
    for app in data:
        app_name = app.get('name', 'Unknown')
        app_names = f"(Other names: {', '.join(app.get('names', []))})" if app.get('names') else ""
        app_type = app.get('type', 'unknown')
        packages = app.get('packages', [])
        
        # Only process stalkerware apps
        if app_type == 'stalkerware' and packages:
            for package in packages:
                if package and isinstance(package, str):
                    # Map package to app name
                    stalkerware_packages[package] = app_name + (" " + app_names if app_names else "")
    
    print(f"✓ Found {len(stalkerware_packages)} stalkerware packages")
    return stalkerware_packages


def update_app_flags(stalkerware_packages):
    """Update app-flags.csv with stalkerware package indicators."""
    print(f"Reading existing app-flags.csv from {APP_FLAGS_CSV}...")
    
    # Read existing CSV
    existing_apps = {}
    if APP_FLAGS_CSV.exists():
        with open(APP_FLAGS_CSV, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                app_id = row['appId']
                existing_apps[app_id] = row
    
    print(f"✓ Found {len(existing_apps)} existing apps in CSV")
    
    # Track changes
    added = 0
    updated = 0
    
    # Add/update stalkerware packages
    for package, app_name in stalkerware_packages.items():
        if package in existing_apps:
            # Update existing entry if not already marked as stalkerware
            if existing_apps[package]['flag'] != 'stalkerware':
                existing_apps[package]['flag'] = 'stalkerware'
                if not existing_apps[package]['title']:
                    existing_apps[package]['title'] = app_name
                updated += 1
        else:
            # Add new stalkerware entry
            existing_apps[package] = {
                'appId': package,
                'store': 'offstore',  # Default to playstore
                'flag': 'stalkerware',
                'title': app_name
            }
            added += 1
    
    # Write updated CSV
    print(f"Writing updated app-flags.csv...")
    with open(APP_FLAGS_CSV, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['appId', 'store', 'flag', 'title']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        # Sort by appId for consistency
        for app_id in sorted(existing_apps.keys()):
            writer.writerow(existing_apps[app_id])
    
    print(f"✓ Updated app-flags.csv:")
    print(f"  - Added: {added} new stalkerware apps")
    print(f"  - Updated: {updated} existing apps")
    print(f"  - Total apps: {len(existing_apps)}")
    
    return added, updated


def cleanup():
    """Remove temporary files."""
    if TEMP_IOC_FILE.exists():
        TEMP_IOC_FILE.unlink()
        print(f"✓ Cleaned up {TEMP_IOC_FILE}")


def main():
    """Main execution."""
    print("=" * 60)
    print("Stalkerware Indicators Updater")
    print("=" * 60)
    
    try:
        # Step 1: Fetch the IOC file
        if not fetch_ioc_yaml():
            return 1
        
        # Step 2: Parse the YAML
        stalkerware_packages = parse_ioc_yaml()
        if not stalkerware_packages:
            print("✗ No stalkerware packages found")
            return 1
        
        # Step 3: Update app-flags.csv
        added, updated = update_app_flags(stalkerware_packages)
        
        print("=" * 60)
        print("✓ Successfully updated stalkerware indicators!")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        cleanup()


if __name__ == "__main__":
    sys.exit(main())
