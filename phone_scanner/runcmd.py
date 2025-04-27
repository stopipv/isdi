import re
from config import logging

# import shlex
import subprocess

"""
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
"""


# TODO: @sam the catch_err should only catch the os level errors, not
# application level errors. They should go to particular application specific
# handling.
def catch_err(
    p: subprocess.Popen[bytes], cmd="", msg="", time=10, large_output=False
) -> str:
    """TODO: Therer are two different types. homogenize them"""
    try:
        large_output_var = b""
        if large_output:
            if p.stdout:
                for line in p.stdout:
                    large_output_var += line

        p.wait(time)
        print("Returncode: ", p.returncode)
        if p.returncode != 0:

            if p.stderr:
                err_msg = p.stderr.read().decode("utf-8")
            else:
                err_msg = (
                    "stderr was none. This may indicate large issues with process."
                )

            m = "[{}]: Error running {!r}. Error ({}): {}\n{}".format(
                "android", cmd, p.returncode, err_msg, msg
            )
            print(cmd, p.returncode, err_msg, msg)
            if "insufficient permissions for device: user in plugdev group" in err_msg:
                e = 'Error: Please set "USB For File Transfers" mode on your Android device.'
                print(e)
                return ""
            # config.add_to_error(m)
            return m
        else:
            if large_output:
                s = large_output_var.decode()
            else:
                if p.stdout:
                    s = p.stdout.read().decode()
                else:
                    return ""

            if (
                (len(s) <= 100 and re.search("(?i)(fail|error)", s))
                or "insufficient permissions for device: user in plugdev group; are your udev rules wrong?"
                in s
            ):
                # config.add_to_error(s)
                return ""
            if (
                "insufficient permissions for device: user in plugdev group; are your udev rules wrong?"
                in s
            ):
                logging.error("Need USB for Charging.")
                return ""
            else:
                logging.error(s)
                return s
    except Exception as ex:
        # config.add_to_error(ex)
        logging.error("Exception>>>", ex)
        return ""


def run_command(cmd: str, **kwargs) -> subprocess.Popen[bytes]:
    """
    Run a command in a subprocess.
    Args:
        cmd (str): The command to run.
        **kwargs: Additional keyword arguments to format the command.
    Returns:
        subprocess.Popen: The process object.
    """
    _cmd = cmd.format(**kwargs)
    logging.debug(_cmd)
    p = subprocess.Popen(
        _cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
    )
    if not (kwargs.get("nowait", False) or kwargs.get("NOWAIT", False)):
        p.wait()
        if p.returncode != 0:
            logging.error("Error running command: {_cmd}. p.returncode: {p.returncode}\n"
                         "p.stderr = {p.stderr.read().decode()}")
        else:
            print(f"Command {_cmd!r} executed successfully.")
    return p
