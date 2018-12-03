cd -
# command -v ideviceinfo >/dev/null 2>&1 || ./ios_dependencies.sh
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

cd stati_data
ln -sf ./app-flags.csv  ./app-flags.csv~test
ln -sf ./app-info.db ./app-info.db~test
