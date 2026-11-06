"""GTFS-RT provider for cities with protobuf realtime feeds (Poznań, Lublin, Białystok, etc.)."""

import asyncio
import csv
import logging
import zipfile
from datetime import timedelta
from io import BytesIO, StringIO, TextIOWrapper
from pathlib import Path

import aiohttp

from homeassistant.util import dt as dt_util

from .const import DOMAIN, MAX_DEPARTURES

_LOGGER = logging.getLogger(__name__)


def _read_csv(zf, filename):
    """Return (header, lazy row iterator) for a GTFS CSV member.

    Rows are streamed straight from the zip so huge members such as Warsaw's
    stop_times.txt (millions of rows) never get materialised in memory.
    The iterator must be consumed while ``zf`` is still open.
    """
    if filename not in zf.namelist():
        return None, ()

    stream = TextIOWrapper(zf.open(filename), encoding="utf-8-sig", newline="")
    reader = csv.reader(stream)
    try:
        header = next(reader)
    except StopIteration:
        stream.close()
        return None, ()

    def _rows():
        try:
            yield from reader
        finally:
            stream.close()

    return header, _rows()

# GTFS-RT city configs: static GTFS zip + realtime TripUpdates URL
GTFSRT_CITIES = {
    "gtfsrt_poznan": {
        "gtfs_url": "https://www.ztm.poznan.pl/pl/dla-deweloperow/getGTFSFile",
        "rt_url": "https://www.ztm.poznan.pl/pl/dla-deweloperow/getGtfsRtFile?file=trip_updates.pb",
        "vehicles_url": "https://www.ztm.poznan.pl/pl/dla-deweloperow/getGtfsRtFile?file=vehicle_dictionary.csv",
        "positions_url": "https://www.ztm.poznan.pl/pl/dla-deweloperow/getGtfsRtFile?file=vehicle_positions.pb",
        "label": "ZTM Pozna\u0144",
    },
    "gtfsrt_lublin": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/lublin/gtfs/default",
        "rt_url": "https://api.zbiorkom.live/api6-open/lublin/gtfsRealtime/default/tripUpdates",
        "positions_url": "https://api.zbiorkom.live/api6-open/lublin/gtfsRealtime/default/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "ZTM Lublin",
    },
    "gtfsrt_kielce": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/kielce/gtfs/default",
        "rt_url": "https://api.zbiorkom.live/api6-open/kielce/gtfsRealtime/default/tripUpdates",
        "positions_url": "https://api.zbiorkom.live/api6-open/kielce/gtfsRealtime/default/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "MPK Kielce",
    },
    "gtfsrt_radom": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/radom/gtfs/default",
        "rt_url": "https://api.zbiorkom.live/api6-open/radom/gtfsRealtime/default/tripUpdates",
        "positions_url": "https://api.zbiorkom.live/api6-open/radom/gtfsRealtime/default/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "MZDiK Radom",
    },
    "gtfsrt_czestochowa": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/czestochowa/gtfs/default",
        "rt_url": "https://api.zbiorkom.live/api6-open/czestochowa/gtfsRealtime/default/tripUpdates",
        "positions_url": "https://api.zbiorkom.live/api6-open/czestochowa/gtfsRealtime/default/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "MPK Cz\u0119stochowa",
    },
    "gtfsrt_elblag": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/elblag/gtfs/default",
        "rt_url": "https://api.zbiorkom.live/api6-open/elblag/gtfsRealtime/default/tripUpdates",
        "positions_url": "https://api.zbiorkom.live/api6-open/elblag/gtfsRealtime/default/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "ZKM Elbl\u0105g",
    },
    "gtfsrt_gorzow": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/gorzow/gtfs/default",
        "rt_url": "https://api.zbiorkom.live/api6-open/gorzow/gtfsRealtime/default/tripUpdates",
        "positions_url": "https://api.zbiorkom.live/api6-open/gorzow/gtfsRealtime/default/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "MZK Gorz\u00f3w Wlkp.",
    },
    "gtfsrt_suwalki": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/suwalki/gtfs/default",
        "rt_url": "https://api.zbiorkom.live/api6-open/suwalki/gtfsRealtime/default/tripUpdates",
        "positions_url": "https://api.zbiorkom.live/api6-open/suwalki/gtfsRealtime/default/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "PGK Suwa\u0142ki",
    },
    "gtfsrt_przemysl": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/przemysl/gtfs/default",
        "rt_url": "https://api.zbiorkom.live/api6-open/przemysl/gtfsRealtime/default/tripUpdates",
        "positions_url": "https://api.zbiorkom.live/api6-open/przemysl/gtfsRealtime/default/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "MZK Przemy\u015bl",
    },
    "gtfsrt_rybnik": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/rybnik/gtfs/default",
        "rt_url": "https://api.zbiorkom.live/api6-open/rybnik/gtfsRealtime/default/tripUpdates",
        "positions_url": "https://api.zbiorkom.live/api6-open/rybnik/gtfsRealtime/default/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "ZTZ Rybnik",
    },
    "gtfsrt_kutno": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/kutno/gtfs/default",
        "rt_url": "https://api.zbiorkom.live/api6-open/kutno/gtfsRealtime/default/tripUpdates",
        "positions_url": "https://api.zbiorkom.live/api6-open/kutno/gtfsRealtime/default/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "MZK Kutno",
    },
    "gtfsrt_legnica": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/legnica/gtfs/default",
        "rt_url": "https://api.zbiorkom.live/api6-open/legnica/gtfsRealtime/default/tripUpdates",
        "positions_url": "https://api.zbiorkom.live/api6-open/legnica/gtfsRealtime/default/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "MPK Legnica",
    },
    "gtfsrt_szczecin": {
        "gtfs_url": "https://www.zditm.szczecin.pl/storage/gtfs/gtfs.zip",
        "rt_url": "https://www.zditm.szczecin.pl/storage/gtfs/gtfs-rt-trips.pb",
        "positions_url": "https://www.zditm.szczecin.pl/api/v2/vehicles?format=json",
        "label": "ZDiTM Szczecin",
    },
    "gtfsrt_warszawa": {
        "gtfs_url": "https://mkuran.pl/gtfs/warsaw.zip",
        "rt_url": "https://mkuran.pl/gtfs/warsaw/vehicles.pb",
        "positions_url": "https://mkuran.pl/gtfs/warsaw/positions.json",
        "label": "ZTM Warszawa",
    },
    "gtfsrt_elk": {
        "gtfs_url": "https://mkuran.pl/gtfs/elk.zip",
        "rt_url": "https://mkuran.pl/gtfs/elk.pb",
        "positions_url": "https://mkuran.pl/gtfs/elk.pb",
        "label": "MZK Ełk",
    },
    "gtfsrt_wkd": {
        "gtfs_url": "https://mkuran.pl/gtfs/wkd.zip",
        "rt_url": "https://mkuran.pl/gtfs/wkd.pb",
        "label": "WKD",
    },
    "gtfs_bialystok": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/bialystok/gtfs/default",
        "rt_url": "https://api.zbiorkom.live/api6-open/bialystok/gtfsRealtime/default/tripUpdates",
        "positions_url": "https://api.zbiorkom.live/api6-open/bialystok/gtfsRealtime/default/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "BKM Białystok",
    },
    "gtfs_olsztyn": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/olsztyn/gtfs/default",
        "rt_url": "https://api.zbiorkom.live/api6-open/olsztyn/gtfsRealtime/default/tripUpdates",
        "positions_url": "https://api.zbiorkom.live/api6-open/olsztyn/gtfsRealtime/default/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "ZDZiT Olsztyn",
    },
    "gtfs_opole": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/opole/gtfs/default",
        "rt_url": "https://api.zbiorkom.live/api6-open/opole/gtfsRealtime/default/tripUpdates",
        "positions_url": "https://api.zbiorkom.live/api6-open/opole/gtfsRealtime/default/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "MZK Opole",
    },
    "gtfsrt_wroclaw": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/wroclaw/gtfs/default",
        "rt_url": "https://api.zbiorkom.live/api6-open/wroclaw/gtfsRealtime/default/tripUpdates",
        "positions_url": "https://api.zbiorkom.live/api6-open/wroclaw/gtfsRealtime/default/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "MPK Wroc\u0142aw",
    },
    "gtfs_rzeszow": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/rzeszow/gtfs/default",
        "rt_url": "https://api.zbiorkom.live/api6-open/rzeszow/gtfsRealtime/default/tripUpdates",
        "positions_url": "https://api.zbiorkom.live/api6-open/rzeszow/gtfsRealtime/default/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "ZTM Rzeszów",
    },
        "gtfs_kalisz": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/kalisz/gtfs/default",
        "rt_url": "https://api.zbiorkom.live/api6-open/kalisz/gtfsRealtime/default/tripUpdates",
        "positions_url": "https://api.zbiorkom.live/api6-open/kalisz/gtfsRealtime/default/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "MZK Kalisz",
    },
    "gtfs_konin": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/konin/gtfs/default",
        "rt_url": "https://api.zbiorkom.live/api6-open/konin/gtfsRealtime/default/tripUpdates",
        "positions_url": "https://api.zbiorkom.live/api6-open/konin/gtfsRealtime/default/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "MZK Konin",
    },
    "gtfs_koszalin": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/koszalin/gtfs/default",
        "rt_url": "https://api.zbiorkom.live/api6-open/koszalin/gtfsRealtime/default/tripUpdates",
        "positions_url": "https://api.zbiorkom.live/api6-open/koszalin/gtfsRealtime/default/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "MZK Koszalin",
    },
    "gtfs_krosno": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/krosno/gtfs/default",
        "rt_url": "https://api.zbiorkom.live/api6-open/krosno/gtfsRealtime/default/tripUpdates",
        "positions_url": "https://api.zbiorkom.live/api6-open/krosno/gtfsRealtime/default/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "MKS Krosno",
    },
    "gtfs_pila": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/pila/gtfs/default",
        "rt_url": "https://api.zbiorkom.live/api6-open/pila/gtfsRealtime/default/tripUpdates",
        "positions_url": "https://api.zbiorkom.live/api6-open/pila/gtfsRealtime/default/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "MZK Piła",
    },
    "gtfs_plock": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/plock/gtfs/default",
        "rt_url": "https://api.zbiorkom.live/api6-open/plock/gtfsRealtime/default/tripUpdates",
        "positions_url": "https://api.zbiorkom.live/api6-open/plock/gtfsRealtime/default/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "KM Płock",
    },
    "gtfs_siedlce": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/siedlce/gtfs/default",
        "rt_url": "https://api.zbiorkom.live/api6-open/siedlce/gtfsRealtime/default/tripUpdates",
        "positions_url": "https://api.zbiorkom.live/api6-open/siedlce/gtfsRealtime/default/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "MPK Siedlce",
    },
    "gtfs_starachowice": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/starachowice/gtfs/default",
        "rt_url": "https://api.zbiorkom.live/api6-open/starachowice/gtfsRealtime/default/tripUpdates",
        "positions_url": "https://api.zbiorkom.live/api6-open/starachowice/gtfsRealtime/default/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "MZK Starachowice",
    },
    "gtfs_tarnow": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/tarnow/gtfs/default",
        "rt_url": "https://api.zbiorkom.live/api6-open/tarnow/gtfsRealtime/default/tripUpdates",
        "positions_url": "https://api.zbiorkom.live/api6-open/tarnow/gtfsRealtime/default/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "MPK Tarnów",
    },
    "gtfs_walbrzych": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/walbrzych/gtfs/default",
        "rt_url": "https://api.zbiorkom.live/api6-open/walbrzych/gtfsRealtime/default/tripUpdates",
        "positions_url": "https://api.zbiorkom.live/api6-open/walbrzych/gtfsRealtime/default/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "ZKM Wałbrzych",
    },
    "gtfs_swinoujscie": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/swinoujscie/gtfs/default",
        "rt_url": "https://api.zbiorkom.live/api6-open/swinoujscie/gtfsRealtime/default/tripUpdates",
        "positions_url": "https://api.zbiorkom.live/api6-open/swinoujscie/gtfsRealtime/default/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "KA Świnoujście",
    },
    "gtfs_bydgoszcz": {
        "gtfs_url": "https://mkuran.pl/gtfs/bydgoszcz.zip",
        "rt_url": None,
        "label": "ZDMiKP Bydgoszcz",
    },
    "gtfs_mielec": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/mielec/gtfs/default",
        "rt_url": "https://api.zbiorkom.live/api6-open/mielec/gtfsRealtime/default/tripUpdates",
        "positions_url": "https://api.zbiorkom.live/api6-open/mielec/gtfsRealtime/default/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "MKS Mielec",
    },
    "gtfs_oswiecim": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/oswiecim/gtfs/default",
        "rt_url": "https://api.zbiorkom.live/api6-open/oswiecim/gtfsRealtime/default/tripUpdates",
        "positions_url": "https://api.zbiorkom.live/api6-open/oswiecim/gtfsRealtime/default/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "MZK Oświęcim",
    },
    "gtfs_radomsko": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/radomsko/gtfs/default",
        "rt_url": "https://api.zbiorkom.live/api6-open/radomsko/gtfsRealtime/default/tripUpdates",
        "positions_url": "https://api.zbiorkom.live/api6-open/radomsko/gtfsRealtime/default/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "MPK Radomsko",
    },
    "gtfs_debica": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/debica/gtfs/default",
        "rt_url": None,
        "label": "MKS Dębica",
    },
    "gtfs_kolobrzeg": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/kolobrzeg/gtfs/default",
        "rt_url": None,
        "label": "KM Kołobrzeg",
    },
    "gtfs_sanok": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/sanok/gtfs/default",
        "rt_url": None,
        "label": "SPGK Sanok",
    },
    "gtfs_ostroleka": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/ostroleka/gtfs/default",
        "rt_url": None,
        "label": "MZK Ostrołęka",
    },
    "gtfs_leszno": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/leszno/gtfs/default",
        "rt_url": "https://api.zbiorkom.live/api6-open/leszno/gtfsRealtime/default/tripUpdates",
        "positions_url": "https://api.zbiorkom.live/api6-open/leszno/gtfsRealtime/default/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "MZK Leszno",
    },
    "gtfsrt_torun": {
        "gtfs_url": "https://api.zbiorkom.live/api6-open/torun/gtfs/default",
        "rt_url": "https://api.zbiorkom.live/api6-open/torun/gtfsRealtime/default/tripUpdates",
        "positions_url": "https://api.zbiorkom.live/api6-open/torun/gtfsRealtime/default/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "MZK Toruń",
    },
    "gtfsrt_gzm": {
        "gtfs_url": None,  # Dynamic - fetched from CKAN API
        "gtfs_package_id": "317435cc-0075-4d10-b8ef-6e9b0010e90a",
        "rt_url": "https://gtfsrt.transportgzm.pl:5443/gtfsrt/gzm/tripUpdates",
        "positions_url": "https://gtfsrt.transportgzm.pl:5443/gtfsrt/gzm/vehiclePositions",
        "positions_format": "gtfsrt_protobuf",
        "label": "ZTM GZM (Katowice)",
    },
    "mpk_lodz": {
        "gtfs_url": "https://otwarte.miasto.lodz.pl/wp-content/uploads/2025/06/GTFS.zip",
        "rt_url": "https://otwarte.miasto.lodz.pl/wp-content/uploads/2025/06/trip_updates.bin",
        "positions_url": "https://otwarte.miasto.lodz.pl/wp-content/uploads/2025/06/vehicle_positions.bin",
        "label": "MPK \u0141\u00f3d\u017a",
    },
}


