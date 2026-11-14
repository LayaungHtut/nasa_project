/**
 * Data contracts for NASA NISAR "Dancing with the SARs" Explorer.
 * In strict alignment with docs/api/api-contract.md and docs/science/limitations.md.
 */

export interface Provenance {
	mission: 'NISAR';
	product: 'GCOV' | 'GUNW';
	granule_id: string;
	daac: 'ASF';
	acquisition_date: string; // ISO 8601 UTC date
	polarization?: 'HH' | 'HV' | 'VV' | 'VH';
	orbit_direction?: 'Ascending' | 'Descending';
	track?: number;
	frequency_band?: 'L-band (24 cm)' | 'S-band (9 cm)';
}

export interface ChangeEventLocation {
	name: string;
	country: string;
	region: string;
	bbox: [number, number, number, number]; // [minLon, minLat, maxLon, maxLat]
	center: [number, number]; // [lon, lat]
	zoom: number;
}

export interface ObservationDates {
	baseline: string;
	post_event: string;
	all_observations?: Array<{
		date: string;
		label: string;
		phase: 'baseline' | 'repeat' | 'peak' | 'receding' | 'normal';
		granule_id: string;
	}>;
}

export interface ProcessingMetadata {
	method: string;
	version: string;
	threshold_db?: number;
	speckle_filter?: string;
	speckle_filter_size?: number;
	min_cluster_pixels?: number;
	limitations: string[];
}

export interface ChangeResults {
	change_area_km2: number;
	confidence: number; // 0-1, YOUTHs derived metric, NOT NASA's
	confidence_type?: string;
	permanent_water_km2?: number;
	total_aoi_km2?: number;
	change_percentage?: number;
	changed_pixels?: number;
	valid_fraction?: number;
}

export type DataStatus = 'REAL' | 'SYNTHETIC_PLACEHOLDER';

export interface EventTiles {
	baseline_url?: string;
	post_event_url?: string;
	change_mask_url?: string;
	preview_url?: string;
	baseline_preview_url?: string;
	post_event_preview_url?: string;
	change_preview_url?: string;
	corner_coordinates?: [[number, number], [number, number], [number, number], [number, number]];
	/** Shared grayscale range of both dates' previews; absent means -25 to -5 dB. */
	display_range_db?: [number, number];
}

export interface PipelineStatistics {
	total_pixels: number;
	aoi_area_km2: number;
	pixel_area_m2: number;
	baseline_water_pixels: number;
	baseline_water_area_km2: number;
	post_event_water_pixels: number;
	post_event_water_area_km2: number;
	new_inundation_pixels: number;
	new_inundation_area_km2: number;
	water_loss_pixels: number;
	water_loss_area_km2: number;
	note?: string;
	valid_pixels: number;
	valid_fraction: number;
	threshold_db: number;
	min_cluster_pixels: number;
	lee_filter_size: number;
	detection_score: number;
	detection_score_formula: string;
}

export interface ChangeEvent {
	id: string;
	title: string;
	subtitle: string;
	phenomenon: 'flood_extent_change' | 'surface_deformation';
	summary: string;
	data_status: DataStatus;
	location: ChangeEventLocation;
	observation_dates: ObservationDates;
	source_products: Provenance[];
	processing: ProcessingMetadata;
	results: ChangeResults;
	tiles: EventTiles;
	change_geometry_url: string;
	statistics_url?: string;
	statistics?: PipelineStatistics;
	independent_validation?: IndependentValidation;
	polarimetry?: Polarimetry;
	timeseries?: TimeSeries;
	ndvi?: NdviSeries;
	processing_versions?: ProcessingVersionComparison;
	weather?: AcquisitionWeather;
	drivers?: DriverHypothesis[];
	ai_explanation: string | null;
	has_explanation?: boolean;
	curated_story?: {
		headline: string;
		context: string;
		radar_insight: string;
		impact_summary: string;
		quote?: string;
	};
	pending_real_source?: {
		note: string;
		catalog_candidate_id: string;
	};
}

export interface IndependentValidation {
	status: 'unconfirmed';
	reference: string;
	summary: string;
	candidate_pixels: number;
	primary_joint_clear_pixels: number;
	primary_window_days: number;
	exploratory: {
		window_days: number;
		baseline_date: string;
		repeat_date: string;
		baseline_offset_days: number;
		repeat_offset_days: number;
		joint_clear_pixels: number;
		land_to_water_pixels: number;
		land_to_land_pixels: number;
		unknown_pixels: number;
	};
	report_path: string;
	figure_path: string;
}

type PerPolarization<T> = { HH: T; HV: T };
type PerDate<T> = { baseline: T; repeat: T };

export interface PolarimetryClass {
	pixels: number;
	HH: PerDate<number | null>;
	HV: PerDate<number | null>;
}

/** HH/HV comparison and HH change map, from services/processing/polarimetry.py. */
export interface Polarimetry {
	method: string;
	display: {
		hv_range_db: [number, number];
		difference_range_db: [number, number];
		difference_transparent_below_db: number;
		difference_display_smoothing: string;
	};
	layers: { baseline_hv_url: string; post_event_hv_url: string; difference_hh_url: string };
	product_flags: PerDate<{ noise_correction_applied: boolean; rfi_mitigation_applied: boolean }>;
	dates: Array<{
		date: 'baseline' | 'repeat';
		granule_id: string;
		rfi_likelihood: PerPolarization<number>;
		noise_equivalent_backscatter_db: PerPolarization<number | null>;
		median_db: PerPolarization<number>;
		hh_hv_correlation: number;
	}>;
	classes: Record<
		'apparent_water_loss' | 'new_inundation_candidate' | 'water_both_dates' | 'land_both_dates',
		PolarimetryClass
	>;
	hh_difference_db: {
		aoi_median: number;
		apparent_water_loss_median: number | null;
		display_fraction_brighter: number;
		display_fraction_darker: number;
	};
	hv_assessment: { hv_usable_for_interpretation: boolean; reasons: string[] };
	record_path: string;
}

