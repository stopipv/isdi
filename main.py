#!/usr/bin/env python3
"""
Main entry point for ISDI Android APK
Bridges between Android app and Flask backend
"""
import os
import sys

def main():
    # Set up Android-specific paths
    if 'ANDROID_STORAGE' in os.environ:
        # Running as APK
        from android.permissions import request_permissions, Permission
        request_permissions([
            Permission.WRITE_EXTERNAL_STORAGE,
            Permission.READ_EXTERNAL_STORAGE,
            Permission.INTERNET
        ])
        
        # Set data directories
        storage = os.environ.get('EXTERNAL_STORAGE', '/sdcard')
        os.makedirs(f'{storage}/isdi/dumps', exist_ok=True)
        os.makedirs(f'{storage}/isdi/reports', exist_ok=True)
    
    # Import and run the Flask app
    from config import app
    
    # # For APK, we'll use webview
    # try:
    #     from android import AndroidBrowser
    #     browser = AndroidBrowser()
    #     browser.open('http://127.0.0.1:5000')
    # except ImportError:
    #     print("Visit http://127.0.0.1:5000 in your browser")
    
    # Run Flask server
    app.run(host='127.0.0.1', port=5000, debug=False)

if __name__ == '__main__':
    main()
