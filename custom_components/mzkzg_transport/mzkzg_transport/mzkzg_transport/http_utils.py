"""Shared HTTP utilities for providers."""

import asyncio
import logging

import aiohttp

_LOGGER = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAYS = (1, 3, 7)


async def fetch_with_retry(session: aiohttp.ClientSession, url: str, timeout: float = 15, as_text: bool = False) -> dict | str:
    """Fetch URL with retry on connection errors."""
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                resp.raise_for_status()
                return await resp.text() if as_text else await resp.json()
        except (aiohttp.ClientConnectorError, aiohttp.ServerDisconnectedError, asyncio.TimeoutError) as err:
            last_err = err
            if attempt < MAX_RETRIES - 1:
                _LOGGER.debug("API attempt %d failed: %s, retrying...", attempt + 1, err)
                await asyncio.sleep(RETRY_DELAYS[attempt])
    raise last_err
