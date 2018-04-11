#!/usr/bin/env python3

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import marisa_trie
from collections import defaultdict, Counter
from pprint import pprint
import re
import sys
import plotly.plotly as py

SUMMARY_THRESHOLD=-1
APPS_PER_DEVICE = 'data/app_set_data-lno.txt.gz'
APPS_TRIE = 'data/apps-unique.marisa_trie'
regex_found = set()
SPY_REGEX = {
  "pos": re.compile(r'(?i)(spy|track|keylog|cheat|recorder|location|gps)')
  #"neg": re.compile(r'(?i)(anti.*(spy|track|keylog)|(spy|track|keylog).*remov[ea])'),
}

if len(sys.argv) < 2:
    SAMPLESIZE = 10000
else:
    SAMPLESIZE = int(sys.argv[1])
OFFSTORE = 'data/offstore_apks.csv'
ONSTORE_ANDROID = 'data/all_android_apps_5k_1.csv'
NUMCHECKS = 3
#NUM_USERS = 34616536 


# organized by check level and device ID.
checks = defaultdict(lambda: defaultdict(list))
# Initialize device counts 
for check in range(1,NUMCHECKS+1):
    checks['check'+str(check)+'summary']['devicecount'] = 0

print("Loading offstore and Android onstore blacklists...")
# Grab the offstore apps as a dataframe
offstore = pd.read_csv(OFFSTORE, index_col='appId')
offstore['appId'] = offstore.index

# Grab the full Play Store IPS apps as a dataframe
apps_full_df = pd.read_csv(ONSTORE_ANDROID, index_col='appId')
apps_full_df['appId'] = apps_full_df.index
android_onstore = apps_full_df[apps_full_df['relevant']=='y']
print("Blacklists loaded.")

# Grab the Android onstore apps as a dataframe
#android_onstore = pd.read_csv(ONSTORE_ANDROID, index_col='appId')
#if ('relevant' not in android_onstore.columns) or \
#    (android_onstore.relevant.count() < len(android_onstore)*0.5):
#    print("Relevant column is missing or unpopulated... recreating")
#    android_onstore['relevant'] = (android_onstore['ml_score'] > 0.4)\
#    .apply(lambda x: 'y' if x else 'n')
#android_onstore['appId'] = android_onstore.index

def load_simulations():
    df = pd.read_csv(APPS_PER_DEVICE, header=None, sep='\n', quotechar='"', \
	    compression='gzip', index_col=0, nrows=SAMPLESIZE)
    df['id'] = df.index
    #df = pd.read_csv(APPS_PER_DEVICE, header=None, sep='\n', quotechar='"', compression='gzip', index_col=0, nrows=samplesize)
    # NB: not very efficient? df is stored as one big CSV string on one column...
    # then extracted to a list here for an intersection.
    # ideally, df would intersect with blacklist df's directly.
    # not sure how to easily bring raw CSV into (str,Series) datatypes
    # when loading it into the dataframe.
    # TODO: can we serialize this nicer? pickle/feather? already tried.
    return df

# How many devices get flagged by each check?
def _updatedevicecount(check, deviceID):
    checks[check+'summary']['devicecount'] = checks[check+'summary']['devicecount'] + \
        (1 if len(checks[check][deviceID])>0 else 0)

#simulated_apps_trie = marisa_trie.Trie()
#simulated_apps_trie.load(APPS_TRIE)

def all_checks(df):
    SPY_REGEX = {
      "pos": re.compile(r'(?i)(spy|track|keylog|cheat|recorder|location|gps)')
      #"neg": re.compile(r'(?i)(anti.*(spy|track|keylog)|(spy|track|keylog).*remov[ea])'),
    }
    for x in range(SAMPLESIZE):
        ID, *deviceapps = df['id'][x].split(',')
        checks['summary']['appsperdevice'].append(len(deviceapps))

        offstore_isn = offstore['appId'].isin(deviceapps)
        offstore_check = offstore_isn[offstore_isn == True]

        android_onstore_isn = android_onstore['appId'].isin(deviceapps)
        android_onstore_check = android_onstore_isn[android_onstore_isn == True]

        #regex1isn = set(simulated_apps_trie.keys('track')).intersection(deviceapps)
        regex1isn = set(filter(SPY_REGEX['pos'].match, deviceapps))
        regex_found.update(regex1isn)

        checks['check1'][ID] = set(offstore_check.index)
        checks['check2'][ID] = checks['check1'][ID].union(set(android_onstore_check.index))
        checks['check3'][ID] = checks['check2'][ID].union(regex1isn)

        #print(checks['check1'][ID])
        #print(checks['check2'][ID])
        #print(checks['check3'][ID])

        for check in range(1,NUMCHECKS+1):
            _updatedevicecount('check'+str(check), ID)