async def fetch(coord: "MzkzgTransportCoordinator") -> dict:
    """Fetch departures using static GTFS + GTFS-RT TripUpdates."""
    session = await coord._get_session()
    now = dt_util.now()
    city_cfg = GTFSRT_CITIES.get(coord.provider)
    if not city_cfg:
        return {"stop_id": coord.stop_id, "stop_name": coord.stop_name, "provider": coord.provider, "departures": [], "last_update": now.isoformat()}

    # Load static GTFS (cached daily)
    gtfs = await _get_gtfs_data(coord, session, city_cfg, now)
    if not gtfs:
        return {"stop_id": coord.stop_id, "stop_name": coord.stop_name or f"Przystanek {coord.stop_id}", "provider": coord.provider, "departures": [], "last_update": now.isoformat()}

    # Get stop name
    if not coord.stop_name:
        coord.stop_name = gtfs["stops"].get(coord.stop_id, {}).get("name", f"Przystanek {coord.stop_id}")

    # Get scheduled departures for this stop
    stop_times = gtfs["stop_times"].get(coord.stop_id, [])

    # Load RT delays
    delays = {}
    if city_cfg.get("rt_url"):
        delays = await _get_rt_delays(session, city_cfg["rt_url"])
    if city_cfg.get("rt_url_tram"):
            tram_delays = await _get_rt_delays(session, city_cfg["rt_url_tram"])
            delays.update(tram_delays)

    departures = []
    for st in stop_times:
        trip_id = st["trip_id"]
        route_id = st["route_id"]
        route_name = gtfs["routes"].get(route_id, {}).get("short_name", route_id)
        headsign = st.get("headsign") or gtfs["trips"].get(trip_id, {}).get("headsign", "")

        # Parse departure time
        h, m, s = st["departure_time"]
        dep_dt = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=h, minutes=m, seconds=s)
        if dep_dt < now - timedelta(minutes=1):
            continue

        # Apply RT delay
        delay_sec = 0
        is_realtime = False
        vehicle_code = ""
        rt_key = f"{trip_id}_{coord.stop_id}"
        rt_key_seq = f"{trip_id}_seq{st.get('stop_sequence', '')}"
        rt_key_route = f"route_{route_id}_{coord.stop_id}"
        rt_key_route_only = f"route_{route_id}"
        for key in (rt_key, rt_key_seq, trip_id, rt_key_route, rt_key_route_only):
            if key in delays:
                delay_sec, vehicle_code = delays[key]
                is_realtime = True
                break

        estimated_dt = dep_dt + timedelta(seconds=delay_sec)

        trip_data = gtfs["trips"].get(trip_id, {})
        departures.append({
            "route": route_name,
            "headsign": headsign,
            "estimated_time": estimated_dt.isoformat(),
            "theoretical_time": dep_dt.isoformat(),
            "delay_seconds": delay_sec,
            "realtime": is_realtime,
            "vehicle_type": gtfs["routes"].get(route_id, {}).get("type", "bus"),
            "vehicle_code": vehicle_code if is_realtime else None,
            "trip_id": trip_id,
            "wheelchair_accessible": trip_data.get("wheelchair"),
            "bike_allowed": trip_data.get("bike"),
            "provider": coord.provider,
        })

    # Enrich with vehicle capabilities if available
    if city_cfg.get("vehicles_url") and any(d.get("vehicle_code") for d in departures):
        veh_dict = await _get_vehicle_dict(coord, session, city_cfg)
        for d in departures:
            vc = d.get("vehicle_code", "")
            if not vc:
                continue
            # Try direct match, then common prefixed variants (for Kraków trams: 121 -> HW121, etc.)
            v = veh_dict.get(vc)
            if not v:
                for prefix in ("HW", "RW", "HZ", "RZ", "HL", "RL", "HK", "RK", "HG", "RG", "HY", "RY", "RP", "RF"):
                    v = veh_dict.get(prefix + vc)
                    if v:
                        break
            if v:
                d["wheelchair_accessible"] = v.get("ramp") or v.get("hf_lf_le")
                d["air_conditioning"] = v.get("air_conditioner")
                d["bike_allowed"] = v.get("place_for_transp_bicycles")
                d["ticket_machine"] = v.get("ticket_machine")
                d["usb"] = v.get("usb_charger")
                if v.get("vehicle_model"):
                    d["vehicle_model"] = v["vehicle_model"]
                if v.get("floor_height"):
                    d["floor_height"] = v["floor_height"]
                if v.get("drive_type"):
                    d["drive_type"] = v["drive_type"]
                if v.get("length"):
                    d["vehicle_length"] = v["length"]

    # Enrich with GPS positions if positions_url is configured
    await _enrich_with_gps_positions(coord, session, city_cfg, departures)

    departures.sort(key=lambda x: x.get("estimated_time") or "")
    # Deduplicate: same route + headsign + theoretical_time = same departure
    seen = set()
    unique = []
    for d in departures:
        est = (d.get("estimated_time") or "")[:16]
        key = (d.get("route"), d.get("headsign"), est)
        if key not in seen:
            seen.add(key)
            unique.append(d)

    # If fewer than 5 departures, load tomorrow's schedule
    if len(unique) < 5 and gtfs.get("_raw"):
        tomorrow = now + timedelta(days=1)
        tomorrow_deps = await coord.hass.async_add_executor_job(
            _get_tomorrow_departures, gtfs, coord.stop_id, tomorrow, now
        )
        for d in tomorrow_deps:
            est = (d.get("estimated_time") or "")[:16]
            key = (d.get("route"), d.get("headsign"), est)
            if key not in seen:
                seen.add(key)
                unique.append(d)
                if len(unique) >= 20:
                    break

    return {
        "stop_id": coord.stop_id,
        "stop_name": coord.stop_name,
        "provider": coord.provider,
        "departures": unique[:MAX_DEPARTURES],
        "last_update": now.isoformat(),
    }


