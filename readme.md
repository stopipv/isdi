# Anti-spyware windows client

This is a small basic script + gui performing the same capabilities
as the anti-spyware android app.

### Requirements
Please refer to [requirements file](requirement.txt) before running it.

### Prerequisite
The script works on a phone connected to the computer via usb.
The phone must have usb-debugging enabled.

### Code
one file: gui.py
The code gets all packages installed o nthe phone. and compares their names
to the app database. Right now it's the database located in this repo.

The matching apps (dual-apps) will be desplayed on screen with some data and you can
choose to uninstall them.