"""Run external device tools (adb, pymobiledevice3).

Commands are always passed as argv lists and never through a shell, so
values that come from the device or from HTTP requests (serials, app IDs)
cannot be interpreted as shell syntax.
"""

import logging
import subprocess
from typing import Mapping, Optional, Sequence


def run(
    argv: Sequence[str],
    timeout: float = 60,
    env: Optional[Mapping[str, str]] = None,
    text: bool = True,
) -> subprocess.CompletedProcess:
    """Run argv and return the CompletedProcess.

    Never raises for a missing binary or a timeout; those come back with a
    non-zero returncode (127 and -1) and the reason in stderr.
    """
    argv = [str(a) for a in argv]
    logging.debug("run: %r", argv)
    kwargs = dict(capture_output=True, timeout=timeout, env=env)
    if text:
        kwargs.update(text=True, errors="replace")
    try:
        return subprocess.run(argv, **kwargs)
    except subprocess.TimeoutExpired:
        logging.warning("Command timed out after %ss: %r", timeout, argv)
        return subprocess.CompletedProcess(argv, -1, "" if text else b"", "timeout")
    except OSError as e:
        logging.error("Could not run %r: %s", argv, e)
        return subprocess.CompletedProcess(argv, 127, "" if text else b"", str(e))


def output(argv: Sequence[str], **kwargs) -> str:
    """Run argv and return stdout, or "" if the command failed."""
    p = run(argv, **kwargs)
    if p.returncode != 0:
        logging.error(
            "Error running %r. returncode=%s stderr=%s", argv, p.returncode, p.stderr
        )
        if "insufficient permissions for device" in (p.stderr or ""):
            logging.error('Please set "USB for File Transfers" mode on the device.')
        return ""
    return p.stdout
