#!/usr/bin/env python3

from appJar import gui
import subprocess
import pandas as pd
import config
import time

'''
NEED https://github.com/imkira/mobiledevice installed (`brew install mobiledevice` or build from source).
'''
def ios_scan():
   installed_apps = subprocess.run(['mobiledevice', 'list_apps'], stdout=subprocess.PIPE) 
   if (installed_apps.returncode != 0):
       print("Error running iOS device scan. Is the 'https://github.com/imkira/mobiledevice" \
            "code installed on this Mac?")
       exit(1)
   installed_apps = installed_apps.stdout
   installed_apps = installed_apps.split('\n').tolist()

   # NB: or use DB!
   apps_df = pd.read_csv(config.APPS_LIST, index_col='appId')
   apps_df['appId'] = apps_df.index
   relevant_spyware_df = apps_df[apps_df['relevant']=='y']
   
   spyware_on_phone = relevant_spyware_df['appId'].isin(installed_apps)
   
   print('-'*80)
   print('Spyware Apps Detected on Phone')
   print('-'*80)
   apps = spyware_on_phone[spyware_on_phone == True]

   relevant_spyware = []
   for app in apps.index:
       spyware_app = relevant_spyware_df[relevant_spyware_df['appId']==app]['title'][0]
       relevant_spyware.append(spyware_app)
   return relevant_spyware

def _dev_ios_scan():
   installed_apps = open(config.TEST_SCAN_RESULTS, 'r').read().splitlines()

   # NB: or use DB!
   apps_df = pd.read_csv(config.APPS_LIST, index_col='appId')
   apps_df['appId'] = apps_df.index
   relevant_spyware_df = apps_df[apps_df['relevant']=='y']
   
   spyware_on_phone = relevant_spyware_df['appId'].isin(installed_apps)
   
   print('-'*80)
   print('Spyware Apps Detected on Phone')
   print('-'*80)
   apps = spyware_on_phone[spyware_on_phone == True]

   relevant_spyware = []
   for app in apps.index:
       spyware_app = relevant_spyware_df[relevant_spyware_df['appId']==app]['title'][0]
       relevant_spyware.append(spyware_app)
   return relevant_spyware

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
      print("Error running Android device scan. Is the Android Debug Bridge (adb)" \
        "tool installed on this machine?")
      try:
          print("Attempting to start Debug Server...")
          android_setup()
          print("Android Debug Server is online! Re-run the scan tool!")
      except Exception as e:
          print(e)
      exit(1)
   installed_apps = installed_apps.stdout.decode()
   installed_apps = str(installed_apps).split('\n')

   # NOTE: or use DB!
   apps_df = pd.read_csv(config.APPS_LIST, index_col='appId')
   apps_df['appId'] = apps_df.index
   relevant_spyware_df = apps_df[apps_df['relevant']=='y']

   spyware_on_phone = relevant_spyware_df['appId'].isin(installed_apps)
   
   print('-'*80)
   print('Spyware Apps Detected on Phone')
   print('-'*80)
   apps = spyware_on_phone[spyware_on_phone == True]

   relevant_spyware = []
   for app in apps.index:
       spyware_app = relevant_spyware_df[relevant_spyware_df['appId']==app]['title'][0]
       relevant_spyware.append(spyware_app)
   return relevant_spyware

def android_setup():
    subprocess.call(['/usr/bin/adb', 'kill-server'])
    subprocess.call(['sudo', '/usr/bin/adb', 'start-server'])

def render_gui(spyware_list):
    # super simple "gui"... it's very 90's and outdated! 
    # TODO: use something better, like meteor (JS), instead.
    with gui("Anti-IPS: Stop intiimate partner surveillance") as app:
        app.setSize(700, 700)
        app.setStretch("both")
        app.setSticky("new")
        app.setBg("#b31b1b")
        app.setFont(22)
        app.addLabel("Spyware", "Spyware found on your device:")
        app.addListBox("spyware_label", spyware_list, 1, 0)
        app.addEmptyMessage("Spyware Found on Device", 1, 1)

if __name__ == "__main__":
    spyware = android_scan()
    render_gui(spyware)
