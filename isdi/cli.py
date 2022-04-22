#!/usr/bin/env python3
import logging
import logging.handlers as handlers
import webbrowser
from threading import Timer

import isdi.config
from .db import init_db
from isdi.web import app, sa

def open_browser(port):
    webbrowser.open('http://127.0.0.1:' + str(port), new=0, autoraise=True)

def main():
    import sys
    if 'TEST' in sys.argv[1:] or 'test' in sys.argv[1:]:
        print("Running in test mode.")
        isdi.config.set_test_mode(True)
        print("Checking mode = {}\nApp flags: {}\nSQL_DB: {}"
              .format(isdi.config.TEST, isdi.config.APP_FLAGS_FILE,
                      isdi.config.SQL_DB_PATH))
    print("TEST={}".format(isdi.config.TEST))
    init_db(app, sa, force=isdi.config.TEST)
    handler = handlers.RotatingFileHandler('logs/app.log', maxBytes=100000,
                                           backupCount=30)
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.ERROR)
    logger.addHandler(handler)
    port = 6200 if not isdi.config.TEST else 6202
    Timer(1, open_browser, [port]).start()
    app.run(host="0.0.0.0", port=port, debug=isdi.config.DEBUG, use_reloader= False)

if __name__ == "__main__":
    main()
