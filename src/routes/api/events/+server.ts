import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { getAuthoritativeEvents } from '$lib/server/events';

/**
 * GET /api/events
 * Returns the catalog of authoritative ChangeEvents per docs/api/api-contract.md
 * Single Source of Truth: Reads directly from data/processed and data/fixtures.
 */
export const GET: RequestHandler = async () => {
	const events = await getAuthoritativeEvents();

	return json(
		{ events },
		{
			headers: {
				'Cache-Control': 'public, max-age=300',
				'Access-Control-Allow-Origin': '*'
			}
		}
	);
};
