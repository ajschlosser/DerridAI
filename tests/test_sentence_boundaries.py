from app.sentence_boundaries import snap_boundaries_to_sentences as snap


def blocks(*texts, kind="body"):
    return [{"block_id": f"b{i}", "text": t, "type": kind, "page": 1} for i, t in enumerate(texts)]


def cut(*ids):
    return [{"after_block_id": f"b{i}"} for i in ids]


def ids(result):
    return [b["after_block_id"] for b in result[0]]


def test_clean_boundary_is_kept():
    b = blocks("One.", "Two.", "Three.", "Four.")
    assert ids(snap(b, cut(1))) == ["b1"]


def test_boundary_mid_sentence_moves_to_nearest_sentence_end():
    b = blocks("One.", "Two begins and", "keeps going", "until here.", "Four.")
    out, report = snap(b, cut(1, 3))
    assert [x["after_block_id"] for x in out] == ["b0", "b3"] or [x["after_block_id"] for x in out] == ["b3"]
    assert "b1" not in [x["after_block_id"] for x in out]
    assert report["moved"] or report["merged"]


def test_next_block_starting_lowercase_makes_boundary_unclean():
    b = blocks("It ended here.", "and it went on.", "New.")
    assert ids(snap(b, cut(0))) != ["b0"]


def test_no_clean_point_merges_records():
    b = blocks("a and", "b and", "c and", "d.")
    result, report = snap(b, cut(0, 1))
    assert result == [] and len(report["merged"]) == 2


def test_oversized_sentence_is_kept_and_reported():
    b = blocks("x" * 50 + " and", "y" * 50 + " and", "z.")
    result, report = snap(b, cut(0), hard_max_chars=60)
    assert ids((result, report)) == ["b0"]
    assert report["unavoidable"][0]["reason"] == "sentence_longer_than_record_limit"


def test_headings_end_a_record_without_punctuation():
    b = blocks("Chapter One", "It begins.", kind="heading")
    b[1]["type"] = "body"
    assert ids(snap(b, cut(0))) == ["b0"]


def test_every_resulting_record_starts_and_ends_on_sentence_boundaries():
    b = blocks("A.", "B starts", "and ends.", "C starts", "here", "and ends.", "D.")
    result, _ = snap(b, cut(0, 1, 3, 4))
    from app.sentence_boundaries import clean_boundary
    index = {x["block_id"]: i for i, x in enumerate(b)}
    for item in result:
        i = index[item["after_block_id"]]
        assert clean_boundary(b[i], b[i + 1])
