import pandas as pd
from isdi.config import get_config
import dataset
import sys

config = get_config()


def join_csv_files(flist, ofname):
    pd.concat([pd.read_csv(f) for f in flist]).to_csv(
        ofname, index=None, compression="gzip"
    )


def create_app_flags_file():
    dlist = []
    for k, v in config.source_files.items():
        d = pd.read_csv(v, index_col="appId")
        if k == "offstore":
            d["relevant"] = "y"
        elif ("relevant" not in d.columns) and ("ml_score" in d.columns):
            d["relevant"] = (d["ml_score"] > 0.4).apply(lambda x: "y" if x else "n")
            print("---->  'relevant' column is missing... recreating", k, v)

            ## TODO: Remove this or set 0.5 to 0.2 or something
        elif (d.relevant.count() < len(d) * 0.5) and ("ml_score" in d.columns):
            print(
                "---->  'relevant' column is underpopulated={}... recreating: k={}\tv={}".format(
                    d.relevant.count(), k, v
                )
            )
            d["relevant"].fillna("", inplace=True)
            e = d.relevant == ""
            d.loc[e, "relevant"] = (d.loc[e, "ml_score"] > 0.4).apply(
                lambda x: "y" if x else "n"
            )

        print("done reading: {} (l={})".format(k, len(d)))
        d = d.query('relevant == "y"')
        r = pd.DataFrame(columns=["store", "flag", "title"], index=d.index)
        r["title"] = d["title"]
        r["store"] = k
        r["flag"] = "dual-use" if k != "offstore" else "spyware"
        dlist.append(r)
    sys.stderr.write("Concatenating...")
    fulld = pd.concat(dlist)
    sys.stderr.write("done\n")
    spyware = pd.read_csv(config.SPYWARE_LIST_FILE, index_col="appId")
    fulld.loc[spyware.index, "flag"] = "spyware"
    print("Writing to the file: {config.APP_FLAGS_FILE}")
    fulld.to_csv(config.APP_FLAGS_FILE)


def create_app_info_dict():
    dlist = []
    conn = dataset.connect(config.APP_INFO_SQLITE_FILE)
    print("Creating app-info dict")
    for k, v in config.source_files.items():
        d = pd.read_csv(v, index_col="appId")

        d["store"] = k

        if "permissions" not in d.columns:
            print(k, v, d.columns)
            d.assign(permissions=["<not recorded>"] * len(d))
        d.columns = d.columns.str.lower().str.replace(" ", "-").str.replace("-", "_")
        dlist.append(d)
    pd.concat(dlist).to_sql("apps", conn.engine, if_exists="replace")
    conn.engine.execute("create index idx_appId on apps(appId)")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        join_csv_files(sys.argv[1:], config.source_files["playstore"])
    create_app_flags_file()
    create_app_info_dict()
