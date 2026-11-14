import type { ObservedScenario, SlopeScenario } from '$lib/types/scenario';
import type { ScenarioLayer } from '$lib/stores/appState.svelte';
import { SCENARIOS, ha, shortDate } from './scenarios';

export interface TourStep {
	title: string;
	headline: string;
	description: string;
	scenarioId: string;
	epochIndex: number;
	layer: ScenarioLayer;
	actionText: string;
	/** Shown on the tour card so a judge always knows the screen is real NISAR data. */
	dataStatus: 'REAL';
}

const real = SCENARIOS.find((s) => s.module === 'observed') as ObservedScenario;
const slopes = SCENARIOS.find((s) => s.module === 'slope') as SlopeScenario;

const rLast = real.epochs.length - 1;
const rm = real.metrics[rLast]!;
const rFirst = real.epochs[0];
const rEnd = real.epochs[rLast];
const u = real.uncertainty;
const pct = (r: number) => `${(r * 100).toFixed(r < 0.01 ? 2 : 1)}%`;

const sLast = slopes.epochs.length - 1;
const su = slopes.uncertainty;
const st = slopes.thresholds;
const top = slopes.candidates[0];
const sTotal = slopes.candidates.reduce((a, c) => a + c.area_m2, 0);
const cmYr = (v: number) => `${v > 0 ? '+' : ''}${v.toFixed(1)} cm/yr`;

