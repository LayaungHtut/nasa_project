import type { LandslideScenario, MiningScenario, ObservedScenario } from '$lib/types/scenario';
import type { ScenarioLayer } from '$lib/stores/appState.svelte';
import { SCENARIOS, compliance, forensics, ha, shortDate } from './scenarios';

export interface TourStep {
	title: string;
	headline: string;
	description: string;
	scenarioId: string;
	epochIndex: number;
	layer: ScenarioLayer;
	actionText: string;
	/** Shown on the tour card so a judge always knows whether a screen is real or simulated. */
	dataStatus: 'REAL' | 'SIMULATED';
}

const real = SCENARIOS.find((s) => s.module === 'observed') as ObservedScenario;
const mining = SCENARIOS.find((s) => s.module === 'mining') as MiningScenario;
const slide = SCENARIOS.find((s) => s.module === 'landslide') as LandslideScenario;

const rLast = real.epochs.length - 1;
const rm = real.metrics[rLast]!;
const rFirst = real.epochs[0];
const rEnd = real.epochs[rLast];
const u = real.uncertainty;
const pct = (r: number) => `${(r * 100).toFixed(r < 0.01 ? 2 : 1)}%`;

const mBreach = compliance(mining, mining.epochs.length - 1).firstBreach;
const mb = mining.metrics[mBreach];
const f = forensics(slide, slide.epochs.length - 1);
const atSlide = slide.metrics[f.slideEpoch];
const atDiversion = slide.metrics[f.diversionEpoch];

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
		actionText: 'How a permit check would work',
		dataStatus: 'REAL'
	},
	{
		title: 'Permit check · demo',
		headline: `Simulated demo: ${ha(mb.outside_beyond_tolerance_m2)} cleared beyond a permit raises an alert`,
		description: `If the licensing authority supplied concession boundaries, this check could run on the real change map. Here it runs on a SIMULATED scene with a fictional permit (${mining.permit.permit_id}): clearing more than ${mining.thresholds.tolerance_m} m outside the yellow line, above ${ha(mining.thresholds.breach_outside_m2)}, raises the alert. It is still a lead for a person to verify, not a verdict.`,
		scenarioId: mining.id,
		epochIndex: mBreach,
		layer: 'compare',
		actionText: 'Landslide demo',
		dataStatus: 'SIMULATED'
	},
	{
		title: 'Landslide · demo',
		headline: 'Simulated demo: a slope fails and dams a river',
		description: `In a SIMULATED Chin Hills valley, ${ha(atSlide.landslide_m2)} of slope loses more than ${slide.thresholds.landslide_drop_db} dB of return and coherence on it collapses to ${atSlide.coherence_at_slide?.toFixed(2)}. ${ha(atSlide.impoundment_m2)} of water ponds behind the debris.`,
		scenarioId: slide.id,
		epochIndex: f.slideEpoch,
		layer: 'coherence',
		actionText: 'Next pass',
		dataStatus: 'SIMULATED'
	},
	{
		title: 'Landslide · root cause',
		headline: `Simulated demo: the river moves ${atDiversion.channel_shift_m} m, ${f.lagDays} days after the slide`,
		description: `${slide.linkage.river_distance_km.toFixed(1)} km downstream the channel shifts, and the app links it to the slide upstream on the same river. A basin-wide flood is ${f.alternatives[0].verdict.toLowerCase()} because water above the lake barely changed. Swipe to see the old and new channel.`,
		scenarioId: slide.id,
		epochIndex: f.diversionEpoch,
		layer: 'compare',
		actionText: 'Wrap up',
		dataStatus: 'SIMULATED'
	},
	{
		title: 'Data and next steps',
		headline: 'Real NISAR where it exists, labelled demos where it does not',
		description: `The Hpakant result uses ${real.provenance.gcov_granules.length} real GCOV passes and ${real.provenance.gunw_granules.length} GUNW pairs, listed by granule ID in its panel. Next: validate it against dry-season NASA HLS optical imagery and field reports, and add official permit boundaries so the compliance check can run on real data.`,
		scenarioId: real.id,
		epochIndex: rLast,
		layer: 'sar',
		actionText: 'Finish tour',
		dataStatus: 'REAL'
	}
];