def _get_tomorrow_departures(gtfs, stop_id, tomorrow, now):
    """Get scheduled departures for tomorrow from raw GTFS zip."""
    raw = gtfs.get("_raw")
    if not raw:
        return []

    tomorrow_str = tomorrow.strftime("%Y%m%d")

    # Scanning stop_times.txt is expensive; keep the result so the nightly
    # "no departures left today" path does not rescan on every refresh.
    memo = gtfs.setdefault("_tomorrow_cache", {})
    memo_key = (stop_id, tomorrow_str)
    if memo_key in memo:
        return [d for dep_dt, d in memo[memo_key] if dep_dt >= now][:15]

    day_name = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][tomorrow.weekday()]
    
    # Parse calendar for tomorrow's active services
    active_services = set()
    with zipfile.ZipFile(BytesIO(raw)) as zf:
        header, rows = _read_csv(zf, "calendar.txt")
        if header:
            sid_idx = header.index("service_id")
            day_idx = header.index(day_name) if day_name in header else -1
            start_idx = header.index("start_date") if "start_date" in header else -1
            end_idx = header.index("end_date") if "end_date" in header else -1
            for parts in rows:
                if len(parts) <= sid_idx:
                    continue
                active = day_idx >= 0 and len(parts) > day_idx and parts[day_idx] == "1"
                if active and start_idx >= 0 and end_idx >= 0 and len(parts) > max(start_idx, end_idx):
                    if parts[start_idx] > tomorrow_str or parts[end_idx] < tomorrow_str:
                        active = False
                if active:
                    active_services.add(parts[sid_idx])

        header, rows = _read_csv(zf, "calendar_dates.txt")
        if header:
            sid_idx = header.index("service_id")
            date_idx = header.index("date")
            etype_idx = header.index("exception_type")
            for parts in rows:
                if len(parts) <= max(sid_idx, date_idx, etype_idx):
                    continue
                if parts[date_idx] != tomorrow_str:
                    continue
                if parts[etype_idx] == "1":
                    active_services.add(parts[sid_idx])
                elif parts[etype_idx] == "2":
                    active_services.discard(parts[sid_idx])

    if not active_services:
        memo.clear()
        memo[memo_key] = []
        return []

    tomorrow_trips = {}
    stop_times = []
    with zipfile.ZipFile(BytesIO(raw)) as zf:
        header, rows = _read_csv(zf, "trips.txt")
        if header:
            tid_idx = header.index("trip_id")
            rid_idx = header.index("route_id")
            svc_idx = header.index("service_id")
            hs_idx = header.index("trip_headsign") if "trip_headsign" in header else -1
            for parts in rows:
                if len(parts) <= max(tid_idx, rid_idx, svc_idx):
                    continue
                if parts[svc_idx] not in active_services:
                    continue
                tomorrow_trips[parts[tid_idx]] = {
                    "route_id": parts[rid_idx],
                    "headsign": parts[hs_idx] if hs_idx >= 0 and len(parts) > hs_idx else "",
                }

        header, rows = _read_csv(zf, "stop_times.txt")
        if header:
            tid_idx = header.index("trip_id")
            sid_idx = header.index("stop_id")
            time_column = "departure_time" if "departure_time" in header else "arrival_time"
            time_idx = header.index(time_column)
            hs_idx = header.index("stop_headsign") if "stop_headsign" in header else -1
            for parts in rows:
                if len(parts) <= max(tid_idx, sid_idx, time_idx) or parts[sid_idx] != stop_id:
                    continue
                trip_id = parts[tid_idx]
                trip = tomorrow_trips.get(trip_id)
                if not trip:
                    continue
                try:
                    h, m, s = map(int, parts[time_idx].split(":"))
                except (TypeError, ValueError):
                    continue
                stop_times.append({
                    "trip_id": trip_id,
                    "route_id": trip["route_id"],
                    "departure_time": (h, m, s),
                    "headsign": parts[hs_idx] if hs_idx >= 0 and len(parts) > hs_idx else "",
                })

    departures = []
    
    for st in stop_times:
        trip_id = st["trip_id"]
        trip = tomorrow_trips[trip_id]
        
        route_id = st["route_id"]
        route_name = gtfs["routes"].get(route_id, {}).get("short_name", route_id)
        headsign = st.get("headsign") or trip.get("headsign", "")
        
        h, m, s = st["departure_time"]
        dep_dt = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=h, minutes=m, seconds=s)

        departures.append((dep_dt, {
            "route": route_name,
            "headsign": headsign,
            "estimated_time": dep_dt.isoformat(),
            "theoretical_time": dep_dt.isoformat(),
            "delay_seconds": 0,
            "realtime": False,
            "vehicle_type": gtfs["routes"].get(route_id, {}).get("type", "bus"),
            "provider": "schedule",
        }))

    departures.sort(key=lambda x: x[0])
    memo.clear()
    memo[memo_key] = departures
    return [d for dep_dt, d in departures if dep_dt >= now][:15]


