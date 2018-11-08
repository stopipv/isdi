## Android ADB helps
1. `adb shell settings list [global|system|secure]` Gives a details of system settings.
2. `pm clear com.android.settings` might remove the developer settings. Need to check.
3. `pm dump <appid>` will output a huge dump of information, which might be useful. For example, we can get the installt time,
   `firstInstallTime=2018-02-23 19:46:51` and the `installerPackageName` from this dump.
4. TODO: How to find whether an app is installed outside play store?


Other interesting services, but may have PII
* backup: (where the account backing up the data)
* batterystats: (which app is using how much of battery)
* content: (have data about syncing, which app is syncing what, how frequently)
* user

I don't know following services:
* country_detector??
* lock_settings:

Definitely has PII
* account, user
* trust

| Service | What info is there |  What is useful|  PII |
|:--------|:-------------------|----------------|----------|
| `account` | The account information | Account {name=\<email\>, type=com.google} | Email, name |
| `activity` | Intent, broadcast, receiver, content providers, services, permissions, recents, activities, process, alarm | Not sure, too much information | Probably none |
| `appops` | App operations provided by the processes, uids, and packages. | Not sure. Some app operations might be useful. | No |
| `backup` | Which apps are backedup, backup queue, destination account |   | Email, account |
| `batterystats` | Statistics about which process is consuming how much data. | App battery consumption | Email (some line contain email of the main account holder) |
| `content` | The sync details | Which process is syncing data back. (Mostly this contain google apps). | Email, and account information |
| `cpuinfo` | Normal version does not have much information. Need to check &quot;cpuinfo detailed&quot;. | Nothing useful | None |
| `dbinfo` | All the primary storage operation commands. Sqlite commands, but no values in the log | Might be useful to know which db operations are frequently done by a process. | Possibly none |
| `device_policy` | Device admins, and the policies set by them. (Can also be found from lgmdm\_device\_policy\_manager) | Device admins, often spyware want themselves to be set as device admin, this might be useful to find them. | None |
| `deviceidle` | The apps that want to be whitelisted from device idle. | Not useful | None |
| `graphicsstats` | Which apps has used how much graphics processor. | Might be useful to find if spyware uses graphics processor often or not. | None |
| `jobscheduler` | Which apps has their jobs running (in the background) | Might be interesting to find the apps that have background activity. | None |
| `location` | Which process asks for location info | Super useful. | none |
| `media.camera` | If any process is accessing the camera or not. | Useful, to see if any app is accessing the camera in the background? | None |
| `meminfo` | Memory used by each app | Useful, to see which app using how much memory (RAM) | None |
| `mount` | Info about secondary storage writes | Useful, will tell about where does the spyware write their information. | None |
| `netpolicy` | Which apps are allowed to transfer data in the background etc. | Useful | None |
| `netstas` | Data transferred using a WiFi. The details version return per app stats | Very hard to understand the log, might not be useful. Rather, **&quot;**** adb shell cat /proc/net/xt\_qtaguid/stats ****&quot;** is much cleaner. | None |
| `notification` | Notification information | Need to check more, but might be useful | None |
| `pacakge` | The information about the packages | Most useful, the package metadata, permissions , etc. | None |
| `power` | Power state | Not useful |   |
| `procstats` | Summary of process stats (some history too). | Useful, need to look more, but seem to have the process memory usage, cpu usage, etc. | None |
| `sensorservice` | Information about the sensor informations | Interesting but probably not useful | none |
| `themeicon` | Not quite sure, but seems to have list of apps with icon. | Need to check more | none |
| `usagestats` | Stat about app usage. | Useful, to get which app run how much time in the background and foreground. | none |
|   |   |   |   |

~I (Rahul) was deciding ~decided~ to dump the whole system information of the device. `adb
shell dumpsys`. This might contain PII, so the data need to be cleaned before
further processing.~ (Not doing)

##### Other programs for accessing iOS device via USB

Must be using a computer running macOS:
`brew install mobiledevice` on the Mac (or build from
https://github.com/imkira/mobiledevice).
Keep the phone unlocked and "trust this computer" when prompted.

iOS devices can be accessed from Linux using `ideviceinstaller` (Mainted by
Ubuntu developers).  Needs some dependencies that are not specified in the
file. Possibly `libusbmuxd-dev`. (I have to check). **Update**: The library is
not dependable, and does not work most of the time.

There are many programs that I found while searching for ways to
communitcate to a iOS device via commandline.
1. [`mobiledevice`](https://github.com/imkira/mobiledevice) - Works sometimes for some version of OSX and iOS
2. [`pymobiledevice`](https://github.com/iOSForensics/pymobiledevice/) - Does not work at all
3. [`MobileDevice`](https://github.com/mountainstorm/MobileDevice/) - Most reliable I could find (though testedo only on one MAC and one iPhone.)
4. ['ios-deploy'](https://github.com/AtomicGameEngine/ios-deploy) -
A `nodjs` package. (Was originally forked from https://github.com/phildrip/fruitstrap,
but much better now. **Using this.**)



## Code Architecture  
The code is getting big enough to fall back to MVC architecture. (20180405)
So, the components are scanning services for each type of devices - `phone_scanner`. 
There should be a view section which is `server.py`.  Finally there should be the logic
for connecting components with views via models. 


ideviceinfo | grep -i Internationalmobile
