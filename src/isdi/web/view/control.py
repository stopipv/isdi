from isdi.web import app
from flask import request, jsonify
import subprocess
import json
import os


@app.route("/kill", methods=["POST", "GET"])
def killme():
    func = request.environ.get("werkzeug.server.shutdown")
    if func is None:
        raise RuntimeError("Not running with the Werkzeug Server")
    func()
    return "The app has been closed!"


@app.route("/termux-usb-permission", methods=["POST"])
def request_termux_usb_permission():
    """Request USB permission for iOS device in Termux"""
    # Temporarily disabled for testing
    # if not os.environ.get('PREFIX'):
    #     return jsonify({"error": "This endpoint is only available on Termux"}), 403
    
    try:
        # First, list USB devices
        result = subprocess.run(
            ["termux-usb", "-l"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return jsonify({"error": f"Failed to list USB devices: {result.stderr}"}), 500
        
        # Parse the JSON output to get the first device
        try:
            devices = json.loads(result.stdout)
            if not devices or len(devices) == 0:
                return jsonify({"error": "No USB devices found. Please connect a device via USB."}), 404
            
            device_path = devices[0]
        except json.JSONDecodeError:
            return jsonify({"error": f"Failed to parse USB devices: {result.stdout}"}), 500
        
        # Request permission for the device and start usbmuxd
        # Note: This will show a permission dialog to the user on Android
        cmd = ["termux-usb", "-r", "-E", "-e", "usbmuxd -f -v", device_path]
        
        # Run in background since usbmuxd is a daemon
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        
        return jsonify({
            "success": True,
            "message": "USB permission requested. Please allow access in the Android permission dialog.",
            "device": device_path
        }), 200
        
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Command timed out"}), 500
    except FileNotFoundError:
        return jsonify({"error": "termux-usb command not found. Please install the Termux:API app."}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500