# Bytes pulled from the end of a remote zip — enough for the central directory
# of a GTFS feed (~20 members), which is what zipfile needs to locate a member.
_ZIP_TAIL_BYTES = 65536


async def _fetch_range(session, url: str, start: int, end: int):
    """Fetch bytes [start, end] of a remote file. Returns (data, status) or (None, status)."""
    headers = {"Range": f"bytes={start}-{end}"}
    async with session.get(
        url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)
    ) as resp:
        if resp.status not in (200, 206):
            return None, resp.status
        return await resp.read(), resp.status


async def _peek_zip_member(session, url: str, size: int, member: str) -> str | None:
    """Read a single small member out of a remote zip using HTTP range requests.

    Avoids downloading the whole archive (GZM ships ~10 MB per zip, 20+ zips) just to
    read a few hundred bytes of calendar.txt. Returns the decoded text, or None if the
    member is absent or the server does not honour range requests.
    """
    tail_len = min(_ZIP_TAIL_BYTES, size)
    data, status = await _fetch_range(session, url, size - tail_len, size - 1)
    if data is None:
        return None

    if status == 200:
        # Server ignored the Range header and sent the whole archive.
        with zipfile.ZipFile(BytesIO(data)) as zf:
            return zf.read(member).decode("utf-8-sig")

    # Rebuild a sparse copy of the archive: only the regions we actually fetch are
    # populated, which is all zipfile touches (end-of-central-directory, then the
    # member's local header + data at its recorded offset). Slice assignment must stay
    # length-exact or every recorded offset shifts.
    if len(data) != tail_len:
        return None
    buf = bytearray(size)
    buf[size - tail_len:] = data

    with zipfile.ZipFile(BytesIO(bytes(buf))) as zf:
        info = zf.getinfo(member)

    start = info.header_offset
    # local header (30 B) + filename + extra field (padded) + compressed payload
    end = min(start + 30 + len(info.filename) + 128 + info.compress_size + 32, size - 1)
    chunk, _ = await _fetch_range(session, url, start, end)
    if chunk is None:
        return None
    buf[start:start + len(chunk)] = chunk

    with zipfile.ZipFile(BytesIO(bytes(buf))) as zf:
        return zf.read(member).decode("utf-8-sig")