/** Every number comes from the scenario records, so the tour can never drift from the panels. */
export const TOUR_STEPS: TourStep[] = [
	{
		title: 'The challenge',
		headline: 'Remote Myanmar: no inspectors on site, and monsoon cloud for weeks',
		description: `Open-pit mines and landslides change the land where nobody can go and optical satellites see only cloud. NISAR's L-band radar (${real.sensor.wavelength_cm} cm) sees through cloud and returns every ${real.sensor.repeat_days} days. We start with real NISAR data over Hpakant, Kachin State, the world's largest jade-mining district.`,
		scenarioId: real.id,
		epochIndex: 0,
		layer: 'sar',
		actionText: 'See the real data',
		dataStatus: 'REAL'
	},
	{
		title: 'Hpakant · baseline',
		headline: `${shortDate(rFirst.date)} 2026: a real NISAR pass, Track ${real.provenance.track} Frame ${real.provenance.frame}`,
		description: `This image is a real L2 GCOV pass from NASA's ASF DAAC. Vegetation scatters L-band radar many times and shows bright in HV; bare, dug or dumped ground and water show dark. The first two passes are averaged into the baseline. ${real.provenance.excluded.length} other passes were left out because their mode or calibration does not match; the panel lists each one.`,
		scenarioId: real.id,
		epochIndex: 0,
		layer: 'sar',
		actionText: 'Compare with the latest pass',
		dataStatus: 'REAL'
	},
	{
		title: 'Hpakant · change',
		headline: `${shortDate(rEnd.date)}: ${ha(rm.disturbed_m2)} of vegetation lost, ${ha(rm.new_water_m2)} of new water`,
		description: `Drag the swipe bar: baseline on the left, latest pass on the right. Orange patches lost more than ${real.thresholds.drop_db} dB of HV return on ground that was vegetated, and blue patches became open water. Each was seen on two consecutive passes, in patches of at least ${ha(real.thresholds.min_cluster_m2)}.`,
		scenarioId: real.id,
		epochIndex: rLast,
		layer: 'compare',
		actionText: 'Show InSAR coherence',
		dataStatus: 'REAL'
	},
	{
		title: 'Hpakant · coherence',
		headline:
			rm.coherence_disturbed !== null && rm.coherence_reference !== null
				? `Coherence ${rm.coherence_disturbed.toFixed(2)} on the changed ground, ${rm.coherence_reference.toFixed(2)} on stable vegetation`
				: 'InSAR coherence for the latest pair',
		description: `Coherence compares two passes, from a real L2 GUNW interferogram. Ground that is dug, dumped or flooded between passes decorrelates and shows dark. It supports the backscatter result but is not proof on its own: vegetation also loses some coherence at L-band.`,
		scenarioId: real.id,
		epochIndex: rLast,
		layer: 'coherence',
		actionText: 'How sure are we?',
		dataStatus: 'REAL'
	},
	{
		title: 'Hpakant · uncertainty',
		headline: `Up to ${ha(rm.expected_false_upper_m2)} could be false alarms; this is change, not proof of mining`,
		description: `Run between the two baseline passes, where little real change is expected, the same rule flags ${pct(u.single_pass_false_rate)} of vegetated ground on one pass. The app calls the result surface change consistent with excavation: mine-waste slides, landslides and monsoon moisture can look similar. No verified permit boundaries exist here, so it makes no legality claim.`,
		scenarioId: real.id,
		epochIndex: rLast,
		layer: 'sar',
		actionText: 'Now the slopes',
		dataStatus: 'REAL'
	},
	{
		title: 'Hpakant slopes · InSAR',
		headline: `${slopes.epochs.length} real NISAR interferograms measure how Hpakant's slopes moved`,
		description: `Hpakant's mine-waste slopes fail often, most deadly in the monsoon. Each real L2 GUNW pair (12 or 24 days apart) from ${shortDate(slopes.epochs[0].coherence_pair![0])} to ${shortDate(slopes.epochs[sLast].date)} gives ground motion along the radar's line of sight. This layer is the mean rate from all the pairs: blue moves toward the satellite, orange away. Blank ground could not be read on most pairs, usually because it is dug, flooded or densely forested.`,
		scenarioId: slopes.id,
		epochIndex: sLast,
		layer: 'deformation',
		actionText: 'Which slopes move?',
		dataStatus: 'REAL'
	},
	{
		title: 'Hpakant slopes · candidates',
		headline: top
			? `${slopes.candidates.length} steep patch${slopes.candidates.length === 1 ? '' : 'es'} (${ha(sTotal)}) moved faster than ${st.sigma_k}× the noise`
			: `No steep slope moved faster than ${st.sigma_k}× the noise`,
		description: `Flat, steadily coherent ground scatters by ${su.rate_sigma_cm_yr.toFixed(1)} cm/yr; a candidate is ground steeper than ${st.slope_min_deg}° (NASA's NASADEM) moving beyond ${st.sigma_k} times that, the same way on most pairs.${top ? ` The largest, ${ha(top.area_m2)} on a ${top.slope_deg}° slope, moves ${cmYr(top.rate_cm_yr)} along the line of sight.` : ''} These are places to check on the ground, not confirmed landslides: mining cuts and dumping move ground too.`,
		scenarioId: slopes.id,
		epochIndex: sLast,
		layer: 'deformation',
		actionText: 'What limits this?',
		dataStatus: 'REAL'
	},
	{
		title: 'Hpakant slopes · limits',
		headline: 'Line-of-sight motion, not elevation loss and not downslope speed',
		description: `The radar sees only motion toward or away from itself, so a slope sliding downhill can read as either, or near zero. The height-dependent part of monsoon water vapour is removed, but patchy vapour stays in the noise figure. On ${su.unread_pairs.length} pairs the phase could not be unwrapped here at all, and ground that decorrelates (dark in this coherence layer) cannot be read.`,
		scenarioId: slopes.id,
		epochIndex: sLast,
		layer: 'coherence',
		actionText: 'Wrap up',
		dataStatus: 'REAL'
	},
	{
		title: 'Data and next steps',
		headline: 'Two real NISAR workflows, every number traceable to a granule',
		description: `Surface change uses ${real.provenance.gcov_granules.length} real GCOV passes and ${real.provenance.gunw_granules.length} GUNW pairs; slope motion uses ${slopes.provenance.gunw_granules.length} GUNW interferograms and NASADEM, each listed by ID in its panel. Next: check both against dry-season NASA HLS optical imagery, field reports and GNSS. A permit check needs official concession boundaries, which are not public, so the app makes no legality claim.`,
		scenarioId: real.id,
		epochIndex: rLast,
		layer: 'sar',
		actionText: 'Finish tour',
		dataStatus: 'REAL'
	}
];
