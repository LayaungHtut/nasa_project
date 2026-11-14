/**
 * Authoritative threshold and Lee-filter sensitivity sweep for Hlawga Reservoir
 * (`yangon-track40-frame10`), computed directly from the real NISAR L2 GCOV raster
 * arrays during Investigation 2 (see `docs/science/real-data-validation.md`, lines 195-216).
 */

export interface SensitivityPoint {
	filter_size: 3 | 5;
	threshold_db: number;
	is_served?: boolean;
	new_inundation_km2: number;
	water_loss_km2: number;
	baseline_water_km2: number;
	post_water_km2: number;
}

export const HLAWGA_SENSITIVITY_SWEEP: readonly SensitivityPoint[] = [
	{
		filter_size: 3,
		threshold_db: -12.0,
		new_inundation_km2: 0.0,
		water_loss_km2: 0.02,
		baseline_water_km2: 0.076,
		post_water_km2: 0.0
	},
	{
		filter_size: 3,
		threshold_db: -11.0,
		new_inundation_km2: 0.0,
		water_loss_km2: 0.369,
		baseline_water_km2: 0.644,
		post_water_km2: 0.006
	},
	{
		filter_size: 3,
		threshold_db: -10.0,
		new_inundation_km2: 0.004,
		water_loss_km2: 2.302,
		baseline_water_km2: 3.207,
		post_water_km2: 0.163
	},
	{
		filter_size: 3,
		threshold_db: -9.54,
		is_served: true,
		new_inundation_km2: 0.056,
		water_loss_km2: 4.517,
		baseline_water_km2: 5.856,
		post_water_km2: 0.571
	},
	{
		filter_size: 3,
		threshold_db: -9.0,
		new_inundation_km2: 0.288,
		water_loss_km2: 8.209,
		baseline_water_km2: 10.614,
		post_water_km2: 1.905
	},
	{
		filter_size: 3,
		threshold_db: -8.0,
		new_inundation_km2: 1.149,
		water_loss_km2: 15.289,
		baseline_water_km2: 24.229,
		post_water_km2: 9.3
	},
	{
		filter_size: 3,
		threshold_db: -7.0,
		new_inundation_km2: 1.508,
		water_loss_km2: 17.911,
		baseline_water_km2: 41.835,
		post_water_km2: 24.494
	},
	{
		filter_size: 5,
		threshold_db: -12.0,
		new_inundation_km2: 0.0,
		water_loss_km2: 0.002,
		baseline_water_km2: 0.003,
		post_water_km2: 0.0
	},
	{
		filter_size: 5,
		threshold_db: -11.0,
		new_inundation_km2: 0.0,
		water_loss_km2: 0.113,
		baseline_water_km2: 0.157,
		post_water_km2: 0.0
	},
	{
		filter_size: 5,
		threshold_db: -10.0,
		new_inundation_km2: 0.002,
		water_loss_km2: 1.285,
		baseline_water_km2: 1.465,
		post_water_km2: 0.005
	},
	{
		filter_size: 5,
		threshold_db: -9.54,
		new_inundation_km2: 0.01,
		water_loss_km2: 3.026,
		baseline_water_km2: 3.324,
		post_water_km2: 0.049
	},
	{
		filter_size: 5,
		threshold_db: -9.0,
		new_inundation_km2: 0.097,
		water_loss_km2: 6.664,
		baseline_water_km2: 7.306,
		post_water_km2: 0.446
	},
	{
		filter_size: 5,
		threshold_db: -8.0,
		new_inundation_km2: 0.868,
		water_loss_km2: 14.577,
		baseline_water_km2: 19.906,
		post_water_km2: 5.806
	},
	{
		filter_size: 5,
		threshold_db: -7.0,
		new_inundation_km2: 1.046,
		water_loss_km2: 18.217,
		baseline_water_km2: 37.622,
		post_water_km2: 19.966
	}
];

export const TESTED_THRESHOLDS_DB: readonly number[] = [
	-12.0, -11.0, -10.0, -9.54, -9.0, -8.0, -7.0
];

export function getSensitivityForEvent(eventId: string): readonly SensitivityPoint[] {
	return eventId === 'yangon-track40-frame10' ? HLAWGA_SENSITIVITY_SWEEP : [];
}
