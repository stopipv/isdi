#!/bin/bash
cd /tmp;
if [[ "$uname" == "Linux" ]]; then 
    curl -O https://dl.google.com/android/repository/platform-tools_r26.0.0-linux.zip
    unzip platform-tools_r26.0.0-linux.zip
else
    curl -O https://dl.google.com/android/repository/platform-tools_r26.0.0-darwin.zip
    unzip platform-tools_r26.0.0-darwin.zip
fi
mv platform-tools ~/.platform-tools
export ANDROID_HOME=~/.platform-tools
export PATH=$ANDROID_HOME:$PATH
