import config
import re
import os
import shlex
import subprocess

def catch_err(p, cmd='', msg='', time=10):
        """TODO: Therer are two different types. homogenize them"""
        try:
            p.wait(time)
            print("Returncode: ", p.returncode)
            if p.returncode != 0:
                m = ("[{}]: Error running {!r}. Error ({}): {}\n{}".format(
                    'android', cmd, p.returncode, p.stderr.read(), msg
                ))
                config.add_to_error(m)
                return -1
            else:
                s = p.stdout.read().decode()
                if (len(s) <= 100 and re.search('(?i)(fail|error)', s)) or \
                        'insufficient permissions for device: user in plugdev group; are your udev rules wrong?'\
                        in s:
                    config.add_to_error(s)
                    return -1
                else:
                    return s
        except Exception as ex:
            config.add_to_error(ex)
            print("Exception>>>", ex)
            return -1

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
