import type { LayoutServerLoad } from './$types';
import { getAuthoritativeEvents } from '$lib/server/events';

/**
 * Root layout server loader.
 * Populates all routes with authoritative ChangeEvents loaded directly
 * from the data/processed and data/fixtures directories.
 */
export const load: LayoutServerLoad = async () => {
	const events = await getAuthoritativeEvents();
	return {
		events
	};
};