def regex_checks(df):
    for x in range(SAMPLESIZE):
        ID, *deviceapps = df['id'][x].split(',')
        checks['summary']['appsperdevice'].append(len(deviceapps))

        #regex1isn = set(simulated_apps_trie.keys('spy')).intersection(deviceapps)
        checks['check3'][ID] = set(filter(SPY_REGEX['pos'].match, deviceapps))
        regex_found.update(checks['check3'][ID])
        _updatedevicecount('check3', ID)

# How many apps get flagged per device? 
def _summarize(check):
    for deviceID in checks[check]:
        numflaggedapps = len(checks[check][deviceID])
        checks[check+'summary']['appsflaggedperdevice'].append(numflaggedapps)

        # maybe take this 'if' out of loop and unroll
        if numflaggedapps>SUMMARY_THRESHOLD: # TODO: param for this
            checks[check+'summary']['deviceIDsflagged'].append(('Phone '+str(deviceID), numflaggedapps))
            #print("Adding "+str(deviceID)+" for "+str(checks[check][deviceID]))
    try:
        checks[check+'summary']['avgflaggedperdevice'] = sum(checks[check+'summary']['appsflaggedperdevice']) \
                / float(len(checks[check+'summary']['appsflaggedperdevice']))
    except ZeroDivisionError:
        checks[check+'summary']['avgflaggedperdevice'] = 0.0

    try:
        checks[check+'summary']['percentflagged'] = checks[check+'summary']['devicecount'] \
            / float(len(checks[check].keys()))
    except ZeroDivisionError:
        checks[check+'summary']['percentflagged'] = 0.0

    try:
        checks['summary']['avgappsperdevice'] = sum(checks['summary']['appsperdevice']) \
                / float(len(checks['summary']['appsperdevice']))
    except ZeroDivisionError:
        checks[check+'summary']['avgappsperdevice'] = 0.0
   
