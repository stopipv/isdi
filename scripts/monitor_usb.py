from usbmonitor import USBMonitor
from usbmonitor.attributes import ID_MODEL, ID_MODEL_ID, ID_VENDOR_ID
import time
import json

device_info_str = lambda device_info: f"{device_info[ID_MODEL]} ({device_info[ID_MODEL_ID]} - {device_info[ID_VENDOR_ID]})"
# Define the `on_connect` and `on_disconnect` callbacks
on_connect = lambda device_id, device_info: print(f"Connected: {device_info_str(device_info=device_info)}")
on_disconnect = lambda device_id, device_info: print(f"Disconnected: {device_info_str(device_info=device_info)}")

# Create the USBMonitor instance
monitor = USBMonitor()

# Start the daemon
# monitor.start_monitoring(on_connect=on_connect, on_disconnect=on_disconnect, check_every_seconds=2)
monitor.check_changes(on_connect=on_connect, on_disconnect=on_disconnect)
print(f"Available devices: {json.dumps(monitor.get_available_devices(), indent=2)}")
time.sleep(5)
# ... Rest of your code ...

# If you don't need it anymore stop the daemon
# monitor.stop_monitoring()
