#!/usr/bin/env python3
"""Diagnostic script to check if routes are registered"""

from isdi.app import create_app

app = create_app()

print("=" * 60)
print("REGISTERED ROUTES:")
print("=" * 60)

for rule in app.url_map.iter_rules():
    methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
    print(f"{rule.rule:50s} {methods:20s} {rule.endpoint}")

print("=" * 60)
print(f"\nTotal routes: {len(list(app.url_map.iter_rules()))}")

# Check specifically for our endpoint
termux_route = [r for r in app.url_map.iter_rules() if 'termux' in r.rule.lower()]
if termux_route:
    print(f"\n✓ Found termux-usb-permission route: {termux_route}")
else:
    print("\n✗ termux-usb-permission route NOT found!")
