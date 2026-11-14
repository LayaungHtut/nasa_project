import record from '../../../data/processed/yangon-track40-frame10/timeseries.json';
import ndviRecord from '../../../data/validation/yangon-track40-frame10/ndvi-series.json';
import versionsRecord from '../../../data/validation/yangon-track40-frame10/processing-versions.json';
import type {
	ChangeEvent,
	LandcoverClass,
	NdviSeries,
	ProcessingVersionComparison,
	TimeSeries
} from '$lib/types/api';

/** The time series applies to this recorded run, not arbitrary reprocessing. */
export function timeSeriesFor(event: ChangeEvent): TimeSeries | undefined {
	const dates = record.dates.map((d) => d.date);
	if (
		event.data_status !== 'REAL' ||
		event.id !== record.event_id ||
		event.processing.threshold_db !== record.inputs.threshold_db ||
		event.processing.speckle_filter_size !== record.inputs.lee_filter_size ||
		!dates.includes(event.observation_dates.baseline) ||
		!dates.includes(event.observation_dates.post_event)
	)
		return undefined;
	return {
		...(record as unknown as Omit<TimeSeries, 'record_path'>),
		record_path: `processed/${event.id}/timeseries.json`
	};
}

function pearson(a: number[], b: number[]): number {
	const mean = (v: number[]) => v.reduce((s, x) => s + x, 0) / v.length;
	const [ma, mb] = [mean(a), mean(b)];
	const cov = a.reduce((s, x, i) => s + (x - ma) * (b[i] - mb), 0);
	const sd = (v: number[], m: number) => Math.sqrt(v.reduce((s, x) => s + (x - m) ** 2, 0));
	return cov / (sd(a, ma) * sd(b, mb));
}

/**
 * Season-level findings, computed from the record so every view quotes the same numbers.
 * Only passes with the first date's processing version are compared: the newer version
 * reads darker everywhere, and that step is as large as some of the changes here.
 */
export function seasonFindings(ts: TimeSeries) {
	const same = ts.dates.filter((d) => d.processing_crid === ts.dates[0].processing_crid);
	const paddy = same.map((d) => ({ date: d.date, value: d.relative_to_forest_db.cropland ?? NaN }));
	const paddyLow = paddy.reduce((a, b) => (b.value < a.value ? b : a));
	const paddyPeak = paddy
		.filter((p) => p.date > paddyLow.date)
		.reduce((a, b) => (b.value > a.value ? b : a), paddyLow);
	const reservoir = same.map((d) => d.hh_by_landcover.permanent_water?.median_db ?? NaN);
	const loss = ts.event_change_by_landcover.apparent_water_loss;
	const lossTotal = loss.pixels / 1e4; // 10 m pixels: 100 m² each
	const lossPaddy = loss.by_landcover_km2.cropland ?? 0;
	return {
		comparableCount: same.length,
		paddyLow,
		paddyPeak,
		paddyRise: paddyPeak.value - paddyLow.value,
		laterVersionCount: ts.dates.length - same.length,
		reservoirRange: [Math.min(...reservoir), Math.max(...reservoir)] as [number, number],
		windCorrelation: pearson(
			same.map((d) => d.weather.era5_wind_ms),
			same.map((d) => d.relative_to_forest_db.permanent_water ?? NaN)
		),
		rainCorrelation: pearson(
			same.map((d) => d.weather.era5_rain_24h_mm),
			same.map((d) => d.hh_by_landcover.tree_cover?.median_db ?? NaN)
		),
		builtRange: ts.stable_reference.range_db_by_processing_version[ts.dates[0].processing_crid],
		loss: {
			total: lossTotal,
			paddy: lossPaddy,
			paddyPct: Math.round((lossPaddy / lossTotal) * 100),
			reservoir: loss.by_landcover_km2.permanent_water ?? 0
		},
		candidatePaddy:
			ts.event_change_by_landcover.new_inundation_candidate.by_landcover_km2.cropland ?? 0
	};
}

/** Optical NDVI on the same land-cover cores; only meaningful next to the matching radar series. */
export function ndviFor(event: ChangeEvent): NdviSeries | undefined {
	const series = timeSeriesFor(event);
	if (
		!series ||
		ndviRecord.event_id !== event.id ||
		ndviRecord.landcover !== record.landcover_source ||
		ndviRecord.landcover_mask_erosion_px !== record.landcover_mask_erosion_px
	)
		return undefined;
	return {
		...(ndviRecord as unknown as Omit<NdviSeries, 'record_path'>),
		record_path: `validation/${event.id}/ndvi-series.json`
	};
}

/** Paddy minus forest NDVI on usable scenes: removes scene-wide shifts, as for the radar. */
export function ndviFindings(ndvi: NdviSeries) {
	const usable = ndvi.scenes.filter(
		(s) => s.cropland_ndvi_median !== undefined && typeof s.forest_ndvi_median === 'number'
	);
	const rel = usable.map((s) => s.cropland_ndvi_median! - s.forest_ndvi_median!);
	const paddy = usable.map((s) => s.cropland_ndvi_median!);
	return {
		usable,
		paddyRange: [Math.min(...paddy), Math.max(...paddy)] as [number, number],
		relRange: [Math.min(...rel), Math.max(...rel)] as [number, number]
	};
}

/** Attached only when both compared passes are dates in the season record. */
export function processingVersionsFor(event: ChangeEvent): ProcessingVersionComparison | undefined {
	const series = timeSeriesFor(event);
	const dates = new Set(series?.dates.map((d) => d.date));
	if (
		!series ||
		versionsRecord.event_id !== event.id ||
		!versionsRecord.compared.every((c) => dates.has(c.date))
	)
		return undefined;
	return {
		...(versionsRecord as unknown as Omit<ProcessingVersionComparison, 'record_path'>),
		record_path: `validation/${event.id}/processing-versions.json`
	};
}

/** Change between two passes, relative to forest so the scene-wide shift drops out. */
export function periodChange(ts: TimeSeries, from: number, to: number) {
	const [a, b] = [ts.dates[from], ts.dates[to]];
	const delta = (c: LandcoverClass) =>
		(b.relative_to_forest_db[c] ?? NaN) - (a.relative_to_forest_db[c] ?? NaN);
	return {
		days: Math.round((Date.parse(b.date) - Date.parse(a.date)) / 864e5),
		sameProcessing: a.processing_crid === b.processing_crid,
		paddy: delta('cropland'),
		reservoir: delta('permanent_water'),
		builtUp: delta('built_up')
	};
}

/** Suggested periods, found from the record rather than hardcoded dates. */
export function periodPresets(ts: TimeSeries, baseline: string, post: string) {
	const f = seasonFindings(ts);
	const idx = (date: string) => ts.dates.findIndex((d) => d.date === date);
	const lastSame = ts.dates.findLastIndex((d) => d.processing_crid === ts.dates[0].processing_crid);
	return [
		{ label: 'Flooded → grown', from: idx(f.paddyLow.date), to: idx(f.paddyPeak.date) },
		{ label: 'Season start → flooded', from: 0, to: idx(f.paddyLow.date) },
		{ label: 'Two-date analysis', from: idx(baseline), to: idx(post) },
		{ label: 'Whole season', from: 0, to: lastSame }
	].filter((p) => p.from >= 0 && p.to > p.from);
}
