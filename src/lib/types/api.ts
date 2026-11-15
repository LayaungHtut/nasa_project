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
