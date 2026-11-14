from datetime import datetime, timezone

from services.processing.weather import build_record, era5_at, metar_near

ERA5 = {
    "latitude": 17.05,
    "longitude": 96.05,
    "hourly": {
        "time": [f"2026-08-27T{h:02d}:00" for h in range(24)],
        "wind_speed_10m": [1.0] * 23 + [2.1],
        "wind_gusts_10m": [2.0] * 23 + [5.2],
        "precipitation": [0.5] * 21 + [0.2, 0.3, 0.1],
    },
}

METAR = """station,valid,sknt,p01m,wxcodes
VYYY,2026-08-27 19:00,4.00,0.00,-RA
VYYY,2026-08-27 22:30,6.00,0.00,M
VYYY,2026-08-27 23:00,0.00,0.00,M
VYYY,2026-08-27 23:30,2.00,0.00,DZ
VYYY,2026-08-28 01:00,9.00,0.00,M
"""


def test_era5_uses_nearest_hour_and_trailing_rain():
    values = era5_at(ERA5["hourly"], datetime(2026, 8, 27, 23, 2, tzinfo=timezone.utc))
    assert values["time_utc"] == "2026-08-27T23:00Z"
    assert values["wind_speed_ms"] == 2.1
    assert values["rain_3h_mm"] == 0.6
    assert values["rain_24h_mm"] == 11.1


def test_metar_takes_reports_within_half_an_hour_and_prior_weather_only():
    values = metar_near(list(__import__("csv").DictReader(__import__("io").StringIO(METAR))), datetime(2026, 8, 27, 23, 2, tzinfo=timezone.utc))
    assert values["reports"] == ["23:00 0.00 kt", "23:30 2.00 kt"]
    assert values["max_wind_ms"] == 1.0
    assert values["present_weather_prior_hours"] == ["19:00 -RA"]


def test_two_calm_mornings_are_reported_as_calm():
    record = build_record("t", 17.0, 96.0, ["2026-08-27T23:02:39Z", "2026-08-27T23:02:39Z"], ERA5, METAR)
    assert record["comparison"]["all_near_calm"] is True
    assert record["dates"][0]["metar"]["max_wind_ms"] == 1.0