def _calendar_covers(text: str, target) -> bool:
    """True if calendar.txt declares a service running on the target date."""
    day_name = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][target.weekday()]
    target_str = target.strftime("%Y%m%d")
    for row in csv.DictReader(StringIO(text)):
        if row.get(day_name) != "1":
            continue
        if (row.get("start_date") or "") <= target_str <= (row.get("end_date") or ""):
            return True
    return False


async def _get_gzm_gtfs_url(session, package_id: str, target_date=None) -> str | None:
    """Fetch the GZM GTFS URL covering target_date (default: today) from the CKAN API.

    GZM publishes one archive per service day rather than a single rolling feed, and the
    CKAN resource list is not ordered by the day each archive covers — its names only
    carry the *publication* date. Picking an arbitrary resource yields an archive whose
    calendar.txt does not include today, so every trip is filtered out as inactive and
    the stop reports no departures (issue #13). Probe each candidate's calendar.txt and
    take the first one that actually covers the day we need.
    """
    try:
        ckan_url = f"https://otwartedane.metropoliagzm.pl/api/3/action/package_show?id={package_id}"
        async with session.get(ckan_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()

        resources = [
            r
            for r in data.get("result", {}).get("resources", [])
            if "schedule" in (r.get("name") or "").lower()
            and (r.get("format") or "").lower() == "zip"
        ]
        if not resources:
            return None

        if target_date is None:
            target_date = dt_util.now().date()

        # Most recently published first, so a re-issued archive wins over a stale one.
        resources.sort(key=lambda r: r.get("last_modified") or r.get("created") or "", reverse=True)

        for r in resources:
            url, size = r.get("url"), r.get("size")
            if not url or not size:
                continue
            try:
                calendar = await _peek_zip_member(session, url, int(size), "calendar.txt")
            except (KeyError, zipfile.BadZipFile, aiohttp.ClientError, OSError) as e:
                _LOGGER.debug("GZM: could not inspect %s: %s", r.get("name"), e)
                continue
            if calendar and _calendar_covers(calendar, target_date):
                _LOGGER.debug("GZM: using %s for %s", r.get("name"), target_date)
                return url

        _LOGGER.warning(
            "GZM: no GTFS archive covers %s; falling back to most recent (%s)",
            target_date,
            resources[0].get("name"),
        )
        return resources[0].get("url")
    except Exception as e:
        _LOGGER.debug("GZM CKAN lookup failed: %s", e)
        return None


def _gtfs_cache_path(coord) -> Path | None:
    """Return the on-disk GTFS fallback path, or None in minimal/test setups."""
    try:
        base = coord.hass.config.path(".storage", DOMAIN, "gtfs")
    except Exception:
        return None
    if not isinstance(base, str):
        return None
    return Path(base) / f"{coord.provider}.zip"


async def _save_gtfs_cache(coord, data: bytes) -> None:
    """Persist a downloaded GTFS archive so departures survive an outage."""
    path = _gtfs_cache_path(coord)
    if path is None:
        return

    def _write() -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(data)
        tmp.replace(path)

    try:
        await coord.hass.async_add_executor_job(_write)
    except Exception as err:
        _LOGGER.debug("GTFS-RT: could not cache GTFS for %s: %s", coord.provider, err)


async def _load_gtfs_cache(coord) -> bytes | None:
    """Return the last successfully downloaded GTFS archive, if any."""
    path = _gtfs_cache_path(coord)
    if path is None:
        return None

    def _read() -> bytes | None:
        return path.read_bytes() if path.exists() else None

    try:
        return await coord.hass.async_add_executor_job(_read)
    except Exception as err:
        _LOGGER.debug("GTFS-RT: could not read cached GTFS for %s: %s", coord.provider, err)
        return None


async def _get_gtfs_data(coord, session, city_cfg, now):
    """Load GTFS data once when several stops of one provider refresh concurrently."""
    locks = coord.hass.data[DOMAIN].setdefault("_gtfsrt_locks", {})
    lock = locks.setdefault(coord.provider, asyncio.Lock())
    async with lock:
        return await _get_gtfs_data_locked(coord, session, city_cfg, now)


async def _get_gtfs_data_locked(coord, session, city_cfg, now):
    """Load and cache parsed GTFS data (daily)."""
    cache = coord.hass.data[DOMAIN].setdefault("_gtfsrt_cache", {})
    today = now.strftime("%Y%m%d")
    cache_key = f"{coord.provider}_{today}"

    if cache.get(cache_key):
        gtfs = cache[cache_key]
        # Parse stop_times for this specific stop if not already done
        if coord.stop_id not in gtfs["stop_times"] and gtfs.get("_raw"):
            await coord.hass.async_add_executor_job(
                _parse_stop_times_for, gtfs, coord.stop_id
            )
        return gtfs

    # Clean old cache entries for this provider (memory leak fix)
    prefix = f"{coord.provider}_"
    for old_key in list(cache.keys()):
        if old_key.startswith(prefix) and old_key != cache_key:
            old_gtfs = cache.pop(old_key, None)
            if old_gtfs:
                # Free raw zip memory
                old_gtfs.pop("_raw", None)
                old_gtfs.pop("_raw_tram", None)
            _LOGGER.debug("Cleaned old GTFS cache: %s", old_key)

    try:
        gtfs_url = city_cfg.get("gtfs_url")
        
        # Dynamic URL for GZM — must be the archive covering today's service day
        if not gtfs_url and city_cfg.get("gtfs_package_id"):
            gtfs_url = await _get_gzm_gtfs_url(session, city_cfg["gtfs_package_id"], now.date())
            if not gtfs_url:
                raise RuntimeError("could not get dynamic GTFS URL for GZM")

        async with session.get(gtfs_url, timeout=aiohttp.ClientTimeout(total=120)) as resp:
            if resp.status != 200:
                raise RuntimeError(f"GTFS download returned HTTP {resp.status}")
            data = await resp.read()

        gtfs = await coord.hass.async_add_executor_job(_parse_gtfs_zip, data)
        await _save_gtfs_cache(coord, data)

        # Merge secondary GTFS zip (e.g. Kraków tram)
        if city_cfg.get("gtfs_url_tram"):
            try:
                async with session.get(city_cfg["gtfs_url_tram"], timeout=aiohttp.ClientTimeout(total=120)) as resp2:
                    if resp2.status == 200:
                        data2 = await resp2.read()
                        gtfs2 = await coord.hass.async_add_executor_job(_parse_gtfs_zip, data2)
                        gtfs["stops"].update(gtfs2["stops"])
                        gtfs["routes"].update(gtfs2["routes"])
                        gtfs["trips"].update(gtfs2["trips"])
                        # Store secondary raw zip for stop_times parsing
                        gtfs["_raw_tram"] = data2
            except Exception as e:
                _LOGGER.debug("GTFS-RT: failed to load tram GTFS for %s: %s", coord.provider, e)

        cache[cache_key] = gtfs
        # Parse stop_times for current stop
        if coord.stop_id not in gtfs["stop_times"]:
            await coord.hass.async_add_executor_job(
                _parse_stop_times_for, gtfs, coord.stop_id
            )
        return gtfs
    except Exception as e:
        _LOGGER.warning("GTFS-RT: failed to load GTFS for %s: %s", coord.provider, e)
        # Offline/outage fallback: keep serving the last downloaded schedule.
        cached = await _load_gtfs_cache(coord)
        if cached:
            try:
                gtfs = await coord.hass.async_add_executor_job(_parse_gtfs_zip, cached)
                cache[cache_key] = gtfs
                if coord.stop_id not in gtfs["stop_times"]:
                    await coord.hass.async_add_executor_job(
                        _parse_stop_times_for, gtfs, coord.stop_id
                    )
                _LOGGER.info("GTFS-RT: using cached GTFS for %s", coord.provider)
                return gtfs
            except Exception as cache_err:
                _LOGGER.debug("GTFS-RT: cached GTFS unusable for %s: %s", coord.provider, cache_err)
        return cache.get(cache_key)


def _parse_gtfs_zip(data: bytes) -> dict:
    """Parse relevant GTFS files from zip."""
    stops = {}
    routes = {}
    trips = {}
    stop_times = {}  # stop_id -> list of {trip_id, route_id, departure_time, headsign}
    raw_zip = data
    today = dt_util.now().date()
    today_str = today.strftime("%Y%m%d")
    day_name = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][today.weekday()]

    with zipfile.ZipFile(BytesIO(data)) as zf:
        # calendar.txt — active services
        active_services = set()
        has_calendar = False
        any_weekday_match = False
        header, rows = _read_csv(zf, "calendar.txt")
        if header:
            has_calendar = True
            sid_idx = header.index("service_id")
            day_idx = header.index(day_name) if day_name in header else -1
            start_idx = header.index("start_date") if "start_date" in header else -1
            end_idx = header.index("end_date") if "end_date" in header else -1
            for parts in rows:
                if len(parts) <= sid_idx:
                    continue
                svc = parts[sid_idx]
                active = day_idx >= 0 and len(parts) > day_idx and parts[day_idx] == "1"
                if active:
                    any_weekday_match = True
                if active and start_idx >= 0 and end_idx >= 0 and len(parts) > max(start_idx, end_idx):
                    if parts[start_idx] > today_str or parts[end_idx] < today_str:
                        active = False
                if active:
                    active_services.add(svc)

        # calendar_dates.txt — exceptions
        header, rows = _read_csv(zf, "calendar_dates.txt")
        if header:
            has_calendar = True
            sid_idx = header.index("service_id")
            date_idx = header.index("date")
            etype_idx = header.index("exception_type")
            for parts in rows:
                if len(parts) <= max(sid_idx, date_idx, etype_idx):
                    continue
                if parts[date_idx] != today_str:
                    continue
                svc = parts[sid_idx]
                if parts[etype_idx] == "1":
                    active_services.add(svc)
                elif parts[etype_idx] == "2":
                    active_services.discard(svc)

        # stops.txt
        header, rows = _read_csv(zf, "stops.txt")
        if header:
            id_idx = header.index("stop_id")
            name_idx = header.index("stop_name")
            for parts in rows:
                if len(parts) > max(id_idx, name_idx):
                    stops[parts[id_idx]] = {"name": parts[name_idx]}

        # routes.txt
        header, rows = _read_csv(zf, "routes.txt")
        if header:
            id_idx = header.index("route_id")
            sn_idx = header.index("route_short_name") if "route_short_name" in header else -1
            rt_idx = header.index("route_type") if "route_type" in header else -1
            for parts in rows:
                if len(parts) > id_idx:
                    rid = parts[id_idx]
                    short = parts[sn_idx] if sn_idx >= 0 and len(parts) > sn_idx else rid
                    rtype = "tram" if rt_idx >= 0 and len(parts) > rt_idx and parts[rt_idx] == "0" else "bus"
                    routes[rid] = {"short_name": short, "type": rtype}

        # trips.txt
        header, rows = _read_csv(zf, "trips.txt")
        if header:
            tid_idx = header.index("trip_id")
            rid_idx = header.index("route_id")
            hs_idx = header.index("trip_headsign") if "trip_headsign" in header else -1
            svc_idx = header.index("service_id") if "service_id" in header else -1
            wc_idx = header.index("wheelchair_accessible") if "wheelchair_accessible" in header else -1
            bike_idx = header.index("bikes_allowed") if "bikes_allowed" in header else -1
            # Some feeds (notably the zbiorkom.live api6 exports) only ship
            # calendar_dates.txt. There is no weekday column to match, but the
            # exception rows still tell us which services run today. Without this,
            # every trip from every service day is shown (issues #32/#33).
            filter_by_service = has_calendar and (any_weekday_match or bool(active_services))
            for parts in rows:
                if len(parts) > max(tid_idx, rid_idx):
                    tid = parts[tid_idx]
                    if filter_by_service and svc_idx >= 0 and len(parts) > svc_idx:
                        if parts[svc_idx] not in active_services:
                            continue
                    rid = parts[rid_idx]
                    hs = parts[hs_idx] if hs_idx >= 0 and len(parts) > hs_idx else ""
                    trip = {"route_id": rid, "headsign": hs}
                    if wc_idx >= 0 and len(parts) > wc_idx and parts[wc_idx] == "1":
                        trip["wheelchair"] = True
                    if bike_idx >= 0 and len(parts) > bike_idx and parts[bike_idx] == "1":
                        trip["bike"] = True
                    trips[tid] = trip

        # Store raw zip for on-demand stop_times parsing
        raw_zip = data

    return {"stops": stops, "routes": routes, "trips": trips, "stop_times": stop_times, "_raw": raw_zip}


