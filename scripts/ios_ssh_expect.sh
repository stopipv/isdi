#!/usr/bin/expect
# https://stackoverflow.com/a/34361221

set timeout 4

set IP [lindex $argv 0]

spawn ssh -p 2222 -o StrictHostKeyChecking=no root@$IP

expect "password:" {
    send_user "\n0\n"
    exit 0
    }   
# "Error connecting to device!" if not jailbroken
send_user "\n1\n" exit 1
