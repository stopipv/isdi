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
        print("IOC repo not initialized properly")
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
try:
    with open(config.IOC_FILE, "r") as f:
        ioc = yaml.load(f, Loader=yaml.FullLoader)
        # print all indicators
        # print("Found " + str(len(apps)) + "  apps from the IOC stalkware indicators repostiory!")

except yaml.YAMLError as e:
    print("Error parsing YAML IOC file: {}".format(e))
    sys.exit(1)
except Exception as e:
    print("Other error reading IOC file: {}".format(e))
    sys.exit(1)

# get packages from every element of ioc dict
apps = [element["packages"] for element in ioc if "packages" in element]

# read app-flags.csv csv file
old_apps = []
try:
    with open(config.APP_FLAGS_FILE, "r") as f:
        reader = csv.reader(f)
        old_apps = set([row[0] for row in csv.reader(f)])
except csv.Error as e:
    print("Error parsing CSV app flags file: {}".format(e))
    sys.exit(1)
except Exception as e:
    print("Other error reading app flags file: {}".format(e))

new_app_count = 0
try:
    # append new apps to app-flags.csv for all ioc apps
    with open(config.APP_FLAGS_FILE, "a") as f:
        writer = csv.writer(f, lineterminator="\n")
        for element in ioc:
            if "packages" not in element:
                continue
            for app in element["packages"]:
                # if app is not in the csv file, add it
                if app not in old_apps:
                    new_app_count += 1
                    if "names" not in element:
                        element["names"] = []
                    names = " / ".join(element["names"])
                    writer.writerow([app, "playstore", "spyware", names])
except csv.Error as e:
    print("Error parsing CSV app flags file: {}".format(e))
    sys.exit(1)
except Exception as e:
    print("Other error reading app flags file: {}".format(e))
    sys.exit(1)

print("\nFound and added " + str(new_app_count) + " new apps!")

# verify that app-flags.csv is a valid csv file
# try:
#     with open(config.APP_FLAGS_FILE, "r") as f:
#         reader = csv.reader(f)
#         for row in reader:
#             if len(row) != 4:
#                 print("Error: app-flags.csv is not a valid csv file!")
#                 sys.exit(1)
# except csv.Error as e:
#     print("Error parsing CSV app flags file: {}".format(e))
#     sys.exit(1)
# except Exception as e:
#     print("Other error reading app flags file: {}".format(e))
#     sys.exit(1)