def _parse_stop_times_for(gtfs, stop_id):
    """Parse stop_times from cached raw zip for a specific stop."""
    raw = gtfs.get("_raw")
    if not raw:
        return
    trips = gtfs["trips"]
    stops = gtfs["stops"]
    with zipfile.ZipFile(BytesIO(raw)) as zf:
        header, rows = _read_csv(zf, "stop_times.txt")
        if not header:
            return
        tid_idx = header.index("trip_id")
        sid_idx = header.index("stop_id")
        dep_idx = header.index("departure_time")
        hs_idx = header.index("stop_headsign") if "stop_headsign" in header else -1
        seq_idx = header.index("stop_sequence") if "stop_sequence" in header else -1

        # First pass: collect our stop's entries + track last stop per trip (for headsign)
        our_entries = []
        last_seq_per_trip = {}  # trip_id -> (max_seq, stop_id)
        need_headsign = set()

        for parts in rows:
            if len(parts) <= max(tid_idx, sid_idx, dep_idx):
                continue
            tid = parts[tid_idx]
            if tid not in trips:
                continue
            sid = parts[sid_idx]
            seq = int(parts[seq_idx]) if seq_idx >= 0 and len(parts) > seq_idx and parts[seq_idx].isdigit() else 0

            if sid == stop_id:
                dep_str = parts[dep_idx]
                try:
                    h, m, s = [int(x) for x in dep_str.split(":")]
                except (ValueError, IndexError):
                    continue
                hs = ""
                if hs_idx >= 0 and len(parts) > hs_idx:
                    hs = parts[hs_idx]
                hs = hs or trips[tid].get("headsign", "")
                our_entries.append({"trip_id": tid, "route_id": trips[tid].get("route_id", ""), "departure_time": (h, m, s), "headsign": hs, "stop_sequence": str(seq)})
                if not hs:
                    need_headsign.add(tid)

            # Track last stop for trips needing headsign
            if tid in need_headsign or (sid == stop_id and not trips[tid].get("headsign")):
                prev = last_seq_per_trip.get(tid, (-1, ""))
                if seq > prev[0]:
                    last_seq_per_trip[tid] = (seq, sid)

        # Fill in headsigns from last stop name
        if need_headsign and last_seq_per_trip:
            for entry in our_entries:
                if not entry["headsign"] and entry["trip_id"] in last_seq_per_trip:
                    last_sid = last_seq_per_trip[entry["trip_id"]][1]
                    entry["headsign"] = stops.get(last_sid, {}).get("name", "")

        gtfs["stop_times"][stop_id] = our_entries

    # Also parse from secondary (tram) zip if present
    if gtfs.get("_raw_tram"):
        _parse_stop_times_from_raw(gtfs, stop_id, gtfs["_raw_tram"])


