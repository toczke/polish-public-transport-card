"""MZK Wejherowo provider (static GTFS)."""

from homeassistant.util import dt as dt_util

from .const import PROVIDER_MZK


async def fetch(coord) -> dict:
    """Fetch departures from MZK Wejherowo static GTFS."""
    from .gtfs_provider import get_gtfs_data

    gtfs = await get_gtfs_data(coord)
    now = dt_util.now()

    if not coord.stop_name:
        stop_info = gtfs.stops.get(coord.stop_id, {})
        coord.stop_name = stop_info.get("name", f"Przystanek {coord.stop_id}")

    departures = gtfs.get_departures(coord.stop_id, now)
    return {
        "stop_id": coord.stop_id,
        "stop_name": coord.stop_name,
        "provider": PROVIDER_MZK,
        "departures": departures,
        "last_update": now.isoformat(),
    }
