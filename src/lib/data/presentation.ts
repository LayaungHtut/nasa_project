import type { ChangeEvent, ObservationDates } from '$lib/types/api';
import { independentValidation } from './validation';
import { polarimetryFor } from './polarimetry';
import { ndviFor, processingVersionsFor, seasonFindings, timeSeriesFor } from './timeseries';
import { weatherFor } from './weather';
import { driverHypotheses, localAcquisitionTime } from './drivers';

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
	const season = timeSeriesFor(event);
	const paddy = season ? seasonFindings(season) : undefined;
	const loss = event.statistics
		? paddy
			? ` The same comparison reports ${event.statistics.water_loss_area_km2} km² of apparent water loss; ${paddy.loss.paddyPct}% of it lies on paddy fields in the ESA WorldCover map and ${paddy.loss.reservoir.toFixed(3)} km² on the reservoir, so it reflects the rice fields changing rather than the reservoir level. Across ${season!.dates.length} NISAR passes the paddy fields brighten by ${paddy.paddyRise.toFixed(1)} dB relative to forest as the season progresses.`
			: ` The same comparison reports ${event.statistics.water_loss_area_km2} km² of apparent water loss. A threshold crossing alone cannot establish a physical water-level change; surface roughness is one possible explanation.`
		: '';
	const validation = independentValidation(event);
	const evidence = validation
		? ` Independent Sentinel-2 check: ${validation.summary} The exploratory optical dates are ${validation.exploratory.baseline_date.slice(0, 10)} and ${validation.exploratory.repeat_date.slice(0, 10)}, about four days away from each radar date. These reference classes are not field ground truth.`
		: ' Independent imagery or reservoir records are needed.';
	return `${status} over ${event.location.name} on ${dates} were compared using ${method} and a ${event.processing.threshold_db} dB threshold. The pipeline flagged ${event.results.change_area_km2} km² as a new-inundation candidate.${loss} This is an unconfirmed interpretation, sensitive to processing choices.${evidence} ${score} ${sources}`;
}

export function presentEvent(event: ChangeEvent): ChangeEvent {
	const presented: ChangeEvent = {
		...event,
		independent_validation: independentValidation(event),
		polarimetry: polarimetryFor(event),
		timeseries: timeSeriesFor(event),
		ndvi: ndviFor(event),
		processing_versions: processingVersionsFor(event),
		weather: weatherFor(event),
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
	presented.drivers = driverHypotheses(presented);
	if (event.id === 'yangon-track40-frame10') {
		const ts = presented.timeseries;
		if (ts) {
			const f = seasonFindings(ts);
			const day = (iso: string) => formatAcquisitionDate(iso).replace(/, \d{4}$/, '');
			presented.title = 'Hlawga rice season, Yangon Region (NISAR 2026)';
			presented.subtitle = `${ts.dates.length} NISAR passes over the rice fields around Hlawga Reservoir, Myanmar`;
			presented.summary = `Follow the paddy fields north of Yangon through the 2026 monsoon, one radar pass every 12 days, and see why a changed radar signal is not the same as a flood.`;
			presented.curated_story = {
				headline: 'A rice season, seen through the clouds',
				context: `Hlawga Reservoir lies about 30 km north of downtown Yangon and supplies drinking water to a city of more than five million people. Paddy fields cover ${Math.round((ts.landcover_fractions.cropland ?? 0) * 100)}% of the study area around it. From ${day(ts.dates[0].date)} to ${day(ts.dates[ts.dates.length - 1].date)}, NISAR passed overhead ${ts.dates.length} times at 05:32 Myanmar time, through monsoon clouds that often hide the ground from optical satellites.`,
				radar_insight: `Flooded paddies reflect radar away like calm water and look dark. As rice grows, its stems and the water beneath bounce the signal back, and the fields brighten. Here they were darkest on ${day(f.paddyLow.date)} and brightened by ${f.paddyRise.toFixed(1)} dB by ${day(f.paddyPeak.date)}. That same change explains ${f.loss.paddyPct}% of the "water loss" a two-date comparison found: the fields changed, not the reservoir.`,
				impact_summary: `Farmers, irrigation planners and water managers need to know when fields are flooded and when crops are growing, even when clouds block the view. This season of NISAR data shows that timing from space, with every number traceable to its source. Field records would confirm it.`
			};
			return presented;
		}
		presented.subtitle = 'Two NISAR observations of Hlawga Reservoir, Myanmar';
		presented.summary = `Compare radar backscatter on ${event.observation_dates.baseline.slice(0, 10)} and ${event.observation_dates.post_event.slice(0, 10)}. Investigate possible water-extent changes across the study area and the limits of threshold-based water mapping.`;
		presented.curated_story = {
			headline: 'Did the water change, or did its radar signal?',
			context: `Hlawga Reservoir lies about 30 km north of downtown Yangon, beside Hlawga National Park, and is one of the reservoirs that supply drinking water to Yangon, a city of more than five million people. Paddy fields surround it. NISAR passed over at ${localAcquisitionTime(event.observation_dates.baseline)} and ${localAcquisitionTime(event.observation_dates.post_event)} (Myanmar time), in the middle of the monsoon, when clouds often hide the ground from optical satellites. This case study asks what the radar signal can tell us, and what still needs checking.`,
			radar_insight: `Smooth water often appears dark in SAR. Here, a scene-specific ${event.processing.threshold_db} dB threshold identifies candidate water pixels; wind, surface roughness and other smooth surfaces can change that classification.`,
			impact_summary: presented.independent_validation
				? `The ${event.results.change_area_km2} km² candidate was checked against Sentinel-2 optical observations. Clouds and acquisition-time differences limit the comparison; water change remains unconfirmed. Inspect the dated optical overlays and agreement counts.`
				: `The ${event.results.change_area_km2} km² candidate can guide closer inspection of the study area. Compare it with independent imagery or water-level records before concluding that inundation occurred.`
		};
	}
	return presented;
}