def _parse_stop_times_from_raw(gtfs, stop_id, raw_data):
    """Parse stop_times from a raw GTFS zip and append to gtfs['stop_times'][stop_id]."""
    trips = gtfs["trips"]
    stops = gtfs["stops"]
    with zipfile.ZipFile(BytesIO(raw_data)) as zf:
        header, rows = _read_csv(zf, "stop_times.txt")
        if not header:
            return
        tid_idx = header.index("trip_id")
        sid_idx = header.index("stop_id")
        dep_idx = header.index("departure_time")
        hs_idx = header.index("stop_headsign") if "stop_headsign" in header else -1
        seq_idx = header.index("stop_sequence") if "stop_sequence" in header else -1

        our_entries = []
        last_seq_per_trip = {}
        need_headsign = set()

        for parts in rows:
            if len(parts) <= max(tid_idx, sid_idx, dep_idx):
                continue
            tid = parts[tid_idx]
            if tid not in trips:
                continue
            sid = parts[sid_idx]
            seq = int(parts[seq_idx]) if seq_idx >= 0 and len(parts) > seq_idx and parts[seq_idx].isdigit() else 0

            if sid == stop_id:
                dep_str = parts[dep_idx]
                try:
                    h, m, s = [int(x) for x in dep_str.split(":")]
                except (ValueError, IndexError):
                    continue
                hs = ""
                if hs_idx >= 0 and len(parts) > hs_idx:
                    hs = parts[hs_idx]
                hs = hs or trips[tid].get("headsign", "")
                our_entries.append({"trip_id": tid, "route_id": trips[tid].get("route_id", ""), "departure_time": (h, m, s), "headsign": hs, "stop_sequence": str(seq)})
                if not hs:
                    need_headsign.add(tid)

            if tid in need_headsign or (sid == stop_id and not trips[tid].get("headsign")):
                prev = last_seq_per_trip.get(tid, (-1, ""))
                if seq > prev[0]:
                    last_seq_per_trip[tid] = (seq, sid)

        if need_headsign and last_seq_per_trip:
            for entry in our_entries:
                if not entry["headsign"] and entry["trip_id"] in last_seq_per_trip:
                    last_sid = last_seq_per_trip[entry["trip_id"]][1]
                    entry["headsign"] = stops.get(last_sid, {}).get("name", "")

        gtfs["stop_times"].setdefault(stop_id, []).extend(our_entries)


