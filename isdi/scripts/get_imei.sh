#!/usr/bin/env bash

a=$(adb shell service call iphonesubinfo 1 | awk -F "'" '{print $2}' | sed '1 d' | tr -d '.' | awk '{print}' ORS= | awk '{print $1}')
echo $a
