#!/usr/bin/env python3
import logging
import logging.handlers as handlers
import webbrowser
from threading import Timer

import config
from db import init_db
from web import app, sa

def open_browser():
    webbrowser.open('http://127.0.0.1:' + str(PORT), new=0, autoraise=True)

if __name__ == "__main__":
    import sys
    # if 'TEST' in sys.argv[1:] or 'test' in sys.argv[1:]:
    #     print("Running in test mode.")
    #     config.set_test_mode(True)
    #     print("Checking mode = {}\nApp flags: {}\nSQL_DB: {}"
    #           .format(config.TEST, config.APP_FLAGS_FILE,
    #                   config.SQL_DB_PATH))
    print("TEST={}".format(config.TEST))
    init_db(app, sa, force=config.TEST)
    handler = handlers.RotatingFileHandler('logs/app.log', maxBytes=100000, 
                                           backupCount=30)
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.ERROR)
    logger.addHandler(handler)
    PORT = 6200 if not config.TEST else 6202
    Timer(1, open_browser).start()
    app.run(host="0.0.0.0", port=PORT, debug=config.DEBUG, use_reloader= False)
