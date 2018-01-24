#!/usr/bin/env python3

import subprocess
import pandas as pd
import config

'''
NEED https://github.com/imkira/mobiledevice installed (`brew install mobiledevice` or build from source).
'''
def ios_scan():
   installed_apps = subprocess.run(['mobiledevice', 'list_apps'], stdout=subprocess.PIPE) 
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
   
   #print('-'*80)
   #print('Apps Installed on Phone:')
   #print('-'*80)
   #print(installed_apps)
   print('-'*80)
   print('Spyware Apps Detected on Phone')
   print('-'*80)
   #print(spyware_on_phone[spyware_on_phone == True])
   apps = spyware_on_phone[spyware_on_phone == True]

   for app in apps.index:
       print(relevant_spyware_df[relevant_spyware_df['appId']==app]['title'][0])
   #print(spyware_on_phone.value_counts())

def _dev_ios_scan():
   installed_apps = open(config.TEST_SCAN_RESULTS, 'r').read().splitlines()

   # NOTE: or use DB!
   apps_df = pd.read_csv(config.APPS_LIST, index_col='appId')
   apps_df['appId'] = apps_df.index
   relevant_spyware_df = apps_df[apps_df['relevant']=='y']
   
   spyware_on_phone = relevant_spyware_df['appId'].isin(installed_apps)
   
   #print('-'*80)
   #print('Apps Installed on Phone:')
   #print('-'*80)
   #print(installed_apps)
   print('-'*80)
   print('Spyware Apps Detected on Phone')
   print('-'*80)
   #print(spyware_on_phone[spyware_on_phone == True])
   apps = spyware_on_phone[spyware_on_phone == True]

   for app in apps.index:
       print(relevant_spyware_df[relevant_spyware_df['appId']==app]['title'][0])
   #print(spyware_on_phone.value_counts())

'''
NEED Android Debug Bridge (adb) tool installed. Ensure your Android device is connected
through Developer Mode with USB Debugging enabled, and `adb devices` showing the device as
connected before running this scan function.
'''
def android_scan():
   installed_apps = subprocess.run(['adb', 'shell', 'pm', 'list', 'packages',
   '-f', '|', 'sed', '-e', "'s/.*=//'", '|', 'sed', "'s/\r//g'", '|', 'sort'],
   stdout=subprocess.PIPE)
  if (installed_apps.returncode != 0):
      print("Error running Android device scan. Is the Android Debug Bridge (adb) \
        'tool installed on this machine?")
      exit(1)
   installed_apps = installed_apps.stdout.decode()
   installed_apps = str(installed_apps).split('\n')

   # NOTE: or use DB!
   apps_df = pd.read_csv(config.APPS_LIST, index_col='appId')
   apps_df['appId'] = apps_df.index
   relevant_spyware_df = apps_df[apps_df['relevant']=='y']

   spyware_on_phone = relevant_spyware_df['appId'].isin(installed_apps)
   
   #print('-'*80)
   #print('Apps Installed on Phone:')
   #print('-'*80)
   #print(installed_apps)
   print('-'*80)
   print('Spyware Apps Detected on Phone')
   print('-'*80)
   #print(spyware_on_phone[spyware_on_phone == True])
   apps = spyware_on_phone[spyware_on_phone == True]

   for app in apps.index:
       print(relevant_spyware_df[relevant_spyware_df['appId']==app]['title'][0])
   #print(spyware_on_phone.value_counts())

def android_setup():
    subprocess.run(['adb', 'kill-server'])
    subprocess.run(['sudo', 'adb', 'start-server'])

if __name__ == "__main__":
    android_scan()
