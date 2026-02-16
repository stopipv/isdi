from collections import defaultdict
import pandas as pd
from isdi.config import get_config
import sqlite3
import json
import os

config = get_config()


class ISDiSummary:
    checkbox_hists = defaultdict(tuple)

    def __init__(self, db_path):
        assert os.path.isfile(db_path), "ISDi db path {!r} was not found.".format(
            db_path
        )
        self.app_info_conn = sqlite3.connect(db_path, check_same_thread=False)
        self.df = pd.read_sql(
            "select * from clients_notes", self.app_info_conn
        )  # , params=(,))

    def hist_checkbox(self, cbox_col, hreadable=None):
        hist = defaultdict(int)
        multibox_counts = defaultdict(int)
        for idx, client in self.df.iterrows():
            checkboxes = json.loads("".join(client[cbox_col]))
            multibox_counts[len(checkboxes)] += 1
            for cbox in checkboxes:
                # human readable dict passed for coded checkboxes
                if hreadable:
                    hist[hreadable[cbox]] += 1
                else:
                    hist[cbox] += 1
        self.checkbox_hists[cbox_col] = (hist, multibox_counts)
        return hist, multibox_counts

    def __str__(self):
        rep = ["ISDi data summary"]
        rep.append("-" * 80)
        if self.devices_scanned:
            rep.append(
                "Number of devices scanned (iOS or Android): {}".format(
                    self.devices_scanned
                )
            )
        for cbox_col, hist in self.checkbox_hists.items():
            rep.append("")
            c = cbox_col.replace("_", " ")
            rep.append("{}:".format(c.title()))
            rep.append("-" * 80)
            for k, v in hist[0].items():
                rep.append(str(k) + ": " + str(v))

            rep.append("")
            rep.append("Overlap (Multiple boxes checked):")
            for k, v in sorted(hist[1].items()):
                rep.append(
                    "Number of clients with " + str(k) + " " + str(c) + ": " + str(v)
                )
        return "\n".join(rep)

    def devices_scanned(self):
        self.devices_scanned = int(
            self.app_info_conn.cursor()
            .execute("select count(distinct(serial)) from scan_res;")
            .fetchall()[0][0]
        )
        return self.devices_scanned


if __name__ == "__main__":
    # TODO: better integrate with tuples used in server? could pull these mappings from config here and in server
    hreadable_vulns = {
        "none": "None",
        "shared plan": "Shared plan / abuser pays for plan",
        "password:observed compromise": "Observed compromise (e.g., client reports abuser shoulder-surfed, or told them password)",
        "password:guessable": "Surfaced guessable passwords",
        "cloud:stored passwords": "Stored passwords in app that is synced to cloud (e.g., passwords written in Notes and backed up)",
        "cloud:passwords synced/password manager": "Password syncing (e.g., iCloud Keychain)",
        "unknown trusted device": "Found an account with an active login from a device not under client's control; trusted device",
        "ISDi:found dual-use apps/spyware": "ISDi found dual-use apps/spyware",
        "ISDi:false positive": "ISDi false positive as confirmed by client",
        "browser extension": "Browser extension potential spyware",
        "desktop potential spyware": "Desktop application potential spyware",
    }

    hreadable_concerns = {
        "spyware": "Worried about spyware/tracking",
        "hacked": "Abuser hacked accounts or knows secrets",
        "location": "Worried abuser was tracking their location",
        "glitchy": "Phone is glitchy",
        "unknown_calls": "Abuser calls/texts from unknown numbers",
        "social_media": "Social media concerns (e.g., fake accounts, harassment)",
        "child_devices": "Concerns about child device(s), e.g., unknown apps",
        "financial_concerns": "Financial concerns, e.g., fraud, money missing from bank account",
        "curious": "Curious and want to learn about privacy",
        "sms": "SMS texts",
        "other": "Other chief concern (write in next question)",
    }

    DB_PATH = config.SQL_DB_PATH.replace("sqlite:///", "")
    summ = ISDiSummary(DB_PATH)
    summ.hist_checkbox("vulnerabilities", hreadable_vulns)
    summ.hist_checkbox("chief_concerns", hreadable_concerns)
    summ.devices_scanned()
    print(summ)
