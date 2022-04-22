#!/usr/bin/env bash
aaptversion='3.2.1-4818971'
#wget https://dl.google.com/dl/android/maven2/com/android/tools/build/aapt2/$aaptversion/aapt2-$aaptversion-osx.jar
wget https://dl.google.com/dl/android/maven2/com/android/tools/build/aapt2/$aaptversion/aapt2-$aaptversion-linux.jar --no-check-certificate
#command -v jar >/dev/null 2>&1 || (brew tap caskroom/versions && brew cask install java8)
#jar xf aapt2-$aaptversion-osx.jar aapt2
jar xf aapt2-$aaptversion-linux.jar aapt2
chmod +x aapt2
