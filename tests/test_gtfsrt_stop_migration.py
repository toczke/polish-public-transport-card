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
    "urzad-miasta1141-mhwf5": {"name": "Urząd Miasta"},
    "urzad-miasta1142-mf76t": {"name": "Urząd Miasta"},
}


def test_existing_id_is_returned_unchanged():
    assert resolve_stop_id(STOPS, "majdanek01-lquai", "anything") == "majdanek01-lquai"


def test_old_numeric_id_resolves_by_name_and_last_digit():
    assert resolve_stop_id(STOPS, "3142", "Majdanek - pomnik NŻ") == "majdanek-pomnik02-liv9t"


def test_embedded_numeric_id_disambiguates_same_name():
    assert resolve_stop_id(STOPS, "1141", "Urząd Miasta") == "urzad-miasta1141-mhwf5"


def test_platform_from_old_name_wins():
    assert resolve_stop_id(STOPS, "3151", "Majdanek 01") == "majdanek01-lquai"


def test_three_platforms_use_last_digit():
    assert resolve_stop_id(STOPS, "3372", "Sulisławicka") == "sulislawicka02-jd3ka"


def test_exact_unique_name_resolves_without_platform():
    assert resolve_stop_id(STOPS, "9999", "Dworzec Lublin") == "dworzec-lublin"


def test_unknown_stop_is_not_guessed():
    assert resolve_stop_id(STOPS, "8000", "Nieistniejący przystanek") is None


# Wrocław (zbiorkom) on 2026-11-19: existing slugs gained a random suffix and the
# stop names changed format, so name matching alone cannot find them.
WROCLAW_STOPS = {
    "smolec-chlopska-glowna80370001-vlqwk": {"name": "Smolec - Chłopska/Główna 80370001"},
    "smolec-chlopska-glowna80370002-vlm9v": {"name": "Smolec - Chłopska/Główna 80370002"},
    "mokronos-gorny-wroclawska-gwarna80370005-wqn52": {"name": "Mokronos Górny - Wrocławska/Gwarna 80370005"},
    "mokronos-gorny-wroclawska-gwarna80370006-wqwec": {"name": "Mokronos Górny - Wrocławska/Gwarna 80370006"},
    "mokronos-gorny-topolowa-jarzebinowa80000007-whifl": {"name": "Mokronos Górny - Topolowa/Jarzębinowa 80000007"},
    "mokronos-gorny-topolowa-jarzebinowa80000008-whifl": {"name": "Mokronos Górny - Topolowa/Jarzębinowa 80000008"},
}


def test_slug_with_new_random_suffix_is_resolved():
    assert (
        resolve_stop_id(WROCLAW_STOPS, "smolec-chlopska-glowna80370002", "Smolec Chłopska Główna")
        == "smolec-chlopska-glowna80370002-vlm9v"
    )
    assert (
        resolve_stop_id(
            WROCLAW_STOPS,
            "mokronos-gorny-wroclawska-gwarna80370005",
            "Mokronos Górny Wrocławska Gwarna",
        )
        == "mokronos-gorny-wroclawska-gwarna80370005-wqn52"
    )


def test_changed_random_suffix_is_resolved_by_embedded_code():
    assert (
        resolve_stop_id(WROCLAW_STOPS, "smolec-chlopska-glowna80370001-abcde", "Smolec")
        == "smolec-chlopska-glowna80370001-vlqwk"
    )


def test_shared_suffix_does_not_mix_platforms():
    assert (
        resolve_stop_id(
            WROCLAW_STOPS, "mokronos-gorny-topolowa-jarzebinowa80000008", "Topolowa"
        )
        == "mokronos-gorny-topolowa-jarzebinowa80000008-whifl"
    )


def test_unknown_slug_code_is_not_guessed():
    assert resolve_stop_id(WROCLAW_STOPS, "smolec-chlopska-glowna80379999", "Nieznany") is None