def print_summary_report():
    print('='*80)
    print("Field Study Simulation Summary")
    print('='*80)
    print("Check levels:\nCheck 1\t\tOffstore Apps\n"\
            "Check 2\t\tOffstore Apps AND Play Store Apps\n"\
            "Check 3\t\tOffstore Apps AND Play Store Apps AND Regexes:\n\t\t"\
            "'spy|track|keylog|cheat|recorder|location|gps'\n")
    print('='*80)
    print("NUMBER OF DEVICES FLAGGED BY CHECK:\n")
    for check in range(1,NUMCHECKS+1):
        print('-'*80)
        print('\nCheck '+str(check)+' (cumulative with previous checks):\n')
        if check>1:
            print("  This check introduced "+str(checks['check'+str(check)+'summary']['devicecount']-\
                    checks['check'+str(check-1)+'summary']['devicecount'])+\
                    " new flagged devices")
        #print('Device IDs flagged with at least '+str(SUMMARY_THRESHOLD+1)+' app(s) "(ID, number of flagged apps)":')
        devicesflagged = sorted(checks['check'+str(check)+'summary']['deviceIDsflagged'], reverse=True, key=lambda x: x[1])
        print("\nGenerating Histogram...")
        flagcounts = [x[1] for x in devicesflagged]

        hist = Counter(flagcounts)
        percentiles = {}
        #for k,v in hist.most_common():
        #    print(str(k)+" app(s) flagged on "+str(v)+"/"+str(SAMPLESIZE)+" devices ({0:.2f}%).".format(100*(v/float(SAMPLESIZE))))
        counts_per_app_num = sorted(hist.items(), reverse=True, key=lambda x: x[0])
        for i in range(len(counts_per_app_num)):
            k,v = counts_per_app_num[i]
            if i > 0:
                percentiles[i] = v + percentiles[i-1]
            else:
                percentiles[i] = int(v)
            #print(str(k)+" app(s) flagged on "+str(v)+"/"+str(SAMPLESIZE)+\
            #        " devices ({0:.2f}%).".format(100*(v/float(SAMPLESIZE))))
            print("% devices with "+str(k)+" apps:\t"+\
                    str(v)+"/"+str(SAMPLESIZE)+\
                    " ({0:.4f}%)"\
                    .format(100*(v/float(SAMPLESIZE)))+\
                    "\t % with >= "+str(k)+" apps: "+str(percentiles[i])+"/"+str(SAMPLESIZE)+\
                    " ({0:.4f}%)"\
                    .format(100*(percentiles[i]/float(SAMPLESIZE))))
        cdf_df = pd.Series(flagcounts)
        bn = sorted(set([x[0] for x in counts_per_app_num]))
        cdf = cdf_df.hist(cumulative=True, density=True, bins=bn, histtype='bar')
        
        def _get_cdf(ax):
            n_cdf,bins_cdf = [],[]
            for rect in ax.patches:
                ((x0, y0), (x1, y1)) = rect.get_bbox().get_points()
                n_cdf.append(y1-y0)
                bins_cdf.append(x0) # left edge of each bin
            bins_cdf.append(x1) # also get right edge of last bin
            return n_cdf,bins_cdf
        n,bins = _get_cdf(cdf)
        print("\nCumDist\t\t\tNumber of IPS Apps or less")
        for i in range(len(n)):
            print(str(n[i])+"\t"+str(bins[i]))
        plt.title("CDF of IPS Apps found on sample of "+str("{:,}".format(SAMPLESIZE))\
                +" phones (check "+str(check)+")")
        plt.xlabel("Number of IPS Apps Flagged")
        plt.ylabel("CumDist of IPS Apps or less")
        #plt.show()
        plt.savefig('cdfSample'+str(SAMPLESIZE)+'check'+str(check)+'.png', bbox_inches='tight')
        plt.clf()

        plt.hist(flagcounts, density=None, bins=bn)
        plt.title("Histogram of IPS Apps found on sample of "+str("{:,}".format(SAMPLESIZE))\
                +" phones (check "+str(check)+")")
        plt.xlabel("IPS Apps Flagged")
        plt.ylabel("Number of Devices Affected")
        fig = plt.gcf()
        #plot_url = py.plot_mpl(fig, filename='mpl-basic-histogram')
        #plt.show()
        plt.savefig('histogramSample'+str(SAMPLESIZE)+'check'+str(check)+'.png', bbox_inches='tight')
        plt.clf()

#        for k,v in hist.most_common():
#            if int(k) > 1:
#                percentiles[k] = v + percentiles[int(k)-1]
#            else:
#                percentiles[k] = int(v)
#            print(str(k)+" app(s) flagged on "+str(v)+"/"+str(SAMPLESIZE)+" devices ({0:.2f}%).".format(100*(v/float(SAMPLESIZE))))
#            print("\t>= ({0:.2f}%).".format(100*(percentiles[k]/float(SAMPLESIZE))))

            #print(str(k)+" apps flagged on "+str(v)+"/"+str(SAMPLESIZE)+" devices ({0:.2f}"+str(100*(v/float(SAMPLESIZE)))+"%).")
    print('='*80)
    print("AVERAGE NUMBER OF APPS FLAGGED PER DEVICE:\n")
    for check in range(1,NUMCHECKS+1):
        print('Check '+str(check)+': '+str(checks['check'+str(check)+'summary']['avgflaggedperdevice']))

        if check>1:
            print("  This check introduced "+str(checks['check'+str(check)+'summary']['avgflaggedperdevice']-\
                    checks['check'+str(check-1)+'summary']['avgflaggedperdevice'])+\
                    " average flagged apps")
    print('Average apps installed per phone: '+str(checks['summary']['avgappsperdevice']))
    print('='*80)
    print("Unique apps found from regex searching in check 3 (are there any false positives to prune?):\n")
    pprint(regex_found)
    print('='*80)
    

if __name__ == "__main__":
    print("Loading "+str(SAMPLESIZE)+" simulated phones into dataframe...")
    df = load_simulations()
    print("Loaded simulations into dataframe.")

    #print("Running check level 3 on "+str(SAMPLESIZE)+" phones...")
    #regex_checks(df)
    print("Running check levels 1, 2, and 3 on "+str(SAMPLESIZE)+" phones...")
    all_checks(df)
    print("Summarizing checks...")
    _summarize('check1')
    _summarize('check2')
    _summarize('check3')
    print("Checks summarized.")
    print_summary_report()
