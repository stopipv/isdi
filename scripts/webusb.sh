#!/usr/bin/env bash
function unbind {
	if [[ `uname` == 'Linux' ]]; then
		echo 'Linux detected.'
		echo 'Need custom udev rule for Linux...'

		# FIXME: grab idVendor and idProduct from `lsusb -v | grep ...`
		# won't work without this on a per-device basis.
		pkexec bash -c "echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="22b8",'\
		       ' ATTR{idProduct}=="2e76", MODE="0660", GROUP="plugdev"'\
		       > /etc/udev/rules.d/50-webusb.test.rules \
		       && echo 'custom udev rule set. Restarting udev...'\
		       && service udev restart && echo 'udev restarted.'"

		echo 'Checking if USB device is currently bound.'
		tree /sys/bus/usb/devices/1-1:1.0 | grep driver
		echo "Testing....don't unbind quite yet."
		#echo -n "1-1:1.0" > /sys/bus/usb/drivers/ub/unbind
	else
		echo 'Not Linux. WebUSB should work without any issues.'
	fi
}

function bind {
	echo "Doesn't do anything yet..(see https://lwn.net/Articles/143397/)"
	#echo -n "1-1:1.0" > /sys/bus/usb/drivers/ub/unbind
}

if [[ "$1" == 'unbind' ]]; then
	unbind
elif [[ "$1" == 'bind' ]]; then
	bind
else
	echo "Usage: $ bash $0 <bind|unbind>"
		echo "'unbind' will take away `uname -n`'s driver connection to the mobile device"\
			"so that webUSB can claim it."
		echo "'bind' will restore `uname -n`'s driver connection to the mobile device."
		echo "HELPFUL HINT: to debug your chrome webUSB connection, check chrome://device-log"\
			"and check the Debug checkbox."
	exit -1;
fi
