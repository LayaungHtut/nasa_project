/** Shape of src/lib/data/scenarios/*.json, all built from real NISAR granules: scripts/build_hpakant.py and scripts/build_slope.py. */
import type { FeatureCollection } from 'geojson';

export type ScenarioModule = 'observed' | 'slope';
/** REAL: measured from NISAR granules. Every module ships real data; there is no simulated mode. */
export type ScenarioDataStatus = 'REAL';
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

export interface ScenarioBase {
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

/** Per 12-day GUNW pair: how much of the window could be read, and the noise on flat reference ground. */
export interface SlopeMetrics {
	measured_pct: number;
	reference_scatter_cm: number | null;
	/** Days between the previous pair's end and this pair's start; that time is not measured. */
	gap_before_days: number;
	/** Share of the window with a rate from the pairs up to this one. */
	rate_coverage_pct: number;
}

/** Steep ground moving faster than the reference scatter allows: a landslide indicator, not a confirmed slide. */
export interface SlopeCandidate {
	candidate_id: string;
	area_m2: number;
	slope_deg: number;
	/** Mean line-of-sight rate; positive is toward the satellite. */
	rate_cm_yr: number;
	direction: 'toward' | 'away';
	sign_agreement: number;
	pairs_measured: number;
	/** Cumulative LOS motion at each epoch (sum of patch-median pair displacements); null where unmeasured. */
	series_cm: Array<number | null>;
	centroid: Corner;
	bbox: [number, number, number, number];
}

export interface SlopeScenario extends ScenarioBase {
	module: 'slope';
	metrics: SlopeMetrics[];
	candidates: SlopeCandidate[];
	reference_series_cm: Array<number | null>;
	thresholds: {
		coherence_min: number;
		flat_max_deg: number;
		slope_min_deg: number;
		min_valid_frac: number;
		sigma_k: number;
		sign_agreement_min: number;
		min_cluster_m2: number;
		display_cm_yr: number;
	};
	uncertainty: {
		rate_sigma_cm_yr: number;
		reference_m2: number;
		rate_coverage_pct: number;
		unmeasured_gap_days: number;
		unread_pairs: string[];
		rule_pass_flat_pct: number;
		rule_pass_steep_pct: number;
		centre_rate_cm_yr: number;
		rim_rate_cm_yr: number;
		residual_rate_vs_elevation_cm_yr_per_100m: number;
		notes: string[];
	};
	provenance: {
		source_archive: string;
		track: number;
		frame: number;
		orbit_direction: string;
		epsg: number;
		gunw_granules: string[];
		gcov_granules: string[];
		dem: { product: string; url: string };
		sign_convention: { statement: string; source: string };
	};
}

export type Scenario = ObservedScenario | SlopeScenario;
