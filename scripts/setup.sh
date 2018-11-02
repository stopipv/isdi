#!/usr/bin/env bash
cd /tmp;
command -v adb &>/dev/null
if [[ "$?" -ne "0" ]]; then 
    if [[ ! -e "$HOME/.platform-tools" ]]; then 
        if [[ `uname` == "Linux" ]]; then 
            echo "Installing Linux adb..."
	    wget https://dl.google.com/android/repository/platform-tools-latest-linux.zip
	    unzip -q platform-tools-latest-linux.zip
        else
            echo "Installing macOS adb..."
	    wget https://dl.google.com/android/repository/platform-tools-latest-darwin.zip
	    unzip -q platform-tools-latest-darwin.zip
        fi
	mv platform-tools "$HOME/.platform-tools"
    fi
    export ANDROID_HOME=$HOME/.platform-tools
else
    export ANDROID_HOME=$(dirname $(which adb))
fi

cd -
command -v ideviceinfo >/dev/null 2>&1 || ./ios_dependencies.sh
#if [ ! -e ios-deploy/build/Release/ios-deploy ]; then
#   git submodule update --recursive --remote && cd ios-deploy && xcodebuild && cd -
#fi

# Does not work for all versions of iOS
# command -v mobiledevice &>/dev/null
# if [[ "$?" -ne "0" ]]; then 
#     git clone https://github.com/imkira/mobiledevice.git && \
# 	cd ./mobiledevice && make && make install
# fi

export PATH=$PATH:$ANDROID_HOME
