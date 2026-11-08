"""Static consistency checks for the provider/city catalogue."""

from mzkzg_transport.config_flow import PROVIDER_OPTIONS
from mzkzg_transport.const import (
    GTFSRT_PROVIDERS,
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
