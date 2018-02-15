from appJar import gui
from subprocess import Popen
from subprocess import PIPE
import pandas as pd
import os

root_folder = os.path.join(os.path.dirname(os.path.abspath(__name__)), '../')
# TODO: Change this to final ML output
SPY_APP_CSV = os.path.join(root_folder, 'data/crawl_random_1000_apps.csv')


def find_spywares():
    res = Popen(
        "adb shell pm list packages -f", stdout=PIPE, shell=True
    ).stdout.read().decode('utf-8')
    pkgs = res.split()
    if '' in pkgs:
        pkgs.remove('')

    for i in range(len(pkgs)):
        pkgs[i] = pkgs[i].rsplit("=", 1)[1]

    spyware_pkgs = pd.read_csv(SPY_APP_CSV, index_col='appId')
    spyware_found = set(spyware_pkgs[spyware_pkgs.relevant=='y'].index) \
                    & set(pkgs)
    return spyware_found


def uninstall_package(button):
    with gui("Anti-IPS: Stop intiimate partner surveillance") as app:
        package = app.getListBox("list")[0]
        res = Popen("adb uninstall " + package, stdout=PIPE, shell=True)
        res = res.stdout.read()
        if res == "Success\r\r\n":
            app.removeListItem("list", package)
        app.infoBox("uninstall_res", res)


def render_gui(spyware_list):
    with gui("Anti-IPS: Stop intiimate partner surveillance") as app:
        app.setGeometry(500, 500)
        app.setStretch("both")
        app.setSticky("nesw")

        app.addListBox("list", spyware_list, 1, 0)
        app.addEmptyMessage("description", 1, 1)

        tools = ['DELETE']
        app.addToolbar(tools, uninstall_package, findIcon=True)


def main():
    spyware_list = find_spywares()
    print("Spyware found", '\n'.join(spyware_list))
    # if len(sys.argv)>1 and sys.argv[1] == '-gui':
    render_gui(spyware_list)


if __name__ == "__main__":
    main()
