import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { getAuthoritativeGeometry } from '$lib/server/events';
import {
	YANGON_FIXTURE_GEOJSON,
	BAGO_FLOOD_GEOJSON,
	DELTA_GEOJSON,
	SAGAING_GEOJSON
} from '$lib/data/fixtures';

/**
 * GET /api/events/{id}/geometry
 * Serves the vectorized GeoJSON polygons of the detected change
 * Single Source of Truth: Reads directly from data/processed/[id]/change.geojson
 */
export const GET: RequestHandler = async ({ params }) => {
	// If an authoritative processed GeoJSON exists on disk, serve it directly!
	const geojson = await getAuthoritativeGeometry(params.id);
	if (geojson) {
		return json(geojson);
	}

	// Synthetic demo fixture fallbacks
	switch (params.id) {
		case 'demo-yangon-fixture':
			return json(YANGON_FIXTURE_GEOJSON);
		case 'bago-flood-2026':
			return json(BAGO_FLOOD_GEOJSON);
		case 'ayeyarwady-delta-2026':
			return json(DELTA_GEOJSON);
		case 'sagaing-fault-deformation':
			return json(SAGAING_GEOJSON);
		default:
			throw error(404, { message: `Geometry not found for event: ${params.id}` });
	}
};
