/** Shape of src/lib/data/scenarios/*.json: simulated demos from scripts/build_scenarios.py, real NISAR from scripts/build_hpakant.py. */
import type { FeatureCollection } from 'geojson';

export type ScenarioModule = 'observed' | 'mining' | 'landslide';
/** REAL: measured from NISAR granules. SIMULATED: synthetic demo scenes. */
export type ScenarioDataStatus = 'SIMULATED' | 'REAL';
export type Corner = [number, number];

export interface Epoch {
	date: string;
	day: number;
	label: string;
	sar_url: string;
	coherence_url: string | null;
	displacement_url: string | null;
	/** Real data only: the GCOV granule of this pass, and the GUNW pair ending on it. */
	granule_id?: string;
	gunw_granule_id?: string | null;
	coherence_pair?: [string, string] | null;
}

export interface MiningMetrics {
	new_clearing_m2: number;
	inside_m2: number;
	outside_m2: number;
	outside_beyond_tolerance_m2: number;
	max_distance_outside_m: number;
	low_coherence_outside_m2: number;
	max_subsidence_outside_cm: number;
}

export interface LandslideMetrics {
	landslide_m2: number;
	impoundment_m2: number;
	channel_shift_m: number;
	new_channel_m2: number;
	abandoned_channel_m2: number;
	control_reach_water_change_pct: number;
	coherence_at_slide: number | null;
}

interface ScenarioBase {
	id: string;
	data_status: ScenarioDataStatus;
	title: string;
	location: {
		name: string;
		region: string;
		center: Corner;
		zoom: number;
		image_coordinates: [Corner, Corner, Corner, Corner];
	};
	story: { headline: string; context: string; radar_insight: string };
	sensor: {
		mission: string;
		band: string;
		wavelength_cm: number;
		repeat_days: number;
		backscatter_product: string;
		insar_product: string;
		polarization: string;
		pixel_m: number;
		looks: number;
	};
	epochs: Epoch[];
	/** Null when there is no independent reference to score against. */
	validation: { note: string; recall: number | null; precision: number | null };
	geojson: FeatureCollection;
}

export interface MiningScenario extends ScenarioBase {
	module: 'mining';
	metrics: MiningMetrics[];
	thresholds: {
		breach_outside_m2: number;
		tolerance_m: number;
		subsidence_watch_cm: number;
		clearing_drop_db: number;
		min_cluster_m2: number;
		coherence_min: number;
	};
	permit: { operator: string; permit_id: string; area_m2: number };
}

export interface LandslideScenario extends ScenarioBase {
	module: 'landslide';
	metrics: LandslideMetrics[];
	thresholds: {
		landslide_drop_db: number;
		landslide_min_m2: number;
		water_db: number;
		channel_shift_m: number;
		new_channel_min_m2: number;
		coherence_min: number;
		link_max_km: number;
		link_max_days: number;
	};
	linkage: {
		river_distance_km: number;
		slide_is_upstream: boolean;
		precursor_creep_cm: number;
		precursor_pass: number;
	};
}

/** Surface change measured on one pass, against the baseline composite; confirmed on two consecutive passes. */
export interface ObservedMetrics {
	disturbed_m2: number;
	new_water_m2: number;
	drop_db_median: number | null;
	coherence_disturbed: number | null;
	coherence_reference: number | null;
	/** False-alarm area if errors on two passes were independent, and the upper bound if they were not. */
	expected_false_m2: number;
	expected_false_upper_m2: number;
	clusters: number;
}

/** Properties of one detected Hpakant patch (a GeoJSON feature; a patch with a hole is still one feature). */
export interface ObservedPatch {
	kind: 'disturbed' | 'new_water';
	/** Pass on which the patch was confirmed. */
	epoch: number;
	/** Unique across the scenario, e.g. "d6-1": kind initial, pass, rank by area on that pass. */
	patch_id: string;
	area_m2: number;
	/** Patch median on every kept pass, after the per-pass reference offset. */
	hv_db: number[];
	hh_db: number[];
	/** Patch median of the baseline composite in the channel the rule tests: HV for loss, HH for water. */
	baseline_db: number;
	/** Vegetation loss only. */
	drop_db_median: number | null;
	/** Median GUNW coherence over the patch for the pair ending on its pass. */
	coherence: number | null;
	/** Passes whose confirmed change of the same kind overlaps this patch. */
	seen_on: number[];
	centroid: Corner;
	/** [west, south, east, north] */
	bbox: [number, number, number, number];
}

export interface DbStats {
	median: number;
	p25: number;
	p75: number;
}

/** HV on every kept pass: ground changed on the latest pass versus the stable vegetated reference. */
export interface ObservedHvSeries {
	polarization: 'HV';
	reference: DbStats[];
	reference_m2: number;
	/** Null when nothing was confirmed on the latest pass. */
	disturbed: DbStats[] | null;
	disturbed_m2: number;
	disturbed_epoch: number;
	note: string;
}

export interface ObservedScenario extends ScenarioBase {
	module: 'observed';
	/** Null on the baseline passes and the first pass after them (nothing to confirm against yet). */
	metrics: (ObservedMetrics | null)[];
	hv_series: ObservedHvSeries;
	thresholds: {
		drop_db: number;
		vegetated_below_reference_db: number;
		water_db: number;
		min_cluster_m2: number;
		calibration_tolerance_db: number;
		coherence_low: number;
		lee_window_px: number;
	};
	uncertainty: {
		null_test: string;
		single_pass_false_rate: number;
		confirmed_false_rate: number;
		vegetated_m2: number;
		reference_offsets_db: number[];
		notes: string[];
	};
	provenance: {
		source_archive: string;
		track: number;
		frame: number;
		orbit_direction: string;
		epsg: number;
		gcov_granules: string[];
		gunw_granules: string[];
		excluded: { date: string; granule_id: string; reason: string }[];
		unreadable: string[];
	};
}

export type Scenario = ObservedScenario | MiningScenario | LandslideScenario;
