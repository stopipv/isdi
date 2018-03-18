#!/bin/bash 

python2=(which python2)
if [[ "$?" != "0" ]]; then
  echo "You need python2 to be able to run this code"
  exit -1;
fi


