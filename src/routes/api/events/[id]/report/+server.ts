import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { getAuthoritativeEvent } from '$lib/server/events';
import { buildReport } from '$lib/server/report';

/**
 * GET /api/events/{id}/report
 * A self-contained HTML analysis report, downloaded as a file. Only real events with a
 * season record have one: a synthetic scenario must never read like an observation report.
 */
export const GET: RequestHandler = async ({ params }) => {
	const event = await getAuthoritativeEvent(params.id);
	const html = event ? buildReport(event) : undefined;
	if (!html) throw error(404, { message: `No analysis report for event: ${params.id}` });
	return new Response(html, {
		headers: {
			'Content-Type': 'text/html; charset=utf-8',
			'Content-Disposition': `attachment; filename="${params.id}-report.html"`,
			'Cache-Control': 'no-store'
		}
	});
};
