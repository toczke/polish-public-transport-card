"""Tests for walking distance helpers."""

from mzkzg_transport.walking import haversine_m, stop_walking_info, walking_minutes


def test_haversine_zero_distance():
    assert haversine_m(54.35, 18.65, 54.35, 18.65) == 0


def test_haversine_known_distance():
    # Gdańsk Główny -> Gdańsk Wrzeszcz is roughly 5.5 km.
    distance = haversine_m(54.3556, 18.6440, 54.3800, 18.6050)
    assert 3000 < distance < 5000


def test_walking_minutes_rounds_up_to_one_minute():
    assert walking_minutes(0) == 1
    assert walking_minutes(80) == 1
    assert walking_minutes(800) == 10


def test_stop_walking_info_returns_distance_and_time():
    info = stop_walking_info(54.3556, 18.6440, 54.3800, 18.6050)
    assert set(info) == {"walking_distance_m", "walking_time_min"}
    assert info["walking_distance_m"] > 0
    assert info["walking_time_min"] >= 1


def test_stop_walking_info_requires_all_coordinates():
    assert stop_walking_info(None, 18.64, 54.35, 18.65) == {}
    assert stop_walking_info(54.35, 18.64, 0, 18.65) == {}
    assert stop_walking_info("54.35", 18.64, 54.35, 18.65) == {}
