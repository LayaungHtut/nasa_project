import record from '../../../data/processed/yangon-track40-frame10/polarization.json';
import type { ChangeEvent, Polarimetry } from '$lib/types/api';

/** The polarization record applies to this recorded run, not arbitrary reprocessing. */
export function polarimetryFor(event: ChangeEvent): Polarimetry | undefined {
	const inputs = record.inputs;
	if (
		event.data_status !== 'REAL' ||
		event.id !== record.event_id ||
		event.processing.threshold_db !== inputs.threshold_db ||
		event.processing.speckle_filter_size !== inputs.lee_filter_size ||
		event.statistics?.water_loss_pixels !== record.classes.apparent_water_loss.pixels ||
		event.statistics?.new_inundation_pixels !== record.classes.new_inundation_candidate.pixels
	)
		return undefined;
	return {
		...(record as unknown as Omit<Polarimetry, 'record_path'>),
		record_path: `processed/${event.id}/polarization.json`
	};
}
