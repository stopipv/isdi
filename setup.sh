#!/bin/bash
cd /tmp;
curl -O https://dl.google.com/android/repository/platform-tools_r26.0.0-darwin.zip
unzip platform-tools_r26.0.0-darwin.zip
mv platform-tools ~/.platform-tools
export ANDROID_HOME=~/.platform-tools
