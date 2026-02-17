import csv
import gzip
import sqlite3
from isdi.config import get_config
import sys

config = get_config()


def join_csv_files(flist, ofname):
    rows = []
    fieldnames = []
    for fpath in flist:
        with open(fpath, "r", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames:
                for name in reader.fieldnames:
                    if name not in fieldnames:
                        fieldnames.append(name)
            for row in reader:
                rows.append(row)
    if not fieldnames and rows:
        fieldnames = list(rows[0].keys())

    with gzip.open(ofname, "wt", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def _read_csv_rows(file_path: str) -> list[dict]:
    with open(file_path, "r", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _normalize_key(key: str) -> str:
    return key.lower().replace(" ", "_").replace("-", "_")


def _score_is_relevant(score: str) -> bool:
    try:
        return float(score) > 0.4
    except (TypeError, ValueError):
        return False


def create_app_flags_file():
    dlist = []
    for k, v in config.source_files.items():
        d = _read_csv_rows(v)
        columns = set(d[0].keys()) if d else set()
        has_relevant = "relevant" in columns
        has_ml_score = "ml_score" in columns
        if k == "offstore":
            for row in d:
                row["relevant"] = "y"
        elif (not has_relevant) and has_ml_score:
            for row in d:
                row["relevant"] = "y" if _score_is_relevant(row.get("ml_score")) else "n"
            print("---->  'relevant' column is missing... recreating", k, v)

            ## TODO: Remove this or set 0.5 to 0.2 or something
        elif has_ml_score:
            relevant_count = len([row for row in d if row.get("relevant") not in (None, "")])
            if relevant_count >= len(d) * 0.5:
                pass
            else:
                print(
                    "---->  'relevant' column is underpopulated={}... recreating: k={}\tv={}".format(
                        relevant_count, k, v
                    )
                )
                for row in d:
                    if row.get("relevant") in (None, ""):
                        row["relevant"] = "y" if _score_is_relevant(row.get("ml_score")) else "n"

        print("done reading: {} (l={})".format(k, len(d)))
        for row in d:
            if row.get("relevant") != "y":
                continue
            app_id = row.get("appId", "")
            dlist.append(
                {
                    "appId": app_id,
                    "title": row.get("title", ""),
                    "store": k,
                    "flag": "dual-use" if k != "offstore" else "spyware",
                }
            )
    sys.stderr.write("Concatenating...")
    fulld = list(dlist)
    sys.stderr.write("done\n")
    spyware_rows = _read_csv_rows(config.SPYWARE_LIST_FILE)
    spyware_set = {row.get("appId", "") for row in spyware_rows if row.get("appId")}
    for row in fulld:
        if row.get("appId") in spyware_set:
            row["flag"] = "spyware"
    print("Writing to the file: {config.APP_FLAGS_FILE}")
    with open(config.APP_FLAGS_FILE, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["appId", "store", "flag", "title"])
        writer.writeheader()
        for row in fulld:
            writer.writerow({
                "appId": row.get("appId", ""),
                "store": row.get("store", ""),
                "flag": row.get("flag", ""),
                "title": row.get("title", ""),
            })


def create_app_info_dict():
    dlist = []
    db_path = config.APP_INFO_SQLITE_FILE.replace("sqlite:///", "")
    conn = sqlite3.connect(db_path)
    print("Creating app-info dict")
    for k, v in config.source_files.items():
        rows = _read_csv_rows(v)
        for row in rows:
            row["store"] = k
            if "permissions" not in row:
                row["permissions"] = "<not recorded>"
            normalized = {}
            for key, value in row.items():
                normalized[_normalize_key(key)] = value
            dlist.append(normalized)

    if not dlist:
        return

    columns = sorted({key for row in dlist for key in row.keys()})
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS apps")
    col_defs = ", ".join([f"{col} TEXT" for col in columns])
    cursor.execute(f"CREATE TABLE apps ({col_defs})")

    placeholders = ", ".join(["?"] * len(columns))
    insert_sql = f"INSERT INTO apps ({', '.join(columns)}) VALUES ({placeholders})"
    for row in dlist:
        values = [row.get(col, "") for col in columns]
        cursor.execute(insert_sql, values)

    if "appid" in columns:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_appId ON apps(appid)")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        join_csv_files(sys.argv[1:], config.source_files["playstore"])
    create_app_flags_file()
    create_app_info_dict()
