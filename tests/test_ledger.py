import hashlib
import json

from shyftr.ledger import append_jsonl, file_sha256, read_jsonl


def test_append_jsonl_adds_deterministic_records_without_rewriting_existing_content(tmp_path):
    ledger = tmp_path / "events.jsonl"
    ledger.write_text('{"existing":true}\n', encoding="utf-8")

    append_jsonl(ledger, {"zeta": 1, "alpha": "first"})
    append_jsonl(ledger, {"nested": {"b": 2, "a": 1}})

    raw_rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
    assert raw_rows[0] == {"existing": True}
    assert raw_rows[1]["alpha"] == "first"
    assert raw_rows[1]["zeta"] == 1
    assert raw_rows[1]["previous_row_hash"]
    assert len(raw_rows[1]["row_hash"]) == 64
    assert raw_rows[2]["nested"] == {"a": 1, "b": 2}
    assert raw_rows[2]["previous_row_hash"] == raw_rows[1]["row_hash"]
    assert list(read_jsonl(ledger)) == [
        (1, {"existing": True}),
        (2, {"alpha": "first", "zeta": 1}),
        (3, {"nested": {"a": 1, "b": 2}}),
    ]


def test_read_jsonl_replays_records_with_line_numbers_and_skips_blank_lines(tmp_path):
    ledger = tmp_path / "events.jsonl"
    ledger.write_text('{"first":1}\n\n{"second":2}\n', encoding="utf-8")

    assert list(read_jsonl(ledger)) == [
        (1, {"first": 1}),
        (3, {"second": 2}),
    ]


def test_file_sha256_hashes_file_bytes(tmp_path):
    payload = tmp_path / "payload.bin"
    payload.write_bytes(b"shyftr\x00payload\n")

    assert file_sha256(payload) == hashlib.sha256(b"shyftr\x00payload\n").hexdigest()


def test_append_jsonl_creates_parent_directories(tmp_path):
    ledger = tmp_path / "nested" / "events.jsonl"

    append_jsonl(ledger, {"created": True})

    raw_record = json.loads(ledger.read_text(encoding="utf-8"))
    assert raw_record["created"] is True
    assert raw_record["previous_row_hash"] == ""
    assert len(raw_record["row_hash"]) == 64
    assert list(read_jsonl(ledger)) == [(1, {"created": True})]


# ---------------------------------------------------------------------------
# Active-learning ledger readers (AL-1)
# ---------------------------------------------------------------------------


def test_read_confidence_events_delegates_to_read_jsonl(tmp_path):
    from shyftr.ledger import read_confidence_events

    cell = tmp_path / "cell"
    cell.mkdir()
    (cell / "ledger").mkdir()
    (cell / "ledger" / "confidence_events.jsonl").write_text(
        '{"confidence_event_id":"ce-1","cell_id":"c"}\n', encoding="utf-8"
    )
    results = list(read_confidence_events(cell))
    assert len(results) == 1
    assert results[0][1]["confidence_event_id"] == "ce-1"


def test_read_retrieval_affinity_events_delegates_to_read_jsonl(tmp_path):
    from shyftr.ledger import read_retrieval_affinity_events

    cell = tmp_path / "cell"
    cell.mkdir()
    (cell / "ledger").mkdir()
    (cell / "ledger" / "retrieval_affinity_events.jsonl").write_text(
        '{"affinity_event_id":"ae-1","cell_id":"c"}\n', encoding="utf-8"
    )
    results = list(read_retrieval_affinity_events(cell))
    assert len(results) == 1
    assert results[0][1]["affinity_event_id"] == "ae-1"


def test_read_audit_sparks_delegates_to_read_jsonl(tmp_path):
    from shyftr.ledger import read_audit_sparks

    cell = tmp_path / "cell"
    cell.mkdir()
    (cell / "ledger").mkdir()
    (cell / "ledger" / "audit_sparks.jsonl").write_text(
        '{"spark_id":"sp-1","cell_id":"c"}\n', encoding="utf-8"
    )
    results = list(read_audit_sparks(cell))
    assert len(results) == 1
    assert results[0][1]["spark_id"] == "sp-1"


def test_read_audit_reviews_delegates_to_read_jsonl(tmp_path):
    from shyftr.ledger import read_audit_reviews

    cell = tmp_path / "cell"
    cell.mkdir()
    (cell / "ledger").mkdir()
    (cell / "ledger" / "audit_reviews.jsonl").write_text(
        '{"review_id":"ar-1","cell_id":"c"}\n', encoding="utf-8"
    )
    results = list(read_audit_reviews(cell))
    assert len(results) == 1
    assert results[0][1]["review_id"] == "ar-1"
