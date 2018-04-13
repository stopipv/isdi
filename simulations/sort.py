import sys, os
from collections import Counter
import json
 
def uniq(fname):
    d = {}
    with open(fname) as f:
        # d = {l.strip() for l in f if not l.rstrip().isdigit()}
        d = Counter(l.strip() for l in f if not l.rstrip().isdigit())
    return d
 
 
 
if __name__ == "__main__":
    # print ('\n'.join(uniq(sys.argv[1])))
    print('appId,cnt')
    for k,v in uniq(sys.argv[1]).items():
        print('{},{}'.format(k,v))
