import re
import sys

whitelist = [
    r"com.google.*",
    r"com.whatsap.*",
    r"com.android.",
    r"com.samsung.",
    r"com.sec.",
]


def check(apk):
    for w in whitelist:
        if re.match(w, apk):
            return 1
    return 0


print(check(sys.argv[1]))