export type LandcoverClass =
	'tree_cover' | 'grassland' | 'cropland' | 'built_up' | 'permanent_water' | 'herbaceous_wetland';

/** Every Track 40 / Frame 10 pass over the AOI, from services/processing/timeseries.py. */
export interface TimeSeries {
	track: number;
	frame: number;
	inputs: { threshold_db: number; lee_filter_size: number; display_range_db: [number, number] };
	landcover_source: string;
	landcover_fractions: Partial<Record<LandcoverClass, number>>;
	/** The radar grid every map layer shares: UTM origin, shape in pixels, EPSG code. */
	grid: { x0: number; y0: number; shape: [number, number]; epsg: number };
	stable_reference: {
		class: LandcoverClass;
		relative_to: LandcoverClass;
		range_db_by_processing_version: Record<string, number>;
	};
	landcover_mask_erosion_px: number;
	erosion_sensitivity_max_db: Partial<Record<LandcoverClass, number>>;
	/** Per-pixel tests on same-processing passes, with forest pixels as the false-positive control. */
	pixel_season: {
		smoothing_px: number;
		compared_dates: { darkest_paddy: string; brightest_paddy_after: string };
		brightened_over_1db: { cropland: number; forest_control: number };
		darkened_over_1db: { cropland: number; forest_control: number };
		rice_rise_threshold_db: number;
		dark_then_rise: { cropland: number; forest_control: number };
		/** How often paddy pixels lag_m apart share a timing group, against spatially random labels. */
		timing_neighbour_agreement: { lag_m: number; observed: number; if_random: number };
		darkest_pass_periods: Array<{ from: string; to: string; cropland_km2: number; color: string }>;
		map_url: string;
	};
	/** Map layers: the land-cover classes behind the finding, and where the two-date water loss fell. */
	landcover_map: {
		map_url: string;
		water_loss_url: string;
		classes: Array<{ key: LandcoverClass; label: string; color: string; area_km2: number }>;
		uncoloured: string;
	};
	/** Where the served event's two-date water loss and gain fall, by land cover. */
	event_change_by_landcover: Record<
		'apparent_water_loss' | 'new_inundation_candidate',
		{ pixels: number; by_landcover_km2: Partial<Record<LandcoverClass, number>> }
	>;
	dates: Array<{
		/** Median HH of each class minus median HH of tree cover, which removes the scene-wide offset. */
		relative_to_forest_db: Partial<Record<LandcoverClass, number>>;
		date: string;
		granule_id: string;
		collection: string;
		processing_crid: string;
		valid_fraction: number;
		water_area_km2: number;
		hh_by_landcover: Partial<
			Record<
				LandcoverClass,
				{
					p25_db: number;
					median_db: number;
					p75_db: number;
					pixels: number;
					radar_water_fraction: number;
				}
			>
		>;
		weather: {
			era5_wind_ms: number;
			airport_max_wind_ms: number | null;
			era5_rain_24h_mm: number;
		};
		frame_url: string;
	}>;
	record_path: string;
}

/** Metadata differences between the season's two NISAR processing versions, from scripts/compare_processing_versions.py. */
export interface ProcessingVersionComparison {
	compared: Array<{
		date: string;
		product_version: string;
		software_release: string | null;
		aoi_noise_equivalent_backscatter_hh_db: number | null;
		flags: Record<string, string>;
	}>;
	flags_that_differ: Record<string, [string, string]>;
	software_release_changed: boolean;
	forest_relative_db_change: Record<'cropland' | 'built_up' | 'permanent_water', number>;
	record_path: string;
}

/** Sentinel-2 NDVI over the same land-cover cores, from services/processing/ndvi.py. */
export interface NdviSeries {
	source: string;
	min_cropland_clear_fraction: number;
	scenes: Array<{
		id: string;
		datetime: string;
		processing_baseline: string;
		cropland_clear_fraction: number;
		cropland_ndvi_median?: number;
		cropland_water_fraction?: number;
		forest_ndvi_median?: number | null;
	}>;
	record_path: string;
}

/** Wind and rain at each acquisition, from services/processing/weather.py. */
export interface AcquisitionWeather {
	dates: Array<{
		time_utc: string;
		era5: { wind_speed_ms: number; wind_gust_ms: number; rain_3h_mm: number; rain_24h_mm: number };
		metar: { reports: string[]; max_wind_ms: number | null; present_weather_prior_hours: string[] };
	}>;
	comparison: { calm_threshold_ms: number; all_near_calm: boolean };
	sources: { era5: string; metar: string };
	record_path: string;
}

export interface DriverHypothesis {
	id: string;
	/** Which observation the hypothesis tries to explain. */
	explains: string;
	title: string;
	support: 'best supported' | 'possible' | 'weakly supported';
	evidence_for: string[];
	evidence_against: string[];
	how_to_test: string;
}

export interface ExplainResponse {
	ai_explanation: string;
	generated_at: string;
	cached: boolean;
	verification: {
		cites_correct_granule: boolean;
		cites_exact_area: boolean;
		cites_confidence: boolean;
		mentions_limitations: boolean;
		grounded_numbers: {
			area_km2: number;
			confidence: number;
		};
	};
}

export interface GeoJsonFeatureCollection {
	type: 'FeatureCollection';
	features: Array<{
		type: 'Feature';
		properties: Record<string, unknown>;
		geometry: {
			type: 'Polygon' | 'MultiPolygon';
			coordinates: number[][][] | number[][][][];
		};
	}>;
}
