import os
import yaml
import csv
import sys

# set current path to root
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# setting path
sys.path.append(os.getcwd())

import config

def requirements():
    # check if submodule is initialized
    if not os.path.exists(config.IOC_PATH) and not os.path.exists(config.IOC_FILE):
        print("Submodule not initialized properly")
        return False

    # check config.APP_FLAGS_FILE exists
    if not os.path.exists(config.APP_FLAGS_FILE):
        print("app-flags.csv not found")
        return False
    return True

# check requirements
if not requirements():
    print("Requirements not met. Exiting...")
    exit()

# parse ioc.yaml
ioc = {}
with open(config.IOC_FILE, "r") as f:
    ioc = yaml.load(f, Loader=yaml.FullLoader)

# get packages from every element of ioc dict
apps = [element['packages'] for element in ioc if 'packages' in element]

# print all indicators
print("Found " + str(len(apps)) + " apps from the IOC stalkware indicators repostiory!")

# read app-flags.csv csv file
old_apps = []
with open(config.APP_FLAGS_FILE, "r") as f:
    reader = csv.reader(f)
    for row in reader:
        old_apps.append(row[0])

new_app_count = 0

# append new apps to app-flags.csv for all ioc apps
with open(config.APP_FLAGS_FILE, "a") as f:
    writer = csv.writer(f)
    for element in ioc:
        if 'packages' not in element:
            continue
        for app in element['packages']:
            # if app is not in the csv file, add it
            if app not in old_apps:
                new_app_count += 1
                writer.writerow([app, "", "", element['name']])

print("\nFound and added " + str(new_app_count) + " new apps!")

