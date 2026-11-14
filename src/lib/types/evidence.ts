import type { GeoJsonFeatureCollection } from './api';

export type RadarReference = 'baseline' | 'repeat';

export interface OpticalScene {
	id: string;
	datetime: string;
	baseline_offset_days: number;
	repeat_offset_days: number;
	image_path: string;
	source_url: string;
	scl_source_url: string;
}

export interface CandidateEvidence {
	component: number;
	centroid_lon_lat: [number, number];
	candidate_pixels: number;
	area_m2: number;
	joint_clear_pixels: number;
	land_to_water_pixels: number;
	land_to_land_pixels: number;
	water_to_water_pixels: number;
	water_to_land_pixels: number;
	unknown_pixels: number;
	references: Array<{
		scene_id: string;
		water_pixels: number;
		land_pixels: number;
		unknown_pixels: number;
	}>;
}

export interface OpticalEvidence {
	event_id: string;
	candidate_mask_sha256: string;
	nisar_dates: { baseline: string; post_event: string };
	corner_coordinates: [[number, number], [number, number], [number, number], [number, number]];
	scenes: OpticalScene[];
	candidates: CandidateEvidence[];
	geometry: GeoJsonFeatureCollection;
}
