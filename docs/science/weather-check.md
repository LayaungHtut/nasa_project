# Weather check: did wind roughen the reservoir?

**Outcome: no evidence that it did. Both acquisition mornings were near calm, so wind does not explain why reservoir pixels were brighter on the second date. The leading explanation for the 4.517 km² apparent water loss is now weakly supported, and the cause remains open.**

Calm open water reflects L-band energy away from the radar and looks dark. Wind ripples scatter energy back and brighten it. If wind explains the second date's brighter reservoir (apparent-loss pixels: median −10.15 → −7.88 dB HH, see the [polarization analysis](polarization-analysis.md)), the second morning should be the windier one.

Record: [`weather.json`](../../data/validation/yangon-track40-frame10/weather.json), with the raw responses in `data/validation/yangon-track40-frame10/weather/`. Code: `services/processing/weather.py`, tests in `tests/test_weather.py`.

## Conditions at each pass

Both passes were at 23:02 UTC, which is 05:32 the next morning in Myanmar time.

| Pass (UTC) | Airport wind, 23:00 / 23:30 | ERA5 wind (gust) | ERA5 rain, 3 h / 24 h | Airport weather in prior 6 h      |
| ---------- | --------------------------- | ---------------- | --------------------- | --------------------------------- |
| Aug 27     | 0 / 0 kt (calm)             | 2.1 (5.2) m/s    | 0.6 / 11.4 mm         | Rain and drizzle, 17:30–20:00 UTC |
| Sep 8      | 0 / 2 kt (≤1.0 m/s)         | 2.1 (3.5) m/s    | 0.1 / 17.9 mm         | None reported                     |

- **Airport:** METAR reports from Yangon International Airport (VYYY), about 16 km south-southeast of the reservoir, via the Iowa Environmental Mesonet. Wind is reported in whole knots; 0 kt means calm.
- **ERA5:** hourly reanalysis via the Open-Meteo archive API at the nearest grid point (17.05° N, 96.05° E). It is a model estimate on a ~25 km grid, not a measurement at the reservoir.

## Reading the result

- Both sources put both mornings below about 3 m/s, where small water bodies normally stay close to mirror-smooth at L-band. The two mornings are also nearly identical to each other (ERA5 2.07 vs 2.11 m/s).
- The only rain fell before the first pass and ended about three hours before it. Rain falling on water roughens it, so if anything it would brighten the first date, the opposite of what was observed.
- Wind and rain are therefore unlikely to explain the change. That also leaves a second question open: on a near-calm morning, reservoir pixels still read about 12 dB above the product's own noise floor. Possible causes include floating or emergent plants, or an effect of processing in these provisional products (no noise correction applied). The Sep 13 Sentinel-2 overview shows dark open water with no obvious plant mats at 10 m resolution. Neither cause has been checked on the ground.

## Limits

- Airport wind is about 16 km away and over land; a lake surface can be locally windier. Both sources agree on near-calm conditions, but neither measures wind at the reservoir.
- Two dates are not enough to test whether reservoir brightness tracks wind in general. More NISAR passes over the same track (Aug 15, Sep 20, Oct 2 and Oct 14, 2026 are in the archive) would allow that comparison. Re-running the command below with those times adds them to the record.

## How the app uses this

`src/lib/data/drivers.ts` reads the record. When both passes were near calm, it downgrades "Wind or rain roughened the reservoir surface" to _weakly supported_, quotes these figures as evidence against it, and adds "Something other than wind keeps the water bright" as a _possible_ explanation. Without a weather record, the earlier ranking would apply.

## Reproduce

```sh
python -m services.processing.weather --event-id yangon-track40-frame10 \
  --lat 17.058 --lon 96.088 --times 2026-08-27T23:02:39Z 2026-09-08T23:02:39Z
```

Weather data: ERA5 reanalysis via [Open-Meteo](https://open-meteo.com/) (CC BY 4.0); VYYY METAR via the [Iowa Environmental Mesonet](https://mesonet.agron.iastate.edu/).
