#!/usr/bin/env bash
echo -e "\033[31mDev-Jam 12/01/2015 - Script to build Libimobiledevice\033[0m"
echo -e "\033[32m\033[1m\033[4m\033[5m\033[7mCreator Dev-Jam improved by matteyeux on 27/12/15\033[0m"

#######################################################################
#
#  Project......: autobuild.sh
#  Creator......: Dev-Jam remasterized for Matteyeux le 27/12/15
#######################################################################



function depends(){

        if [[ $(which apt-get) ]]; then
                sudo apt-get install -y git build-essential make autoconf \
                automake libtool openssl tar perl binutils gcc g++ \
                libc6-dev libssl-dev libusb-1.0-0-dev \
                libcurl4-gnutls-dev fuse libxml2-dev \
                libgcc1 libreadline-dev libglib2.0-dev libreadline-dev \
                libclutter-1.0-dev libzip-dev cython \
                libfuse-dev python-dev python2.7 \
                libncurses5 policykit-1
        else
                echo "Package manager is not supported"
                exit 1
        fi
}

function brew_install(){
        # Install Hombrew.
        if [[ ! -e $(which brew) ]]; then
                echo "Brew is not installed..."
                echo "installing brew..."
                sleep 1
                ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
        else
                echo "Brew already installed"
        fi

        # Install command-line tools using Homebrew.

        # Ask for the administrator password upfront.
        sudo -v

        # Keep-alive: update existing `sudo` time stamp until the script has finished.
        while true; do sudo -n true; sleep 60; kill -0 "$$" || exit; done 2>/dev/null &

        # Make sure we’re using the latest Homebrew.
        brew update

        # Upgrade any already-installed formulae.
        brew upgrade

	 # Install Development Packages;
        brew install libxml2
        brew install libzip
        brew install libplist
        brew update    
	brew install openssl    
	brew install usbmuxd
	ln -s /usr/local/opt/openssl/lib/libcrypto.1.0.0.dylib /usr/local/lib/    
	ln -s /usr/local/opt/openssl/lib/libssl.1.0.0.dylib /usr/local/lib
        brew install --HEAD libimobiledevice
	brew link --overwrite libimobiledevice
	brew install gnutls


        # Install Software;
        brew install automake
        brew install cmake
        brew install colormake
        brew install autoconf
        brew install libtool
        brew install pkg-config
        brew install gcc
        brew install libusb
        brew install glib

        # Install Optional;
        brew install Caskroom/cask/osxfuse

        
        # Install other useful binaries.
        brew install ack
        #brew install exiv2
        brew install git

        # Remove outdated versions from the cellar.
        brew cleanup
         
}

function build_libimobiledevice(){
        if [[ $(uname) == 'Darwin' ]]; then
                brew link openssl --force
        fi
        successlibs=()
        failedlibs=()
        libs=( "libplist" "libusbmuxd" "libimobiledevice" "usbmuxd" "libirecovery" \
                "ideviceinstaller" "libideviceactivation" "idevicerestore" "ifuse" )

        spinner() {
            local pid=$1
            local delay=0.75
            local spinstr='|/-\'
            echo "$pid" > "/tmp/.spinner.pid"
            while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
                local temp=${spinstr#?}
                printf " [%c]  " "$spinstr"
                local spinstr=$temp${spinstr%"$temp"}
                sleep $delay
                printf "\b\b\b\b\b\b"
            done
            printf "    \b\b\b\b"
        }

        buildlibs() {
          mkdir -p ./ios_deps && cd ios_deps
                for i in "${libs[@]}"
                do
                        echo -e "\033[1;32mFetching $i..."
                        git clone https://github.com/libimobiledevice/${i}.git
                        cd $i
                        echo -e "\033[1;32mConfiguring $i..."
                        ./autogen.sh
                        ./configure
                        echo -e "\033[1;32mBuilding $i..."
                        make && sudo make install
                        echo -e "\033[1;32mInstalling $i..."
                        cd ..
                done
          cd ..
        }

        buildlibs
        if [[ -e $(which ldconfig) ]]; then
        	ldconfig
        else 
        	echo " "
        fi
}

if [[ $(uname) == 'Linux' ]]; then
        depends
elif [[ $(uname) == 'Darwin' ]]; then
        brew_install
fi
build_libimobiledevice
echo -e "\033[32m\033[1m\033[4m\033[5m\033[7mLibimobiledevice installed success Thanks for use Script\033[0m"
