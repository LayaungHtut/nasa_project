import { describe, expect, it } from 'vitest';
import { getAuthoritativeEvent } from '$lib/server/events';
import record from '../../../data/processed/yangon-track40-frame10/timeseries.json';
import statistics from '../../../data/processed/yangon-track40-frame10/statistics.json';

describe('Time series record', () => {
	it('contains both analysed dates with the same water counts as the event', async () => {
		const served = (await getAuthoritativeEvent('yangon-track40-frame10'))!;
		const byDate = new Map(served.timeseries!.dates.map((d) => [d.date, d]));
		expect(byDate.get(served.observation_dates.baseline)?.water_area_km2).toBe(
			statistics.baseline_water_area_km2
		);
		expect(byDate.get(served.observation_dates.post_event)?.water_area_km2).toBe(
			statistics.post_event_water_area_km2
		);
		const times = record.dates.map((d) => Date.parse(d.date));
		expect(times).toEqual([...times].sort((a, b) => a - b));
	});

	it('is not attached to a run with different processing', async () => {
		const served = (await getAuthoritativeEvent('yangon-track40-frame10'))!;
		const rerun = { ...served, processing: { ...served.processing, speckle_filter_size: 5 } };
		const { presentEvent } = await import('./presentation');
		expect(presentEvent(rerun).timeseries).toBeUndefined();
	});

	it('shows a paddy signal well above the forest control and keeps edge effects small', () => {
		const ps = record.pixel_season;
		expect(ps.brightened_over_1db.cropland).toBeGreaterThan(
			5 * ps.brightened_over_1db.forest_control
		);
		expect(ps.dark_then_rise.cropland).toBeGreaterThan(3 * ps.dark_then_rise.forest_control);
		expect(record.erosion_sensitivity_max_db.cropland).toBeLessThan(0.5);
		const t = ps.timing_neighbour_agreement;
		expect(t.observed - t.if_random).toBeGreaterThan(0.1);
	});

	it('attaches the Sentinel-2 NDVI record only alongside the matching radar series', async () => {
		const served = (await getAuthoritativeEvent('yangon-track40-frame10'))!;
		expect(served.ndvi?.scenes.length).toBeGreaterThan(0);
		const rerun = { ...served, processing: { ...served.processing, threshold_db: -10 } };
		const { presentEvent } = await import('./presentation');
		expect(presentEvent(rerun).ndvi).toBeUndefined();
	});

	it('backs the processing-version evidence with the recorded metadata', async () => {
		const served = (await getAuthoritativeEvent('yangon-track40-frame10'))!;
		const v = served.processing_versions!;
		expect(v.flags_that_differ).toEqual({});
		expect(v.compared.every((c) => c.flags.noiseCorrectionApplied === 'False')).toBe(true);
		const shift = v.forest_relative_db_change;
		expect(Math.abs(shift.permanent_water)).toBeGreaterThan(
			3 * Math.max(Math.abs(shift.cropland), Math.abs(shift.built_up))
		);
		const { driverHypotheses } = await import('./drivers');
		const notWind = driverHypotheses(served).find((h) => h.id === 'not-wind');
		expect(notWind?.evidence_for.some((e) => e.includes('processing software changed'))).toBe(true);
	});
});

describe('Period comparison', () => {
	it('derives presets from the record and matches the season finding', async () => {
		const { periodPresets, periodChange, seasonFindings } = await import('./timeseries');
		const served = (await getAuthoritativeEvent('yangon-track40-frame10'))!;
		const ts = served.timeseries!;
		const { baseline, post_event } = served.observation_dates;
		const presets = periodPresets(ts, baseline, post_event);
		for (const p of presets) expect(p.to).toBeGreaterThan(p.from);
		const grown = presets.find((p) => p.label === 'Flooded → grown')!;
		const f = seasonFindings(ts);
		expect(periodChange(ts, grown.from, grown.to).paddy).toBeCloseTo(f.paddyRise, 6);
		const pair = presets.find((p) => p.label === 'Two-date analysis')!;
		expect(ts.dates[pair.from].date).toBe(baseline);
		expect(ts.dates[pair.to].date).toBe(post_event);
		// The whole-season preset never crosses into the newer processing version.
		const whole = presets.find((p) => p.label === 'Whole season')!;
		expect(periodChange(ts, whole.from, whole.to).sameProcessing).toBe(true);
	});

	it('flags a period that spans two processing versions', async () => {
		const { periodChange } = await import('./timeseries');
		const ts = (await getAuthoritativeEvent('yangon-track40-frame10'))!.timeseries!;
		const change = periodChange(ts, 0, ts.dates.length - 1);
		expect(change.sameProcessing).toBe(false);
		expect(change.days).toBeGreaterThan(100);
	});
});

describe('Land-cover map layer', () => {
	it('colours only the finding classes, with areas matching the recorded fractions', async () => {
		const ts = (await getAuthoritativeEvent('yangon-track40-frame10'))!.timeseries!;
		const lc = ts.landcover_map;
		expect(lc.classes.map((c) => c.key)).toEqual(['cropland', 'permanent_water', 'built_up']);
		const totalKm2 = (ts.grid.shape[0] * ts.grid.shape[1] * 100) / 1e6; // 10 m pixels
		for (const c of lc.classes)
			expect(c.area_km2).toBeCloseTo((ts.landcover_fractions[c.key] ?? 0) * totalKm2, 0);
		// Colour follows the entity: the same colours as the season chart.
		expect(Object.fromEntries(lc.classes.map((c) => [c.key, c.color]))).toEqual({
			cropland: '#199e70',
			permanent_water: '#3987e5',
			built_up: '#d95926'
		});
	});
});
