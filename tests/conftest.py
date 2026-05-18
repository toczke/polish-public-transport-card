"""Pytest configuration."""

import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components"))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def pytest_configure(config):
    config.addinivalue_line("markers", "gdansk: ZTM Gdańsk tests")
    config.addinivalue_line("markers", "gdynia: ZKM Gdynia tests")
    config.addinivalue_line("markers", "tczew: Time4Bus Tczew tests")
    config.addinivalue_line("markers", "kiedyprzyjedzie: kiedyPrzyjedzie providers")
    config.addinivalue_line("markers", "gtfsrt: GTFS-RT providers")
    config.addinivalue_line("markers", "plk: PLK rail tests")
    config.addinivalue_line("markers", "common: common/shared tests")
