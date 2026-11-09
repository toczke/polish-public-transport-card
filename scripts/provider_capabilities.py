"""Generate the provider capability matrix embedded in README.md.

Run from the repository root:

    python scripts/provider_capabilities.py

The README test imports :func:`render_markdown` so the table cannot silently
drift from the provider catalogue.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components"))

from mzkzg_transport.config_flow import PROVIDER_OPTIONS
from mzkzg_transport.const import (
    PROVIDER_KRAKOW,
    PROVIDER_LODZ,
    PROVIDER_MZK,
    PROVIDER_PLK,
    PROVIDER_ZKM,
    PROVIDER_ZTM,
    TIME4BUS_PROVIDERS,
)
from mzkzg_transport.gtfsrt_cities import GTFSRT_CITIES

YES = "✅"
NO = "—"
DEPENDENT = "✅*"

DEDICATED = {
    PROVIDER_ZTM: (True, True, True, True, True, True),
    PROVIDER_ZKM: (True, False, False, True, True, True),
    PROVIDER_MZK: (False, False, False, False, False, False),
    PROVIDER_LODZ: (True, True, True, True, True, True),
    PROVIDER_KRAKOW: (True, True, True, False, False, False),
    PROVIDER_PLK: (True, False, False, False, False, False),
}


def capabilities(provider: str) -> tuple[bool, bool, bool, bool, bool, bool] | None:
    """Return (rt, gps, alerts, wheelchair, bike, ac) for a provider."""
    if provider in DEDICATED:
        return DEDICATED[provider]

    if provider in TIME4BUS_PROVIDERS:
        return (True, False, False, True, False, True)

    if provider.startswith("kiedyprzyjedzie_"):
        return (True, False, False, True, True, True)

    cfg = GTFSRT_CITIES.get(provider)
    if not cfg:
        return None

    rt = bool(cfg.get("rt_url"))
    if not rt:
        return (False, False, False, False, False, False)

    gps = bool(cfg.get("positions_url"))
    alerts = bool(cfg.get("alerts_url")) or "/gtfsRealtime/" in str(cfg["rt_url"])
    # GTFS-RT trip updates expose wheelchair/bike where the static feed has the
    # corresponding columns; the vehicle dictionary is the only AC source.
    wheelchair = True
    bike = True
    ac = bool(cfg.get("vehicles_url"))
    return (rt, gps, alerts, wheelchair, bike, ac)


def _cell(value: bool | str) -> str:
    if isinstance(value, str):
        return value
    return YES if value else NO


def render_markdown() -> str:
    """Render the Markdown table used in README.md."""
    lines = [
        "| Provider | Alerts | RT | GPS | Wheelchair | Bike | AC |",
        "|---|:--:|:--:|:--:|:--:|:--:|:--:|",
    ]
    for provider, label in PROVIDER_OPTIONS.items():
        caps = capabilities(provider)
        if caps is None:
            continue
        dependent = provider not in DEDICATED
        cells = [
            _cell(caps[2]),
            _cell(caps[0]),
            _cell(caps[1]),
            _cell(DEPENDENT if caps[3] and dependent else caps[3]),
            _cell(DEPENDENT if caps[4] and dependent else caps[4]),
            _cell(DEPENDENT if caps[5] and dependent else caps[5]),
        ]
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


if __name__ == "__main__":
    print(render_markdown())
