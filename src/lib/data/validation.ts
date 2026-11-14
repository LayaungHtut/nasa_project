import comparison from '../../../data/validation/yangon-track40-frame10/comparison.json';
import type { ChangeEvent, IndependentValidation } from '$lib/types/api';

/** The optical audit applies to this recorded run, not arbitrary reprocessing. */
export function independentValidation(event: ChangeEvent): IndependentValidation | undefined {
	const processing = comparison.processing_snapshot;
	if (
		event.data_status !== 'REAL' ||
		event.id !== comparison.event_id ||
		event.observation_dates.baseline !== comparison.nisar_dates.baseline ||
		event.observation_dates.post_event !== comparison.nisar_dates.post_event ||
		event.processing.method !== processing.method ||
		event.processing.version !== processing.version ||
		event.processing.threshold_db !== processing.threshold_db ||
		event.processing.speckle_filter_size !== processing.speckle_filter_size ||
		event.processing.min_cluster_pixels !== processing.min_cluster_pixels ||
		event.results.changed_pixels !== comparison.candidate_pixels ||
		event.results.change_area_km2 !== comparison.results_snapshot.change_area_km2
	)
		return undefined;
	const pair = comparison.exploratory;
	return {
		status: 'unconfirmed',
		reference: comparison.reference,
		summary: comparison.summary,
		candidate_pixels: comparison.candidate_pixels,
		primary_joint_clear_pixels: comparison.primary.joint_clear_pixels,
		primary_window_days: comparison.primary.window_days,
		exploratory: {
			window_days: pair.window_days,
			baseline_date: comparison.scenes.find((scene) => scene.id === pair.baseline_scene)!.datetime,
			repeat_date: comparison.scenes.find((scene) => scene.id === pair.repeat_scene)!.datetime,
			baseline_offset_days: pair.baseline_offset_days,
			repeat_offset_days: pair.repeat_offset_days,
			joint_clear_pixels: pair.joint_clear_pixels,
			land_to_water_pixels: pair.land_to_water_pixels,
			land_to_land_pixels: pair.land_to_land_pixels,
			unknown_pixels: pair.unknown_pixels
		},
		report_path: `validation/${event.id}/comparison.json`,
		figure_path: `validation/${event.id}/optical-comparison.png`
	};
}
