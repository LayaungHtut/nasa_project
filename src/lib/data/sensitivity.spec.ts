import { describe, expect, it } from 'vitest';
import {
	getSensitivityForEvent,
	HLAWGA_SENSITIVITY_SWEEP,
	TESTED_THRESHOLDS_DB
} from './sensitivity';
import statistics from '../../../data/processed/yangon-track40-frame10/statistics.json';

describe('Hlawga Reservoir threshold and filter sensitivity sweep', () => {
	it('matches statistics.json exactly at the served 3x3 / -9.54 dB configuration', () => {
		const served = HLAWGA_SENSITIVITY_SWEEP.find((p) => p.is_served);
		expect(served).toBeDefined();
		expect(served?.filter_size).toBe(statistics.lee_filter_size);
		expect(served?.threshold_db).toBe(statistics.threshold_db);
		expect(served?.new_inundation_km2).toBe(statistics.new_inundation_area_km2);
		expect(served?.water_loss_km2).toBe(statistics.water_loss_area_km2);
		expect(served?.baseline_water_km2).toBe(statistics.baseline_water_area_km2);
		expect(served?.post_water_km2).toBe(statistics.post_event_water_area_km2);
	});

	it('preserves baseline > post-event water asymmetry across every tested threshold and filter', () => {
		for (const point of HLAWGA_SENSITIVITY_SWEEP) {
			expect(point.baseline_water_km2).toBeGreaterThan(point.post_water_km2);
		}
		expect(getSensitivityForEvent('yangon-track40-frame10')).toHaveLength(
			TESTED_THRESHOLDS_DB.length * 2
		);
		expect(getSensitivityForEvent('demo-yangon-fixture')).toEqual([]);
	});
});
