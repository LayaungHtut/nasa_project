import { describe, expect, it } from 'vitest';
import { getAuthoritativeEvent } from '$lib/server/events';
import { CURATED_EVENTS } from '$lib/data/fixtures';
import { driverHypotheses, localAcquisitionTime } from './drivers';
import record from '../../../data/processed/yangon-track40-frame10/polarization.json';
import statistics from '../../../data/processed/yangon-track40-frame10/statistics.json';
import weather from '../../../data/validation/yangon-track40-frame10/weather.json';
import timeseries from '../../../data/processed/yangon-track40-frame10/timeseries.json';

describe('Polarization record and driver hypotheses', () => {
	it('attaches the polarization record only to the run it was computed from', async () => {
		const served = await getAuthoritativeEvent('yangon-track40-frame10');
		expect(served?.polarimetry?.classes.apparent_water_loss.pixels).toBe(
			statistics.water_loss_pixels
		);
		expect(served?.polarimetry?.hv_assessment).toEqual(record.hv_assessment);

		const rerun = { ...served!, processing: { ...served!.processing, threshold_db: -10 } };
		const { presentEvent } = await import('./presentation');
		expect(presentEvent(rerun).polarimetry).toBeUndefined();
		expect(presentEvent(rerun).drivers).toEqual([]);
	});

	it('gives the offline copy the same hypotheses as the server', async () => {
		const served = await getAuthoritativeEvent('yangon-track40-frame10');
		const offline = CURATED_EVENTS.find((e) => e.id === 'yangon-track40-frame10');
		expect(offline?.drivers).toEqual(served?.drivers);
	});

	it('quotes recorded numbers and leaves synthetic events without hypotheses', async () => {
		const served = (await getAuthoritativeEvent('yangon-track40-frame10'))!;
		const drivers = driverHypotheses(served);
		// The season record puts 92% of the water loss on paddy fields, so rice growth ranks first.
		expect(drivers.map((d) => d.id)).toEqual([
			'paddy-growth',
			'not-wind',
			'edge-inundation',
			'roughened-water',
			'drawdown'
		]);
		const paddy = drivers.find((d) => d.id === 'paddy-growth')!;
		expect(paddy.support).toBe('best supported');
		expect(paddy.evidence_for.join(' ')).toContain(
			`${timeseries.event_change_by_landcover.apparent_water_loss.by_landcover_km2.cropland.toFixed(2)} km²`
		);
		const wind = drivers.find((d) => d.id === 'roughened-water')!;
		expect(wind.explains).toBe(`${statistics.water_loss_area_km2} km² apparent water loss`);
		expect(wind.evidence_for[0]).toContain(
			`${record.hh_difference_db.apparent_water_loss_median.toFixed(1)} dB`
		);
		for (const d of drivers) expect(d.how_to_test.length).toBeGreaterThan(0);

		const synthetic = CURATED_EVENTS.find((e) => e.data_status === 'SYNTHETIC_PLACEHOLDER')!;
		expect(driverHypotheses(synthetic)).toEqual([]);
	});

	it('downgrades the wind explanation when both passes were near calm', async () => {
		const served = (await getAuthoritativeEvent('yangon-track40-frame10'))!;
		expect(served.weather?.comparison.all_near_calm).toBe(weather.comparison.all_near_calm);
		const wind = served.drivers!.find((d) => d.id === 'roughened-water')!;
		expect(wind.support).toBe('weakly supported');
		expect(wind.evidence_against.join(' ')).toContain('near calm');

		const windy = {
			...served,
			weather: {
				...served.weather!,
				comparison: { ...served.weather!.comparison, all_near_calm: false }
			}
		};
		const unchecked = driverHypotheses({ ...served, weather: undefined, timeseries: undefined });
		expect(driverHypotheses(windy).find((d) => d.id === 'not-wind')).toBeUndefined();
		expect(unchecked[0].id).toBe('roughened-water');
		expect(unchecked[0].support).toBe('best supported');
	});

	it('converts UTC acquisition times to Myanmar time', () => {
		expect(localAcquisitionTime('2026-08-27T23:02:39Z')).toBe('Aug 28, 05:32');
	});
});
