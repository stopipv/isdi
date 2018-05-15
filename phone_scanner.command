# . scripts/setup.sh
cd /Users/rahul/phone_scanner
mkdir -p phone_dumps data
python3 server.py $@  2>&1 >>scanner.log &
sleep 2
/usr/bin/open -a "/Applications/Google Chrome.app" 'http://localhost:5000' 2>&1 >>chrome.log &
