/** Shape of src/lib/data/scenarios/*.json, written by scripts/build_scenarios.py. */
import type { FeatureCollection } from 'geojson';

export type ScenarioModule = 'mining' | 'landslide';
/** Only simulated scenarios exist today; real observations would carry 'REAL'. */
export type ScenarioDataStatus = 'SIMULATED' | 'REAL';
export type Corner = [number, number];

export interface Epoch {
	date: string;
	day: number;
	label: string;
	sar_url: string;
	coherence_url: string | null;
	displacement_url: string | null;
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
	validation: { note: string; recall: number; precision: number };
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

export type Scenario = MiningScenario | LandslideScenario;
