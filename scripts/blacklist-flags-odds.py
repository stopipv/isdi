#!/usr/bin/env python3
""""""
import pandas as pd

OUTFILE = "app-flags.with-sources.csv"
ODDS_THRESHOLD = 1.0
VERBOSE = True

flags_df = pd.read_csv("app-flags.csv")
odds_df = pd.read_csv("kevins_approach.csv")

flags_df["source"] = "appscraper"
flags_play_df = flags_df[flags_df["store"] == "playstore"]

if VERBOSE:
    print("Appscraper has {} Android apps.".format(flags_play_df.shape[0]))

    print("Co-occurrence odds-ratio has {} Android apps.".format(odds_df.shape[0]))

    print("Apps in common: {}".format(flags_play_df.appId.isin(odds_df.appId).shape[0]))

odds_flags_df = pd.DataFrame(columns=flags_df.columns.tolist())

# increase odds ratio threshold necessary?
# taint-prob,odd-ratio
odds_df = odds_df[odds_df["odd-ratio"] > ODDS_THRESHOLD]

# FIXME: assuming they're all from playstore?
# should run scraper to verify offstore or playstore?
odds_flags_df["appId"] = odds_df.appId
odds_flags_df["source"] = "odds-ratio"
odds_flags_df["store"] = "playstore"
odds_flags_df["flag"] = "high co-occurence odds"
odds_flags_df = odds_flags_df.fillna("<Unknown>")

print("Concatenating into {}...".format(OUTFILE))
pd.concat([flags_df, odds_flags_df]).reset_index(drop=True).to_csv(OUTFILE)
print("Concatenated.")
