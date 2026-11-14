import type { ChangeEvent, DriverHypothesis } from '$lib/types/api';
import { ndviFindings, seasonFindings } from './timeseries';

/** Local (Myanmar Time, UTC+6:30) clock time and date of an acquisition. */
export function localAcquisitionTime(iso: string): string {
	return new Date(iso).toLocaleString('en-US', {
		timeZone: 'Asia/Yangon',
		hour: '2-digit',
		minute: '2-digit',
		hourCycle: 'h23',
		month: 'short',
		day: 'numeric'
	});
}

const db = (value: number) => `${value.toFixed(1)} dB`;

/**
 * Competing explanations for what the radar shows, each tied to recorded numbers.
 * Hypotheses only: none is confirmed, and each says what evidence would decide it.
 */
export function driverHypotheses(event: ChangeEvent): DriverHypothesis[] {
	const stats = event.statistics;
	const pol = event.polarimetry;
	const threshold = event.processing.threshold_db;
	if (
		event.data_status !== 'REAL' ||
		event.phenomenon !== 'flood_extent_change' ||
		!stats ||
		!pol ||
		threshold === undefined
	)
		return [];

	const loss = pol.classes.apparent_water_loss;
	const land = pol.classes.land_both_dates;
	const lossBefore = loss.HH.baseline ?? NaN;
	const lossAfter = loss.HH.repeat ?? NaN;
	const landAfter = land.HH.repeat ?? NaN;
	const noiseFloor =
		pol.dates.reduce((sum, d) => sum + (d.noise_equivalent_backscatter_db.HH ?? NaN), 0) /
		pol.dates.length;
	const lossShare = Math.round((stats.water_loss_area_km2 / stats.baseline_water_area_km2) * 100);
	const brighter = Math.round(pol.hh_difference_db.display_fraction_brighter * 100);
	const times = [event.observation_dates.baseline, event.observation_dates.post_event]
		.map(localAcquisitionTime)
		.join(' and ');
	const optical = event.independent_validation?.exploratory;
	const lossLabel = `${stats.water_loss_area_km2} km² apparent water loss`;

	const weather = event.weather;
	const calm = weather?.comparison.all_near_calm ?? false;
	const reservoirAboveFloor = `On the first date, reservoir pixels read about ${db(lossBefore)} in HH, about ${Math.round(lossBefore - noiseFloor)} dB above the product's own noise floor (${db(noiseFloor)}). Calm open water usually sits near that floor.`;
	const keptWaterSignature = `The "lost" pixels brightened by a median ${db(pol.hh_difference_db.apparent_water_loss_median ?? NaN)} to ${db(lossAfter)}, just enough to cross the ${threshold} dB threshold. Land around them reads about ${db(landAfter)}, so they still look far more like water than land.`;
	const opticalWater = optical
		? [
				`The Sentinel-2 overview from ${optical.repeat_date.slice(0, 10)} still shows the reservoir as a dark water body.`
			]
		: [];

	const season = event.timeseries ? seasonFindings(event.timeseries) : undefined;
	const greenness = event.ndvi ? ndviFindings(event.ndvi) : undefined;
	const versions = event.processing_versions;
	const v1Water = event.timeseries?.dates.find((d) => d.date === versions?.compared[1].date)
		?.hh_by_landcover.permanent_water?.median_db;
	const seasonDate = (iso: string) =>
		new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });
	const lossOnPaddy = season
		? [
				`Checked against the independent ESA WorldCover land-cover map, ${season.loss.paddyPct}% of the ${lossLabel.split(' ')[0]} km² (${season.loss.paddy.toFixed(2)} km²) lies on paddy fields and only ${season.loss.reservoir.toFixed(3)} km² on the reservoir.`
			]
		: [];
	const windSeason = season
		? [
				`Across ${season.comparableCount} NISAR passes, reservoir brightness does not follow wind (correlation ${season.windCorrelation.toFixed(2)}).`
			]
		: [];

	const weatherEvidence: string[] = [];
	if (weather) {
		const [first, second] = weather.dates;
		const observed = (d: typeof first) =>
			d.metar.max_wind_ms === null ? 'no report' : `${d.metar.max_wind_ms.toFixed(1)} m/s`;
		weatherEvidence.push(
			`Weather at the two passes (${times}, Myanmar time): Yangon airport reported ${observed(first)} and ${observed(second)}; the ERA5 weather model gives ${first.era5.wind_speed_ms.toFixed(1)} and ${second.era5.wind_speed_ms.toFixed(1)} m/s.${calm ? ` Both mornings were near calm (under ${weather.comparison.calm_threshold_ms} m/s), so wind does not explain why the second date is brighter.` : ''}`
		);
		const rainBefore = first.metar.present_weather_prior_hours;
		if (rainBefore.length && !second.metar.present_weather_prior_hours.length)
			weatherEvidence.push(
				`The only rain reported fell before the first pass (last report at ${rainBefore[rainBefore.length - 1].split(' ')[0]} UTC). Rain ripples water, so it would brighten the first date, not the second.`
			);
	}

	const hypotheses: DriverHypothesis[] = [
		...(calm
			? [
					{
						id: 'not-wind',
						explains: 'why the reservoir reads bright even on calm mornings',
						title: 'Something other than wind keeps the water bright',
						support: 'possible' as const,
						evidence_for: [
							reservoirAboveFloor,
							'Weather records show both mornings near calm, so wind ripples are unlikely to be the cause.',
							...(season
								? [
										`The reservoir reads between ${db(season.reservoirRange[0])} and ${db(season.reservoirRange[1])} on all ${season.comparableCount} comparable passes, so the brightness is persistent, not a one-off.`,
										...windSeason
									]
								: []),
							...(versions?.software_release_changed
								? [
										`When NISAR's processing software changed (${versions.compared[0].software_release} to ${versions.compared[1].software_release}, from ${seasonDate(versions.compared[1].date)}), the reservoir read ${Math.abs(versions.forest_relative_db_change.permanent_water).toFixed(1)} dB darker relative to forest, while paddy and built-up land moved by ${Math.max(Math.abs(versions.forest_relative_db_change.cropland), Math.abs(versions.forest_relative_db_change.built_up)).toFixed(1)} dB or less. Noise correction is off in both versions and the noise floor is unchanged, so part of the reservoir's brightness in the earlier products likely came from processing, not the water.${v1Water !== undefined && versions.compared[1].aoi_noise_equivalent_backscatter_hh_db !== null ? ` Even in the newer products it reads ${db(v1Water)}, still about ${Math.round(v1Water - versions.compared[1].aoi_noise_equivalent_backscatter_hh_db)} dB above the noise floor, so processing does not explain all of it.` : ''}`
									]
								: [])
						],
						evidence_against: [
							...(optical
								? [
										`The Sentinel-2 overview from ${optical.repeat_date.slice(0, 10)} shows dark open water, with no obvious plant mats at 10 m resolution.`
									]
								: []),
							'Nobody has checked the reservoir surface on the ground. Candidates include floating or emergent plants, or an effect of processing in these provisional products, which had no noise correction.'
						],
						how_to_test:
							'Look for plant mats in a clear, close-date optical image of the reservoir, ask park staff or local residents, and follow the reservoir through more passes from the newer NISAR processing to see where it settles.'
					}
				]
			: []),
		{
			id: 'roughened-water',
			explains: lossLabel,
			title: 'Wind or rain roughened the reservoir surface',
			support: calm || season ? 'weakly supported' : 'best supported',
			evidence_for: [
				...(calm ? [] : [reservoirAboveFloor]),
				keptWaterSignature,
				'On the second date the remaining dark pixels are scattered specks rather than one water body (validation report, Investigation 2).',
				...opticalWater
			],
			evidence_against: [
				...lossOnPaddy,
				...windSeason,
				...(weather
					? weatherEvidence
					: ['No wind, rain or water-level record for the acquisition times has been checked yet.'])
			],
			how_to_test: weather
				? 'Compare reservoir brightness with wind across more NISAR passes: if wind drives it, the windier mornings should be the brighter ones.'
				: `Check wind and rain near Hlawga at ${times} (Myanmar time), for example in Yangon International Airport weather reports, and compare with reservoir level records.`
		},
		{
			id: 'edge-inundation',
			explains: `${event.results.change_area_km2} km² new-inundation candidate`,
			title: 'Water rose slightly at the reservoir edge',
			support: 'possible',
			evidence_for: [
				'Candidate pixels sit along the reservoir shoreline, not scattered across the study area.',
				...(optical
					? [
							`In the ±${optical.window_days}-day Sentinel-2 comparison, ${optical.land_to_water_pixels} candidate cells changed from land to water.`
						]
					: [])
			],
			evidence_against: [
				...(season
					? [
							`On the WorldCover land-cover map, ${season.candidatePaddy.toFixed(3)} km² of the ${event.results.change_area_km2} km² candidate lies on paddy fields, so field flooding is as likely as a rise in the reservoir.`
						]
					: []),
				'The candidate area changes by about two orders of magnitude across reasonable thresholds and filter sizes.',
				...(optical
					? [
							`${optical.land_to_land_pixels} candidate cells stayed land in Sentinel-2 and ${optical.unknown_pixels} were hidden by cloud.`
						]
					: [])
			],
			how_to_test:
				'Use higher-resolution imagery close to the radar dates, or visit the flagged shoreline.'
		},
		{
			id: 'paddy-growth',
			explains: season
				? `${brighter}% of the study area brightening, and ${season.loss.paddyPct}% of the ${lossLabel}`
				: `${brighter}% of the study area brightened by more than ${pol.display.difference_transparent_below_db} dB`,
			title: 'Rice grew in the surrounding paddy fields',
			support: season ? 'best supported' : 'possible',
			evidence_for: [
				'The brightening is concentrated in the rectangular field blocks west and north of the reservoir. Built-up areas change little.',
				'Late August to September falls in the monsoon rice season in lower Myanmar. At L-band, HH backscatter usually rises as rice stems grow above standing water, because the signal bounces between the water and the stems (double-bounce scattering).',
				...lossOnPaddy,
				...(season
					? [
							`Across ${season.comparableCount} passes, paddy fields were darkest relative to forest on ${seasonDate(season.paddyLow.date)}, when flooded fields looked like water, then brightened by ${season.paddyRise.toFixed(1)} dB to ${seasonDate(season.paddyPeak.date)}: the shape of a growing rice crop.`,
							`Tested patch by patch, ${Math.round(event.timeseries!.pixel_season.brightened_over_1db.cropland * 100)}% of paddy brightened by more than 1 dB over those dates, against ${Math.round(event.timeseries!.pixel_season.brightened_over_1db.forest_control * 100)}% of forest, so the change is widespread and specific to the fields.`
						]
					: [])
			],
			evidence_against: [
				'No crop calendar or field survey for these fields has been checked. WorldCover marks them as cropland but does not name the crop.',
				...(greenness
					? [
							`Sentinel-2 does not show the growth directly: on ${greenness.usable.length} cloud-free dates the fields were already green and their NDVI relative to forest stayed between ${greenness.relRange[0].toFixed(2)} and ${greenness.relRange[1].toFixed(2)}. Greenness levels off once a rice canopy closes, so this neither confirms nor rules out continued growth.`
						]
					: []),
				...(season
					? [
							`Rain lifts the whole scene on some dates (correlation ${season.rainCorrelation.toFixed(2)} with forest brightness); comparing with forest removes most of that, but not necessarily all.`
						]
					: ['Wetter soil or rain on the fields could also raise backscatter.'])
			],
			how_to_test: greenness
				? 'Ask local farmers when they planted, or check a crop calendar for the Hlawga fields. Planting dates would test the Field Timing map directly; Sentinel-2 cannot settle it here, with too few clear scenes in the monsoon.'
				: 'Compare a Sentinel-2 vegetation index (NDVI) time series for the same fields, or ask local farmers when they planted.'
		},
		{
			id: 'drawdown',
			explains: lossLabel,
			title: 'The reservoir level actually fell',
			support: 'weakly supported',
			evidence_for: ['Fewer pixels met the water threshold on the second date.'],
			evidence_against: [
				...lossOnPaddy,
				`Losing ${lossShare}% of the classified water surface in 12 days would need a dramatic drawdown during the monsoon, when reservoirs normally fill.`,
				`The "lost" pixels stayed much darker than land (${db(lossAfter)} vs ${db(landAfter)}).`
			],
			how_to_test: 'Ask the reservoir operator for daily water-level records for the two dates.'
		}
	];
	const rank: Record<DriverHypothesis['support'], number> = {
		'best supported': 0,
		possible: 1,
		'weakly supported': 2
	};
	return hypotheses.sort((a, b) => rank[a.support] - rank[b.support]);
}
