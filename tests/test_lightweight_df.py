from isdi.scanner.lightweight_df import LightDataFrame


def test_read_csv_fillna_isin(tmp_path):
    csv_path = tmp_path / "apps.csv"
    csv_path.write_text(
        "appId,title,flag\n" "com.example.app,,spyware\n" "com.safe.app,Safe App,\n"
    )

    df = LightDataFrame.read_csv(str(csv_path))
    filled = df.fillna({"title": "", "flag": "unknown"})
    spyware = filled.isin("flag", {"spyware"})

    assert len(df) == 2
    assert len(spyware) == 1
    assert spyware.data[0]["appId"] == "com.example.app"


def test_merge_groupby_sort_values():
    left = LightDataFrame(
        [
            {"id": "a1", "group": "g1", "score": 2},
            {"id": "a2", "group": "g1", "score": 1},
            {"id": "b1", "group": "g2", "score": 5},
        ]
    )
    right = LightDataFrame(
        [
            {"id": "a1", "name": "Alpha"},
            {"id": "b1", "name": "Beta"},
        ]
    )

    merged = left.merge(right, on="id", how="left")
    assert merged.data[0]["name"] == "Alpha"
    assert merged.data[1].get("name") in (None, "")

    grouped = left.groupby("group").agg({"score": "sum", "id": "count"})
    sorted_groups = grouped.sort_values(by="score", ascending=False)

    assert sorted_groups.data[0]["group"] == "g2"
    assert sorted_groups.data[0]["score"] == 5
    assert sorted_groups.data[1]["score"] == 3


def test_to_dict_orientations():
    df = LightDataFrame(
        [
            {"appId": "a", "title": "A"},
            {"appId": "b", "title": "B"},
        ]
    )

    records = df.to_dict(orient="records")
    index = df.to_dict(orient="index")
    columns = df.to_dict(orient="dict")

    assert records[0]["appId"] == "a"
    assert index["a"]["title"] == "A"
    assert columns["title"] == ["A", "B"]


def test_with_columns_select_and_to_csv(tmp_path):
    df = LightDataFrame(
        [
            {"appId": "a", "score": 1},
            {"appId": "b", "score": 2},
        ]
    )

    updated = df.with_columns({"risk": lambda row: row["score"] * 2})
    selected = updated.select(["appId", "risk"])

    csv_path = tmp_path / "out.csv"
    selected.to_csv(str(csv_path))

    roundtrip = LightDataFrame.read_csv(str(csv_path))
    assert roundtrip.data[0]["appId"] == "a"
    assert roundtrip.data[1]["risk"] == "4"
