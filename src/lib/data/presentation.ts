import type { ChangeEvent, ObservationDates } from '$lib/types/api';

export function formatAcquisitionDate(date: string): string {
	return Number.isFinite(Date.parse(date))
		? new Date(date).toLocaleDateString('en-US', {
				month: 'short',
				day: 'numeric',
				year: 'numeric',
				timeZone: 'UTC'
			})
		: 'Synthetic scene';
}

/** Only acquired scenes become timeline steps; analysis layers are not acquisitions. */
export function observationTimeline(
	event: ChangeEvent
): NonNullable<ObservationDates['all_observations']> {
	return [
		{
			date: event.observation_dates.baseline,
			label: 'Baseline observation',
			phase: 'baseline' as const
		},
		{
			date: event.observation_dates.post_event,
			label: 'Repeat observation',
			phase: 'repeat' as const
		}
	].flatMap((observation) => {
		const source = event.source_products.find(
			(product) => product.acquisition_date === observation.date
		);
		return source && Number.isFinite(Date.parse(observation.date))
			? [{ ...observation, granule_id: source.granule_id }]
			: [];
	});
}

/** Deterministic narration, generated from the same record as the map and metrics. */
export function explainObservation(event: ChangeEvent): string {
	const status =
		event.data_status === 'REAL' ? 'NISAR radar observations' : 'Synthetic demonstration data';
	const dates = `${event.observation_dates.baseline.slice(0, 10)} and ${event.observation_dates.post_event.slice(0, 10)}`;
	const score = `The detection score ${event.results.confidence.toFixed(3)} is a heuristic, not a probability or a NASA assessment.`;
	const sources = `Source identifiers: ${event.source_products.map((source) => source.granule_id).join('; ')}.`;
	if (event.phenomenon !== 'flood_extent_change') {
		return `${status} for ${event.location.name} (${dates}) describe a ${event.results.change_area_km2} km² analysis area. ${score} ${event.processing.limitations.join(' ')} ${sources}`;
	}
	const method = event.processing.speckle_filter_size
		? `${event.processing.speckle_filter_size} × ${event.processing.speckle_filter_size} Lee filtering`
		: (event.processing.speckle_filter ?? 'the recorded speckle filter');
	const loss = event.statistics
		? ` The same comparison reports ${event.statistics.water_loss_area_km2} km² of apparent water loss. A threshold crossing alone cannot establish a physical water-level change; surface roughness is one possible explanation.`
		: '';
	const evidence = ' Independent imagery or reservoir records are needed.';
	return `${status} over ${event.location.name} on ${dates} were compared using ${method} and a ${event.processing.threshold_db} dB threshold. The pipeline flagged ${event.results.change_area_km2} km² as a new-inundation candidate.${loss} This is an unconfirmed interpretation, sensitive to processing choices.${evidence} ${score} ${sources}`;
}

export function presentEvent(event: ChangeEvent): ChangeEvent {
	const presented: ChangeEvent = {
		...event,
		observation_dates: { ...event.observation_dates, all_observations: observationTimeline(event) },
		processing: {
			...event.processing,
			speckle_filter: event.processing.speckle_filter_size
				? `${event.processing.speckle_filter_size} × ${event.processing.speckle_filter_size} Lee filter`
				: event.processing.speckle_filter
		},
		ai_explanation: explainObservation(event),
		has_explanation: true
	};
	return presented;
}
