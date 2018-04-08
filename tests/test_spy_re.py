import re
from blacklist import _regex_blacklist
test_list = [
    ('com.spyware.app', True),
    ('com.antispyware.app', False),
    ('com.spyware-anti.app', True),
    ('com.something.Anti-Spyware.com', False),
    ('com.something.Anti-something-Spyware.com', False),
    ('com.-something-Spyware.com', True),
    ('com.Trackware.com', True),
    ('com.AntiTrackware.com', False),
    ('com.spyware-removal.com', False),
]
# regex_ = r'(?i)(?!.*anti)[\-\s]*(spy|track|keylog)'
# regex_ = r'(?i)((?!.*anti)[\-\s]*.*(spy|track)).*'
regex_pos = r'(?i)(spy|track|keylog)'
regex_neg = r'(?i)(anti.*(spy|track|keylog)|(spy|track|keylog).*remov[ea])'


def test_regex():
    for a, m in test_list:
        assert (re.search(regex_pos, a) and not re.search(regex_neg, a)) == m


def test_blacklist():
    for a, m in test_list:
        assert (_regex_blacklist(a) != []) == m
