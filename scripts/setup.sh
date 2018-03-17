#!/bin/bash
cd /tmp;
command -v adb &>/dev/null
if [[ "$?" -ne "0" ]]; then 
    if [[ "$uname" == "Linux" ]]; then 
	curl -O https://dl.google.com/android/repository/platform-tools_r26.0.0-linux.zip
	unzip -q platform-tools_r26.0.0-linux.zip
    else
	curl -O https://dl.google.com/android/repository/platform-tools_r26.0.0-darwin.zip
	unzip -q platform-tools_r26.0.0-darwin.zip
    fi
    if [ ! -e "$HOME/.platform-tools" ]; then
	mv platform-tools "$HOME/.platform-tools"
    fi
    export ANDROID_HOME=$HOME/.platform-tools
fi
command -v mobiledevice &>/dev/null
if [[ "$?" -ne "0" ]]; then 
    git clone https://github.com/imkira/mobiledevice.git && \
	cd ./mobiledevice && make && make install
fi

PATH=$PATH:$ANDROID_HOME
export PATH
cd -