"""Static consistency checks for the provider/city catalogue."""

from mzkzg_transport.config_flow import PROVIDER_OPTIONS
from mzkzg_transport.const import (
    GTFSRT_PROVIDERS,
    KIEDYPRZYJEDZIE_PROVIDERS,
    PROVIDER_COLORS,
    PROVIDER_CZERNICA,
    PROVIDER_DEBICA,
    PROVIDER_LABELS,
    PROVIDER_SANOK,
)
from mzkzg_transport.gtfsrt_cities import GTFSRT_CITIES


def test_every_gtfsrt_provider_has_a_city_config():
    missing = GTFSRT_PROVIDERS - set(GTFSRT_CITIES)
    assert not missing, f"providers without GTFSRT_CITIES entry: {sorted(missing)}"


def test_every_city_has_a_source_or_is_marked_unavailable():
    broken = []
    for provider, cfg in GTFSRT_CITIES.items():
        if cfg.get("unavailable"):
            continue
        if not (cfg.get("gtfs_url") or cfg.get("gtfs_package_id")):
            broken.append(provider)
    assert not broken, f"city configs without a GTFS source: {broken}"


def test_unavailable_cities_are_not_offered_in_config_flow():
    assert PROVIDER_DEBICA not in PROVIDER_OPTIONS
    assert PROVIDER_SANOK not in PROVIDER_OPTIONS


def test_every_city_and_provider_has_a_label():
    missing_cities = [
        provider for provider, cfg in GTFSRT_CITIES.items() if not cfg.get("label")
    ]
    missing_providers = [
        provider for provider in GTFSRT_PROVIDERS if not PROVIDER_LABELS.get(provider)
    ]
    assert not missing_cities, f"cities without label: {missing_cities}"
    assert not missing_providers, f"providers without label: {missing_providers}"


def test_every_kiedyprzyjedzie_provider_is_selectable_and_styled():
    missing_options = sorted(
        provider for provider in KIEDYPRZYJEDZIE_PROVIDERS if provider not in PROVIDER_OPTIONS
    )
    missing_labels = sorted(
        provider for provider in KIEDYPRZYJEDZIE_PROVIDERS if not PROVIDER_LABELS.get(provider)
    )
    missing_colors = sorted(
        provider for provider in KIEDYPRZYJEDZIE_PROVIDERS if not PROVIDER_COLORS.get(provider)
    )
    assert not missing_options, f"carriers missing from config flow: {missing_options}"
    assert not missing_labels, f"carriers without label: {missing_labels}"
    assert not missing_colors, f"carriers without header colour: {missing_colors}"
    assert PROVIDER_OPTIONS[PROVIDER_CZERNICA] == "Gmina Czernica"
    assert PROVIDER_LABELS[PROVIDER_CZERNICA] == "Gmina Czernica"
    assert PROVIDER_COLORS[PROVIDER_CZERNICA] == "#1e3a8a"
