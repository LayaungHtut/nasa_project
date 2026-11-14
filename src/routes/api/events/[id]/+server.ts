import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { getAuthoritativeEvent } from '$lib/server/events';

/**
 * GET /api/events/{id}
 * Returns full detail for an individual authoritative ChangeEvent
 * Single Source of Truth: Reads directly from data/processed and data/fixtures.
 */
export const GET: RequestHandler = async ({ params }) => {
	const event = await getAuthoritativeEvent(params.id);

	if (!event) {
		throw error(404, {
			message: `ChangeEvent not found with id: ${params.id}`
		});
	}

	return json(event, {
		headers: {
			'Cache-Control': 'public, max-age=300',
			'Access-Control-Allow-Origin': '*'
		}
	});
};
