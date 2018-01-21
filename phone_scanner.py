#!/usr/bin/env python3

import subprocess
import pandas as pd
import config

'''
NEED https://github.com/imkira/mobiledevice installed (`brew install mobiledevice` or build from source).
'''
def ios_scan(phone_id):
   installed_apps = subprocess.run(['mobiledevice', 'list_apps', '-u', phone_id], stdout=subprocess.PIPE) 
   if (installed_apps.returncode != 0):
       print("Error running iOS device scan. Is the 'https://github.com/imkira/mobiledevice' \
            'code installed on this Mac?")
       exit(1)
   installed_apps = installed_apps.stdout
   installed_apps = installed_apps.split('\n').tolist()

   # NOTE: or use DB!
   apps_df = pd.read_csv(config.APPS_LIST, index_col='appId')
   apps_df['appId'] = apps_df.index
   relevant_spyware_df = apps_df[apps_df['relevant']=='y']
   
   spyware_on_phone = relevant_spyware_df['appId'].isin(installed_apps)
   print(spyware_on_phone)
   print(spyware_on_phone.value_counts())

def _dev_ios_scan():
   installed_apps = open(config.TEST_SCAN_RESULTS, 'r').read().splitlines()

   # NOTE: or use DB!
   apps_df = pd.read_csv(config.APPS_LIST, index_col='appId')
   apps_df['appId'] = apps_df.index
   relevant_spyware_df = apps_df[apps_df['relevant']=='y']
   
   spyware_on_phone = relevant_spyware_df['appId'].isin(installed_apps)
   print(spyware_on_phone)
   print(spyware_on_phone.value_counts())
  
#def android_scan(phone_id):

if __name__ == "__main__":
    _dev_ios_scan()
