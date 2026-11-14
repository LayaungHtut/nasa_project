"""Wind and rain at each NISAR acquisition time, from two independent sources.

Tests the "wind roughened the water" explanation for changes in reservoir
backscatter. Calm open water reflects L-band energy away from the radar; wind
ripples scatter it back. If wind explains a brightening, the brighter date
should be the windier one.

Sources (both public, no credentials):
  - ERA5 reanalysis via the Open-Meteo archive API, hourly, at the AOI center
    (a ~25 km model grid: an estimate, not a measurement at the reservoir).
  - METAR reports from Yangon International Airport (VYYY, ~16 km SSE of the
    reservoir) via the Iowa Environmental Mesonet archive, half-hourly, wind
    in whole knots (0 kt = calm).

CLI usage:
    python -m services.processing.weather --event-id yangon-track40-frame10 \\
        --lat 17.058 --lon 96.088 --times 2026-08-27T23:02:39Z 2026-09-08T23:02:39Z

Writes data/validation/<event-id>/weather/{era5-open-meteo.json,metar-vyyy.csv}
(raw responses, for audit) and data/validation/<event-id>/weather.json.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATION_DIR = REPO_ROOT / "data" / "validation"

KNOT_MS = 0.514444
STATION = "VYYY"
ERA5_URL = "https://archive-api.open-meteo.com/v1/archive"
METAR_URL = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"

CALM_WIND_MS = 3.0
"""Below roughly this 10 m wind speed, small water bodies stay close to
specular at L-band; treated as 'near calm' when comparing dates."""


def _parse_utc(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(timezone.utc)


def _number(value: str | None) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def era5_at(hourly: dict, when: datetime) -> dict:
    """Nearest-hour ERA5 values, plus rain summed over the 3 and 24 hours up to it."""
    nearest = (when + timedelta(minutes=30)).replace(minute=0, second=0, microsecond=0)
    i = hourly["time"].index(nearest.strftime("%Y-%m-%dT%H:%M"))
    rain = hourly["precipitation"]
    return {
        "time_utc": hourly["time"][i] + "Z",
        "wind_speed_ms": hourly["wind_speed_10m"][i],
        "wind_gust_ms": hourly["wind_gusts_10m"][i],
        "rain_3h_mm": round(sum(rain[max(0, i - 2) : i + 1]), 1),
        "rain_24h_mm": round(sum(rain[max(0, i - 23) : i + 1]), 1),
    }


def metar_near(rows: list[dict], when: datetime, window_min: int = 30, weather_hours: int = 6) -> dict:
    """Airport wind reports within +-window_min of the acquisition, and any
    present-weather codes (e.g. RA rain, DZ drizzle) in the preceding hours."""
    def at(row):
        return datetime.strptime(row["valid"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)

    near = [r for r in rows if abs((at(r) - when).total_seconds()) <= window_min * 60]
    winds = [k * KNOT_MS for k in (_number(r["sknt"]) for r in near) if k is not None]
    recent = [
        f"{at(r):%H:%M} {r['wxcodes']}"
        for r in rows
        if timedelta(0) <= when - at(r) <= timedelta(hours=weather_hours) and r["wxcodes"] not in ("M", "")
    ]
    return {
        "reports": [f"{at(r):%H:%M} {r['sknt']} kt" for r in near],
        "max_wind_ms": round(max(winds), 1) if winds else None,
        "present_weather_prior_hours": recent,
    }


def compare(dates: list[dict]) -> dict:
    """Is the wind difference between dates large enough to matter?"""
    def wind(d):
        observed = d["metar"]["max_wind_ms"]
        return observed if observed is not None else d["era5"]["wind_speed_ms"]

    winds = [wind(d) for d in dates]
    all_calm = all(w < CALM_WIND_MS for w in winds) and all(d["era5"]["wind_speed_ms"] < CALM_WIND_MS for d in dates)
    return {
        "calm_threshold_ms": CALM_WIND_MS,
        "all_near_calm": all_calm,
        "observed_or_modelled_wind_ms": winds,
        "windiest_date": dates[max(range(len(dates)), key=lambda i: winds[i])]["time_utc"],
    }


def build_record(event_id: str, lat: float, lon: float, times: list[str], era5: dict, metar_csv: str) -> dict:
    rows = list(csv.DictReader(io.StringIO(metar_csv)))
    dates = []
    for iso in times:
        when = _parse_utc(iso)
        dates.append({"time_utc": iso, "era5": era5_at(era5["hourly"], when), "metar": metar_near(rows, when)})
    return {
        "event_id": event_id,
        "method": "acquisition_weather_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "location": {"lat": lat, "lon": lon, "era5_grid_point": [era5["latitude"], era5["longitude"]]},
        "sources": {
            "era5": "ERA5 reanalysis via Open-Meteo archive API (open-meteo.com), CC BY 4.0",
            "metar": f"{STATION} (Yangon International Airport) METAR via Iowa Environmental Mesonet",
            "raw_files": [f"validation/{event_id}/weather/era5-open-meteo.json", f"validation/{event_id}/weather/metar-vyyy.csv"],
        },
        "dates": dates,
        "comparison": compare(dates),
    }


def fetch(lat: float, lon: float, start: datetime, end: datetime) -> tuple[dict, str]:
    era5 = requests.get(
        ERA5_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "start_date": f"{start:%Y-%m-%d}",
            "end_date": f"{end:%Y-%m-%d}",
            "hourly": "wind_speed_10m,wind_gusts_10m,precipitation",
            "wind_speed_unit": "ms",
            "timezone": "GMT",
        },
        timeout=60,
    )
    era5.raise_for_status()
    metar = requests.get(
        METAR_URL,
        params={
            "station": STATION,
            "data": ["sknt", "p01m", "wxcodes"],
            "year1": start.year, "month1": start.month, "day1": start.day,
            "year2": end.year, "month2": end.month, "day2": end.day,
            "tz": "Etc/UTC",
            "format": "onlycomma",
            "missing": "M",
        },
        timeout=60,
    )
    metar.raise_for_status()
    return era5.json(), metar.text


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--event-id", required=True)
    parser.add_argument("--lat", type=float, required=True)
    parser.add_argument("--lon", type=float, required=True)
    parser.add_argument("--times", nargs="+", required=True, help="acquisition start times, ISO 8601 UTC")
    args = parser.parse_args()

    whens = sorted(_parse_utc(t) for t in args.times)
    era5, metar_csv = fetch(args.lat, args.lon, whens[0] - timedelta(days=1), whens[-1] + timedelta(days=1))

    raw_dir = VALIDATION_DIR / args.event_id / "weather"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "era5-open-meteo.json").write_text(json.dumps(era5))
    (raw_dir / "metar-vyyy.csv").write_text(metar_csv)

    record = build_record(args.event_id, args.lat, args.lon, args.times, era5, metar_csv)
    (VALIDATION_DIR / args.event_id / "weather.json").write_text(json.dumps(record, indent=2))
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
