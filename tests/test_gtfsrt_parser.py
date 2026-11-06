"""Pytest unit tests for gtfsrt_parser module."""
import sys
import os
import io
import zipfile
from datetime import date

# Direct import - gtfsrt_parser has no HA dependencies
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'mzkzg_transport'))
from gtfsrt_parser import _read_csv, _parse_gtfs_zip, _parse_stop_times_for


# ─── Helpers ────────────────────────────────────────────────────────────────

def _make_zip(files: dict) -> bytes:
    """Build an in-memory ZIP with the given filename→content mapping."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def _today() -> str:
    return date.today().strftime('%Y%m%d')


def _today_day_name() -> str:
    return ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'][date.today().weekday()]


# ─── _read_csv tests ─────────────────────────────────────────────────────────

def test_read_csv_missing_file():
    """Returns (None, empty iterator) when file not in zip."""
    data = _make_zip({'other.txt': 'a,b\n1,2\n'})
    buf = io.BytesIO(data)
    with zipfile.ZipFile(buf) as zf:
        header, rows = _read_csv(zf, 'missing.txt')
    assert header is None
    assert list(rows) == []


def test_read_csv_valid():
    """Correctly reads header and rows."""
    data = _make_zip({'stops.txt': 'stop_id,stop_name\nS1,Main St\nS2,Park Ave\n'})
    buf = io.BytesIO(data)
    with zipfile.ZipFile(buf) as zf:
        header, rows = _read_csv(zf, 'stops.txt')
    assert header == ['stop_id', 'stop_name']
    assert list(rows) == [['S1', 'Main St'], ['S2', 'Park Ave']]


def test_read_csv_utf8_bom():
    """Handles UTF-8 BOM (common in Polish GTFS files)."""
    content = '\ufeffstop_id,stop_name\nS1,Gorna\n'
    data = _make_zip({'stops.txt': content})
    buf = io.BytesIO(data)
    with zipfile.ZipFile(buf) as zf:
        header, rows = _read_csv(zf, 'stops.txt')
    assert header[0] == 'stop_id'  # BOM stripped
    assert list(rows)[0][1] == 'Gorna'


# ─── _parse_gtfs_zip tests ───────────────────────────────────────────────────

def test_parse_gtfs_zip_returns_required_keys():
    """Result always has all expected keys."""
    data = _make_zip({})
    result = _parse_gtfs_zip(data)
    for key in ('stops', 'routes', 'trips', 'stop_times', '_raw'):
        assert key in result


def test_parse_gtfs_zip_empty_zip():
    """Handles zip with no relevant files gracefully."""
    data = _make_zip({})
    result = _parse_gtfs_zip(data)
    assert result['stops'] == {}
    assert result['routes'] == {}
    assert result['trips'] == {}
    assert result['stop_times'] == {}


def test_parse_gtfs_zip_stops():
    """Extracts stops from stops.txt."""
    data = _make_zip({
        'stops.txt': 'stop_id,stop_name\nS1,Plac Wolnosci\nS2,Rynek\n',
    })
    result = _parse_gtfs_zip(data)
    assert result['stops']['S1']['name'] == 'Plac Wolnosci'
    assert result['stops']['S2']['name'] == 'Rynek'


def test_parse_gtfs_zip_routes_with_color():
    """Parses route_color and prefixes with '#'."""
    data = _make_zip({
        'routes.txt': 'route_id,route_short_name,route_type,route_color\nR1,10,3,FF0000\n',
    })
    result = _parse_gtfs_zip(data)
    assert result['routes']['R1']['color'] == '#FF0000'


def test_parse_gtfs_zip_routes_no_color():
    """route dict has no color key when route_color is empty."""
    data = _make_zip({
        'routes.txt': 'route_id,route_short_name,route_type,route_color\nR1,10,3,\n',
    })
    result = _parse_gtfs_zip(data)
    assert 'color' not in result['routes']['R1']


def test_parse_gtfs_zip_routes_no_color_column():
    """route dict has no color key when column is absent."""
    data = _make_zip({
        'routes.txt': 'route_id,route_short_name,route_type\nR1,10,3\n',
    })
    result = _parse_gtfs_zip(data)
    assert 'color' not in result['routes']['R1']


def test_parse_gtfs_zip_tram_route_type():
    """route_type=0 maps to tram, others to bus."""
    data = _make_zip({
        'routes.txt': 'route_id,route_short_name,route_type\nT1,1,0\nB1,101,3\n',
    })
    result = _parse_gtfs_zip(data)
    assert result['routes']['T1']['type'] == 'tram'
    assert result['routes']['B1']['type'] == 'bus'


def test_parse_gtfs_zip_trips_with_active_calendar():
    """Only includes trips whose service_id is active today."""
    day_col = _today_day_name()
    calendar = (
        f'service_id,{day_col},start_date,end_date\n'
        f'SVC_A,1,20200101,29991231\n'
        f'SVC_B,0,20200101,29991231\n'
    )
    trips = (
        'trip_id,route_id,service_id,trip_headsign\n'
        'T1,R1,SVC_A,Downtown\n'
        'T2,R1,SVC_B,Airport\n'
    )
    data = _make_zip({
        'calendar.txt': calendar,
        'trips.txt': trips,
        'routes.txt': 'route_id,route_short_name\nR1,10\n',
    })
    result = _parse_gtfs_zip(data)
    assert 'T1' in result['trips']
    assert 'T2' not in result['trips']


def test_parse_gtfs_zip_calendar_dates_exception():
    """calendar_dates exception_type=2 removes, type=1 adds service."""
    today = _today()
    day_col = _today_day_name()
    calendar = (
        f'service_id,{day_col},start_date,end_date\n'
        f'SVC_A,1,20200101,29991231\n'
        f'SVC_B,0,20200101,29991231\n'
    )
    calendar_dates = f'service_id,date,exception_type\nSVC_A,{today},2\nSVC_B,{today},1\n'
    trips = 'trip_id,route_id,service_id\nT1,R1,SVC_A\nT2,R1,SVC_B\n'
    data = _make_zip({
        'calendar.txt': calendar,
        'calendar_dates.txt': calendar_dates,
        'trips.txt': trips,
        'routes.txt': 'route_id,route_short_name\nR1,10\n',
    })
    result = _parse_gtfs_zip(data)
    assert 'T1' not in result['trips']   # removed by exception
    assert 'T2' in result['trips']        # added by exception


# ─── _parse_stop_times_for tests ─────────────────────────────────────────────

def _make_full_gtfs() -> bytes:
    day_col = _today_day_name()
    calendar = f'service_id,{day_col},start_date,end_date\nSVC1,1,20200101,29991231\n'
    trips = 'trip_id,route_id,service_id,trip_headsign\nTRIP1,R1,SVC1,Centrum\n'
    routes = 'route_id,route_short_name\nR1,10\n'
    stops = 'stop_id,stop_name\nSTOP_A,Plac\nSTOP_B,Rynek\n'
    stop_times = (
        'trip_id,stop_id,departure_time,stop_sequence\n'
        'TRIP1,STOP_A,08:30:00,1\n'
        'TRIP1,STOP_B,08:45:00,2\n'
    )
    return _make_zip({
        'calendar.txt': calendar,
        'trips.txt': trips,
        'routes.txt': routes,
        'stops.txt': stops,
        'stop_times.txt': stop_times,
    })


def test_parse_stop_times_for_populates():
    """Populates stop_times for given stop_id from _raw."""
    data = _make_full_gtfs()
    gtfs = _parse_gtfs_zip(data)
    assert 'STOP_A' not in gtfs['stop_times']  # lazy-loaded
    _parse_stop_times_for(gtfs, 'STOP_A')
    assert 'STOP_A' in gtfs['stop_times']
    entries = gtfs['stop_times']['STOP_A']
    assert len(entries) == 1
    assert entries[0]['departure_time'] == (8, 30, 0)
    assert entries[0]['trip_id'] == 'TRIP1'


def test_parse_stop_times_for_no_raw():
    """Does nothing gracefully when _raw is missing."""
    gtfs = {'stops': {}, 'routes': {}, 'trips': {'T1': {}}, 'stop_times': {}}
    _parse_stop_times_for(gtfs, 'STOP_X')  # must not raise
    assert 'STOP_X' not in gtfs['stop_times']


def test_parse_stop_times_for_idempotent():
    """Calling twice doesn't duplicate entries."""
    data = _make_full_gtfs()
    gtfs = _parse_gtfs_zip(data)
    _parse_stop_times_for(gtfs, 'STOP_A')
    count_first = len(gtfs['stop_times']['STOP_A'])
    _parse_stop_times_for(gtfs, 'STOP_A')
    count_second = len(gtfs['stop_times']['STOP_A'])
    assert count_first == count_second
