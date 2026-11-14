import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { getAuthoritativeEvent } from '$lib/server/events';
import { explainObservation } from '$lib/data/presentation';
import type { ExplainResponse } from '$lib/types/api';

/** Deterministic summary of the authoritative record; no model inference. */
export const POST: RequestHandler = async ({ params }) => {
	const event = await getAuthoritativeEvent(params.id);
	if (!event) error(404, 'Event not found');
	const explanation = explainObservation(event);
	const response: ExplainResponse = {
		ai_explanation: explanation,
		generated_at: new Date().toISOString(),
		cached: false,
		verification: {
			cites_correct_granule: event.source_products.every((source) =>
				explanation.includes(source.granule_id)
			),
			cites_exact_area: explanation.includes(`${event.results.change_area_km2} km²`),
			cites_confidence: explanation.includes(event.results.confidence.toFixed(3)),
			mentions_limitations: explanation.includes('not a probability'),
			grounded_numbers: {
				area_km2: event.results.change_area_km2,
				confidence: event.results.confidence
			}
		}
	};
	return json(response);
};
