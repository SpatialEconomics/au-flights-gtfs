"""Tests for the GTFS builder, driven by the built-in fallback timetable."""

from __future__ import annotations

from au_flights_gtfs import Config, GTFSBuilder, build_fallback_flights
from au_flights_gtfs.builder import sec_to_gtfs


def _feed():
    cfg = Config(use_api=False, service_date="20260610", service_id="SVC_20260610")
    return GTFSBuilder(cfg).build(build_fallback_flights(), source_label="test")


def test_sec_to_gtfs_basic():
    assert sec_to_gtfs(0) == "00:00:00"
    assert sec_to_gtfs(3661) == "01:01:01"
    assert sec_to_gtfs(25 * 3600) == "25:00:00"   # GTFS allows >24h


def test_tables_present_and_nonempty():
    feed = _feed()
    for name in ("agency.txt", "stops.txt", "routes.txt", "trips.txt",
                 "stop_times.txt", "shapes.txt", "calendar_dates.txt", "feed_info.txt"):
        assert name in feed.tables, f"missing {name}"
    c = feed.counts()
    assert c["trips"] > 0
    assert c["stop_times"] >= 2 * c["trips"]      # at least origin+destination each
    assert c["agency"] >= 1


def test_calendar_single_date():
    feed = _feed()
    rows = feed.tables["calendar_dates.txt"]
    assert len(rows) == 1
    assert rows[0]["date"] == "20260610"
    assert rows[0]["exception_type"] == "1"


def test_every_stop_time_references_a_known_stop():
    feed = _feed()
    stop_ids = {r["stop_id"] for r in feed.tables["stops.txt"]}
    for st in feed.tables["stop_times.txt"]:
        assert st["stop_id"] in stop_ids


def test_multi_stop_trip_chained():
    """The fallback contains a SYD->ABX->WGA flight (RXA8100) -> a 3-stop trip."""
    feed = _feed()
    from collections import Counter
    per_trip = Counter(st["trip_id"] for st in feed.tables["stop_times.txt"])
    assert any(n >= 3 for n in per_trip.values()), "expected at least one multi-stop trip"


def test_write_and_zip(tmp_path):
    feed = _feed()
    out = feed.write(tmp_path / "gtfs")
    assert (out / "stop_times.txt").exists()
    zp = feed.to_zip(tmp_path / "gtfs.zip", out)
    assert zp.exists() and zp.stat().st_size > 0
