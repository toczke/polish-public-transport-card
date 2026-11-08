"""Memory and cache-bound regression tests."""

import gc
import io
import tracemalloc
import zipfile
from datetime import datetime

from mzkzg_transport.gtfsrt_parser import (
    _parse_gtfs_zip,
    _parse_stop_times_for,
    _release_gtfs_raw,
)
from mzkzg_transport.provider_kiedyprzyjedzie import (
    TIMETABLE_CACHE_TTL,
    TIMETABLE_MAX_CACHE_ENTRIES,
    _prune_timetable_cache,
)


def _gtfs_zip(rows: int = 1500) -> bytes:
    day = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][
        datetime.now().weekday()
    ]
    stop_times = ["trip_id,stop_id,departure_time,stop_sequence"]
    for index in range(rows):
        stop_times.append(f"T{index % 50},S1,{8 + index // 60:02d}:{index % 60:02d}:00,1")
        stop_times.append(f"T{index % 50},S2,{8 + index // 60:02d}:{index % 60 + 5:02d}:00,2")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("stops.txt", "stop_id,stop_name\nS1,One\nS2,Two\n")
        archive.writestr("routes.txt", "route_id,route_short_name,route_type\nR1,10,3\n")
        archive.writestr(
            "trips.txt",
            "trip_id,route_id,service_id,trip_headsign\n"
            + "".join(f"T{i},R1,SVC1,Centrum\n" for i in range(50)),
        )
        archive.writestr(
            "calendar.txt",
            f"service_id,{day},start_date,end_date\nSVC1,1,20200101,29991231\n",
        )
        archive.writestr("stop_times.txt", "\n".join(stop_times) + "\n")
    return buffer.getvalue()


def test_release_gtfs_raw_drops_archive():
    gtfs = _parse_gtfs_zip(_gtfs_zip())
    _parse_stop_times_for(gtfs, "S1")
    assert gtfs["_raw"]

    _release_gtfs_raw(gtfs, ["S1"], datetime.now())

    assert "_raw" not in gtfs
    assert "_raw_tram" not in gtfs


def test_repeated_parse_and_release_does_not_accumulate_memory():
    data = _gtfs_zip()
    # Warm up allocator pools before taking the baseline.
    gtfs = _parse_gtfs_zip(data)
    _parse_stop_times_for(gtfs, "S1")
    _release_gtfs_raw(gtfs, ["S1"], datetime.now())
    del gtfs
    gc.collect()

    tracemalloc.start()
    baseline = tracemalloc.get_traced_memory()[0]
    try:
        for _ in range(20):
            gtfs = _parse_gtfs_zip(data)
            _parse_stop_times_for(gtfs, "S1")
            _release_gtfs_raw(gtfs, ["S1"], datetime.now())
            del gtfs
            gc.collect()
        current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    # Peak is allowed to be larger, but after release and GC nothing may pile up.
    assert current - baseline < 1_500_000
    assert peak < 12_000_000


def test_timetable_cache_drops_expired_entries():
    now = 10_000.0
    cache = {
        index: {"rows": [], "_ts": now - TIMETABLE_CACHE_TTL - index}
        for index in range(10)
    }
    _prune_timetable_cache(cache, now)
    assert cache == {}


def test_timetable_cache_is_capped():
    now = 10_000.0
    cache = {index: {"rows": [], "_ts": now - index} for index in range(800)}

    _prune_timetable_cache(cache, now)

    assert len(cache) == TIMETABLE_MAX_CACHE_ENTRIES
    assert 0 in cache  # newest entry stays
    assert 799 not in cache  # oldest entry is gone
