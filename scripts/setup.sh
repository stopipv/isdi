#!/bin/bash
cd /tmp;
command -v adb &>/dev/null
if [[ "$?" -ne "0" ]]; then 
    if [[ ! -e "$HOME/.platform-tools" ]]; then 
        if [[ "$uname" == "Linux" ]]; then 
	    curl -O https://dl.google.com/android/repository/platform-tools_r26.0.0-linux.zip
	    unzip -q platform-tools_r26.0.0-linux.zip
        else
	    curl -O https://dl.google.com/android/repository/platform-tools_r26.0.0-darwin.zip
	    unzip -q platform-tools_r26.0.0-darwin.zip
        fi
	mv platform-tools "$HOME/.platform-tools"
    fi
    export ANDROID_HOME=$HOME/.platform-tools
else
    export ANDROID_HOME=$(dirname $(which adb))
fi

cd -
git submodule update --recursive --remote && cd ios-deploy && xcodebuild
# Does not work for all versions of iOS
# command -v mobiledevice &>/dev/null
# if [[ "$?" -ne "0" ]]; then 
#     git clone https://github.com/imkira/mobiledevice.git && \
# 	cd ./mobiledevice && make && make install
# fi

export PATH=$PATH:$ANDROID_HOME
cd -
