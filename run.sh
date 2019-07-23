DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
platform='unknown'
unamestr=`uname`
if [[ "$unamestr" == 'Linux' ]]; then
   platform='linux'
elif [[ "$unamestr" == 'Darwin' ]]; then
    platform='darwin'
elif [[ "$unamestr" == 'FreeBSD' ]]; then
   platform='freebsd'
fi

if [[ $platform == 'darwin' ]]; then
    export PATH=${DIR}/static_data/libimobiledevice-darwin/:$PATH
    export DYLD_LIBRARY_PATH=${DIR}/static_data/libimobiledevice-darwin/
elif [[ $platform == 'linux' ]]; then
    export PATH=${DIR}/static_data/libimobiledevice-linux/:$PATH
fi

export DEBUG=0
export TEST=0
python3 server.py $@
