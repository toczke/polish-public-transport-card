"""Walking distance utilities for MZKZG Transport."""
import math


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance in meters (Haversine formula)."""
    R = 6_371_000  # Earth radius in metres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def walking_minutes(distance_m: float, speed_mpm: float = 80.0) -> int:
    """Convert distance in metres to estimated walking time in minutes.

    Default walking speed: 80 m/min ≈ 4.8 km/h (comfortable urban pace).
    """
    return max(1, round(distance_m / speed_mpm))


def stop_walking_info(
    home_lat: float | None,
    home_lon: float | None,
    stop_lat: float | None,
    stop_lon: float | None,
) -> dict:
    """Return walking distance dict or empty dict if coordinates unavailable."""
    if not all(isinstance(v, (int, float)) and v != 0 for v in (home_lat, home_lon, stop_lat, stop_lon)):
        return {}
    dist = haversine_m(home_lat, home_lon, stop_lat, stop_lon)
    return {
        "walking_distance_m": round(dist),
        "walking_time_min": walking_minutes(dist),
    }
