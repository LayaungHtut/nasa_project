import record from '../../../data/validation/yangon-track40-frame10/weather.json';
import type { AcquisitionWeather, ChangeEvent } from '$lib/types/api';

/** The weather record applies only when it covers both of this event's acquisitions. */
export function weatherFor(event: ChangeEvent): AcquisitionWeather | undefined {
	const times = record.dates.map((d) => d.time_utc);
	if (
		event.data_status !== 'REAL' ||
		event.id !== record.event_id ||
		!times.includes(event.observation_dates.baseline) ||
		!times.includes(event.observation_dates.post_event)
	)
		return undefined;
	return {
		...(record as unknown as Omit<AcquisitionWeather, 'record_path'>),
		record_path: `validation/${event.id}/weather.json`
	};
}
