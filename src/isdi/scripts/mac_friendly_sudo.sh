#!/usr/bin/env bash
# https://stackoverflow.com/a/3034671
export bar=""
for i in "$@"; do export bar="$bar '${i}'";done
osascript -e "do shell script \"$bar\" with administrator privileges"