async def _get_vehicle_dict(coord, session, city_cfg) -> dict:
    """Load and cache vehicle capabilities dictionary (CSV or JSON)."""
    cache = coord.hass.data[DOMAIN].setdefault("_gtfsrt_vehicles", {})
    cache_key = coord.provider
    
    # TTL check (1 hour)
    cached = cache.get(cache_key)
    if cached and isinstance(cached, dict):
        ts = cached.get("_ts", 0)
        if ts and (dt_util.now().timestamp() - ts < 3600):
            return cached.get("data", {})
    
    try:
        async with session.get(city_cfg["vehicles_url"], timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                return {}
            text = await resp.text()

        if city_cfg.get("vehicles_format") == "json":
            import json
            raw = json.loads(text)
            result = {}
            for _key, v in raw.items():
                num = v.get("num", "")
                if not num or num.startswith("??"):
                    continue
                low = v.get("low")
                result[num] = {
                    "hf_lf_le": low == 2,
                    "ramp": low in (1, 2),
                    "vehicle_model": v.get("type", ""),
                }
            cache[cache_key] = {"data": result, "_ts": dt_util.now().timestamp()}
            return result

        if city_cfg.get("vehicles_format") == "ttss_positions":
            import json
            raw = json.loads(text)
            pos = raw.get("pos", {})
            result = {}
            # Also fetch tram positions if configured
            urls = [city_cfg["vehicles_url"]]
            if city_cfg.get("vehicles_url_tram"):
                urls.append(city_cfg["vehicles_url_tram"])
            # Parse first response (already fetched)
            for _vid, v in pos.items():
                vtype = v.get("type", {})
                num = vtype.get("num", "")
                if not num or num.startswith("??"):
                    continue
                low = vtype.get("low")
                ac = vtype.get("ac")
                result[num] = {
                    "hf_lf_le": low == 2,
                    "ramp": low in (1, 2),
                    "air_conditioner": ac in (1, 2),
                    "vehicle_model": vtype.get("type", ""),
                }
            # Fetch tram positions if separate URL
            if city_cfg.get("vehicles_url_tram"):
                try:
                    async with session.get(city_cfg["vehicles_url_tram"], timeout=aiohttp.ClientTimeout(total=15)) as resp2:
                        if resp2.status == 200:
                            text2 = await resp2.text()
                            raw2 = json.loads(text2)
                            for _vid, v in raw2.get("pos", {}).items():
                                vtype = v.get("type", {})
                                num = vtype.get("num", "")
                                if not num or num.startswith("??"):
                                    continue
                                low = vtype.get("low")
                                ac = vtype.get("ac")
                                result[num] = {
                                    "hf_lf_le": low == 2,
                                    "ramp": low in (1, 2),
                                    "air_conditioner": ac in (1, 2),
                                    "vehicle_model": vtype.get("type", ""),
                                }
                except Exception as exc:
                    _LOGGER.debug("Failed to load tram vehicles: %s", exc)
            cache[cache_key] = {"data": result, "_ts": dt_util.now().timestamp()}
            return result

        # Default: CSV format (Poznań)
        lines = text.strip().splitlines()
        header = lines[0].split(",")
        veh_idx = header.index("vehicle") if "vehicle" in header else 0
        result = {}
        for line in lines[1:]:
            parts = line.split(",")
            if len(parts) <= veh_idx:
                continue
            vid = parts[veh_idx].strip()
            row = {}
            for i, col in enumerate(header):
                if i != veh_idx and i < len(parts):
                    row[col.strip()] = parts[i].strip() == "1"
            result[vid] = row
        cache[cache_key] = {"data": result, "_ts": dt_util.now().timestamp()}
        return result
    except Exception:
        return {}


async def _enrich_with_gps_positions(coord, session, city_cfg, departures):
    """Fetch vehicle GPS positions and enrich departures with vehicle_lat/lng."""
    url = city_cfg.get("positions_url")
    if not url or not departures:
        return

    cache = coord.hass.data[DOMAIN].setdefault("_gtfsrt_positions", {})
    now_ts = dt_util.now().timestamp()
    cached = cache.get(coord.provider)
    if cached and now_ts - cached.get("_ts", 0) < 30:
        _apply_positions(departures, cached.get("data", {}))
        return

    positions = {}
    try:
        if "/api/v2/vehicles" in url:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for item in data.get("data", []):
                        vn = item.get("vehicle", {}).get("number")
                        pos = item.get("position", {})
                        if vn and "latitude" in pos and "longitude" in pos:
                            positions[str(vn)] = {"lat": pos["latitude"], "lng": pos["longitude"], "bearing": pos.get("bearing"), "speed": pos.get("velocity")}
        elif "positions.json" in url:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for p in data.get("positions", []):
                        sn = p.get("side_number")
                        tid = p.get("trip_id")
                        lat = p.get("lat")
                        lon = p.get("lon")
                        if not lat or not lon:
                            continue
                        entry = {"lat": lat, "lng": lon, "bearing": p.get("bearing")}
                        if sn:
                            positions[str(sn)] = entry
                        if tid:
                            positions[tid] = entry
        elif city_cfg.get("positions_format") == "gtfsrt_protobuf" or url.endswith(".pb"):
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    positions = _parse_gtfsrt_positions(await resp.read())
        _apply_positions(departures, positions)
        cache[coord.provider] = {"data": positions, "_ts": now_ts}
    except Exception as e:
        _LOGGER.debug("GPS positions failed for %s: %s", coord.provider, e)


def _parse_gtfsrt_positions(raw):
    """Parse a GTFS-RT VehiclePositions payload into positions keyed by vehicle ID."""
    from google.transit import gtfs_realtime_pb2

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(raw)
    positions = {}
    for entity in feed.entity:
        if not entity.HasField("vehicle"):
            continue
        vehicle = entity.vehicle
        vehicle_id = vehicle.vehicle.id or vehicle.vehicle.label or ""
        vehicle_id = vehicle_id.split("/")[-1] if "/" in vehicle_id else vehicle_id
        if not vehicle_id or not vehicle.HasField("position"):
            continue
        entry = {
            "lat": vehicle.position.latitude,
            "lng": vehicle.position.longitude,
        }
        try:
            entry["bearing"] = vehicle.position.bearing if vehicle.position.HasField("bearing") else None
        except (ValueError, AttributeError):
            pass
        try:
            entry["speed"] = vehicle.position.speed if vehicle.position.HasField("speed") else None
        except (ValueError, AttributeError):
            pass
        if vehicle.HasField("trip") and vehicle.trip.route_id:
            entry["route_id"] = vehicle.trip.route_id
        positions[vehicle_id] = entry
    return positions


def _apply_positions(departures, positions):
    """Add vehicle_lat/lng to departures matching positions by vehicle_code (or route_id fallback)."""
    # Build route_id → best position map for cities without vehicle_code (e.g. Wrocław)
    route_positions = {}
    for vid, entry in positions.items():
        rid = entry.get("route_id")
        if rid:
            route_positions.setdefault(rid, []).append(entry)

    for d in departures:
        vc = d.get("vehicle_code", "")
        tid = d.get("trip_id", "")
        p = None
        if vc and vc in positions:
            p = positions[vc]
        elif tid and tid in positions:
            p = positions[tid]
        elif not vc:
            rid = d.get("route", "")
            candidates = route_positions.get(rid, [])
            if candidates:
                p = candidates[0]
                candidates.append(candidates.pop(0))  # round-robin
        if p is None:
            continue
        d["vehicle_lat"] = p["lat"]
        d["vehicle_lng"] = p["lng"]
        if p.get("bearing") is not None:
            d["vehicle_direction"] = p["bearing"]
        if p.get("speed") is not None:
            d["vehicle_speed"] = round(p["speed"] * 3.6)


async def _get_rt_delays(session, rt_url: str) -> dict:
    """Fetch GTFS-RT TripUpdates and return {trip_id_stop_id: delay_seconds}."""
    from google.transit import gtfs_realtime_pb2
    
    last_err = None
    for attempt in range(3):
        try:
            async with session.get(rt_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return {}
                data = await resp.read()

            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(data)
            return _parse_rt_feed(feed)
        except (aiohttp.ClientConnectorError, aiohttp.ServerDisconnectedError, asyncio.TimeoutError) as e:
            last_err = e
            if attempt < 2:
                _LOGGER.debug("GTFS-RT attempt %d failed: %s, retrying...", attempt + 1, e)
                await asyncio.sleep([1, 3, 7][attempt])
        except Exception as e:
            # A retired/HTML feed must not spam the log on every 30 s poll. The static
            # schedule still works, so this is a degraded state, not a failure.
            _LOGGER.debug("GTFS-RT: failed to parse RT data from %s: %s", rt_url, e)
            return {}
    
    if last_err:
        _LOGGER.debug("GTFS-RT: all retries failed for %s: %s", rt_url, last_err)
    return {}


def _parse_rt_feed(feed) -> dict:
    """Parse a GTFS-RT FeedMessage into {key: (delay, vehicle_label)} with route-level fallback."""
    delays = {}
    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue
        trip_id = entity.trip_update.trip.trip_id
        route_id = entity.trip_update.trip.route_id if entity.trip_update.trip.route_id else ""
        vehicle_label = ""
        if entity.trip_update.HasField("vehicle"):
            v = entity.trip_update.vehicle
            vid = v.id or v.label or ""
            vehicle_label = vid.split("/")[-1] if "/" in vid else vid
        for stu in entity.trip_update.stop_time_update:
            delay = stu.departure.delay if stu.HasField("departure") else (stu.arrival.delay if stu.HasField("arrival") else 0)
            if stu.stop_id:
                delays[f"{trip_id}_{stu.stop_id}"] = (delay, vehicle_label)
                if route_id:
                    delays[f"route_{route_id}_{stu.stop_id}"] = (delay, vehicle_label)
            if stu.stop_sequence:
                delays[f"{trip_id}_seq{stu.stop_sequence}"] = (delay, vehicle_label)
            delays[trip_id] = (delay, vehicle_label)
            if route_id:
                delays[f"route_{route_id}"] = (delay, vehicle_label)
    return delays
