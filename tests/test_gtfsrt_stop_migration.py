"""Tests for resolving stale GTFS stop IDs after operator feed changes."""

from mzkzg_transport.gtfsrt_parser import resolve_stop_id


STOPS = {
    "majdanek-pomnik01-lim0g": {"name": "Majdanek - pomnik 01", "lat": 51.227222, "lon": 22.602341},
    "majdanek-pomnik02-liv9t": {"name": "Majdanek - pomnik 02", "lat": 51.227314, "lon": 22.602482},
    "majdanek01-lquai": {"name": "Majdanek 01", "lat": 51.224952, "lon": 22.608734},
    "majdanek02-lsn3s": {"name": "Majdanek 02", "lat": 51.224776, "lon": 22.610066},
    "sulislawicka01-lb0vq": {"name": "Sulisławicka 01"},
    "sulislawicka02-jd3ka": {"name": "Sulisławicka 02"},
    "sulislawicka03-k2m1x": {"name": "Sulisławicka 03"},
    "dworzec-lublin": {"name": "Dworzec Lublin"},
}


def test_existing_id_is_returned_unchanged():
    assert resolve_stop_id(STOPS, "majdanek01-lquai", "anything") == "majdanek01-lquai"


def test_old_numeric_id_resolves_by_name_and_last_digit():
    assert resolve_stop_id(STOPS, "3142", "Majdanek - pomnik NŻ") == "majdanek-pomnik02-liv9t"


def test_platform_from_old_name_wins():
    assert resolve_stop_id(STOPS, "3151", "Majdanek 01") == "majdanek01-lquai"


def test_three_platforms_use_last_digit():
    assert resolve_stop_id(STOPS, "3372", "Sulisławicka") == "sulislawicka02-jd3ka"


def test_exact_unique_name_resolves_without_platform():
    assert resolve_stop_id(STOPS, "9999", "Dworzec Lublin") == "dworzec-lublin"


def test_unknown_stop_is_not_guessed():
    assert resolve_stop_id(STOPS, "8000", "Nieistniejący przystanek") is None
