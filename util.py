import os
from collections import defaultdict

def prefix(pre, a):
    if not pre:
        return a
    return os.path.commonprefix([pre, a])

def common_prefix_set(a, prefix_criteria=lambda x: len(x)>=5):
    """Finds the possible set of common prefixes in the set
    a -> set, prefix_crietria is a funciton that describes what is allowed as a prefix.
    outputs a set. 
    """
    a = sorted(a)
    pre = ''
    ret = defaultdict(list)
    for i, x in enumerate(a):
        prfx = prefix(pre, x)
        if prefix_criteria(prfx):
            ret[prfx].append(x)
            pre = prfx
        else:
            pre = x
    return ret


if __name__ == "__main__":
    print(common_prefix_set('''appinventor.ai_thewolfman1984.Spytxt_listen_in
com.ITU.ahmedsohail.spyapp
com.ah.ispyoo.config
com.ah.ispyoo.main
com.ah.ispyoo.sync.ambient
com.ah.ispyoo.sync.location
com.antispycell.free
com.aspy.freephonetracker
com.aspy.freesmstracker
com.bettertomorrowapps.spyyourlovefree
com.bettertomorrowapps.spyyourlovefree.ServicePeriodicLocationCheck
com.bettertomorrowapps.spyyourlovefree.ServicePeriodicSynchronize
com.bettertomorrowapps.spyyourlovefree.ServiceSentSms
com.cornell.AntiSpyware
com.example.hadas.cornell_anti_spyware
com.hellospy.system
com.ispyoo.android.activity.MainActivity
com.ispyoo.common.admin.DeviceAdmin
com.ispyoo.common.calltracker.receiver.CallReceiver
com.ispyoo.common.calltracker.receiver.TrackerService
com.ispyoo.common.monitor.AndroidSchedulingService
com.ispyoo.common.monitor.AndroidSyncBroadcastReceiver
com.ispyoo.common.monitor.AndroidWatchdogService
com.ispyoo.common.monitor.BootBroadcastReceiver
com.ispyoo.common.monitor.NetworkChangeReceiver
com.ispyoo.common.monitor.OutGoingCallReceiver
com.ispyoo.common.monitor.SpyApp
com.ispyoo.common.monitor.UserPresentBroadcastReceiver
com.jalle.ispyserver
com.mxspy
com.mxspy.RegistrationIntentService
com.trackerspy'''.split()))
