#import config
import re
# import shlex
import subprocess

'''
def add_to_error(*args):
    global ERROR_LOG
    m = '\n'.join(str(e) for e in args)
    print(m)
    ERROR_LOG.append(m)

def error():
    global ERROR_LOG
    e = ''
    if len(ERROR_LOG)>0:
        e, ERROR_LOG = ERROR_LOG[0], ERROR_LOG[1:]

        print("ERROR: {}".format(e))
    return e.replace("\n", "<br/>")
'''

# TODO: @sam the catch_err should only catch the os level errors, not
# application level errors. They should go to particular application specific
# handling.
def catch_err(p, cmd='', msg='', time=10):
    """TODO: Therer are two different types. homogenize them"""
    try:
        p.wait(time)
        print("Returncode: ", p.returncode)
        if p.returncode != 0:
            err_msg = p.stderr.read().decode('utf-8')
            m = ("[{}]: Error running {!r}. Error ({}): {}\n{}".format(
                'android', cmd, p.returncode, err_msg, msg
            ))
            if 'insufficient permissions for device: user in plugdev group' in err_msg:
                e = 'Error: Please set "USB For File Transfers" mode on your Android device.'
                print(e)
                return ""
            # config.add_to_error(m)
            return m
        else:
            s = p.stdout.read().decode()
            if (len(s) <= 100 and re.search('(?i)(fail|error)', s)) or \
                    'insufficient permissions for device: user in plugdev group; are your udev rules wrong?'\
                    in s:
                # config.add_to_error(s)
                return ""
            if 'insufficient permissions for device: user in plugdev group; are your udev rules wrong?'\
                    in s:
                print('Need USB for Charging.')
                return ""
            else:
                print(s)
                return s
    except Exception as ex:
        # config.add_to_error(ex)
        print("Exception>>>", ex)
        return ""


def run_command(cmd, **kwargs):
    _cmd = cmd.format(
        cli='adb', **kwargs
    )
    print(_cmd)
    if kwargs.get('nowait', False) or kwargs.get('NOWAIT', False):
        pid = subprocess.Popen(
            _cmd,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        ).pid
        return pid
    else:
        p = subprocess.Popen(
            _cmd,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        return p
