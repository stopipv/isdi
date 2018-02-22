from appJar import gui
from phone_scanner import AndroidScan, IosScan
import config

app = gui(config.TITLE) 

def uninstall_package(button):
    package = app.getListBox("list")[0]
    res = Popen("adb uninstall " + package, stdout=PIPE, shell=True)
    res = res.stdout.read()
    if res == "Success\r\r\n":
        app.removeListItem("list", package)
    app.infoBox("uninstall_res", res)


def scan(button):
    if button.lower() == 'android':
        sc = AndroidScan()
    elif button.lower() == 'ios':
        sc = IosScan()
    spyapps = sc.find_spyapps()
    app.updateListBox('spyware_label', spyapps)
    return spyapps


    
def render_gui():
    # super simple "gui"... it's very 90's and outdated! 
    # TODO: use something better, like meteor (JS), instead.
    app.setGeometry(500, 500)
    app.setStretch("both")
    app.setSticky("nsew")
    app.addLabel("Spyware", "Spyware found on your device:")
    # app.addEmptyMessage("Spyware Found on Device", 1, 1)

    #  TODO
    # tools = ['DELETE']
    # app.addToolbar(tools, uninstall_package, findIcon=True)

    app.addButtons(["Android", "Ios"], scan)
    app.addListBox("spyware_label", [])

    app.go()

def main():
    render_gui()


if __name__ == "__main__":
    main()
