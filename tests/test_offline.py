"""Tests for the persistent offline schedule snapshots."""

from datetime import datetime
from types import SimpleNamespace

import pytest

from mzkzg_transport.offline import (
    async_has_snapshot,
    async_load_snapshot,
    async_save_snapshot,
    replay_snapshot,
)


class FakeHass:
    def __init__(self, root):
        self.config = SimpleNamespace(path=lambda *parts: str(root.joinpath(*parts)))

    async def async_add_executor_job(self, func, *args):
        return func(*args)


NOW = datetime(2026, 11, 9, 12, 0, 0)


@pytest.mark.asyncio
async def test_snapshot_round_trip_filters_volatile_fields(tmp_path):
    hass = FakeHass(tmp_path)
    departures = [
        {
            "route": "6",
            "headsign": "Jelitkowo",
            "theoretical_time": "2026-11-09T12:05:00",
            "estimated_time": "2026-11-09T12:07:00",
            "realtime": True,
            "delay_seconds": 120,
            "vehicle_code": "1026",
            "vehicle_lat": 54.1,
            "vehicle_lng": 18.2,
            "wheelchair_accessible": True,
        },
        {
            "route": "6",
            "headsign": "Jelitkowo",
            "theoretical_time": "2026-11-09T12:05:00",
        },
        {"route": "7", "headsign": "No time"},
    ]

    assert await async_save_snapshot(
        hass, "ztm_gdansk", "2230", "Płocka 01", departures, now=NOW
    )
    snapshot = await async_load_snapshot(hass, "ztm_gdansk", "2230")

    assert snapshot is not None
    assert snapshot["stop_name"] == "Płocka 01"
    assert len(snapshot["departures"]) == 1
    row = snapshot["departures"][0]
    assert row["route"] == "6"
    assert row["wheelchair_accessible"] is True
    assert "vehicle_code" not in row
    assert "realtime" not in row
    assert await async_has_snapshot(hass, "ztm_gdansk", "2230") is True
    assert await async_has_snapshot(hass, "ztm_gdansk", "9999") is False


@pytest.mark.asyncio
async def test_snapshot_ignores_empty_and_broken_files(tmp_path):
    hass = FakeHass(tmp_path)

    assert not await async_save_snapshot(hass, "x", "1", "Stop", [])
    assert await async_load_snapshot(hass, "x", "1") is None

    path = tmp_path / ".storage" / "mzkzg_transport" / "offline" / "x__2.json"
    path.parent.mkdir(parents=True)
    path.write_text("{not-json", encoding="utf-8")
    assert await async_load_snapshot(hass, "x", "2") is None


def test_replay_snapshot_shifts_to_today_and_marks_offline():
    snapshot = {
        "provider": "ztm_gdansk",
        "stop_id": "2230",
        "stop_name": "Płocka 01",
        "saved_at": "2026-11-08T18:00:00",
        "departures": [
            {"time": "2026-11-08T12:30:00", "route": "6", "headsign": "Jelitkowo"},
            {"time": "2026-11-08T13:15:00", "route": "3", "headsign": "Nowy Port"},
        ],
    }

    data = replay_snapshot(snapshot, NOW)

    assert data["offline"] is True
    assert data["offline_saved_at"] == "2026-11-08T18:00:00"
    assert data["stop_name"] == "Płocka 01"
    assert [row["route"] for row in data["departures"]] == ["6", "3"]
    assert data["departures"][0]["estimated_time"].startswith("2026-11-09T12:30")
    assert all(row["realtime"] is False for row in data["departures"])
    assert all(row["offline"] is True for row in data["departures"])


def test_replay_snapshot_rolls_past_times_to_tomorrow():
    snapshot = {
        "provider": "x",
        "stop_id": "1",
        "stop_name": "Stop",
        "saved_at": "2026-11-09T10:00:00",
        "departures": [
            {"time": "2026-11-09T08:00:00", "route": "1", "headsign": "A"},
        ],
    }

    data = replay_snapshot(snapshot, NOW)

    assert data["departures"][0]["estimated_time"].startswith("2026-11-10T08:00")
