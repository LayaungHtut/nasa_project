import type {
	LandslideScenario,
	MiningScenario,
	ObservedPatch,
	ObservedScenario,
	Scenario
} from '$lib/types/scenario';
import observed from './scenarios/hpakant-observed.json';
import mining from './scenarios/mining-compliance-mc07.json';
import landslide from './scenarios/landslide-river-diversion.json';

/** Real NISAR first (scripts/build_hpakant.py), then the two simulated demos (scripts/build_scenarios.py). */
export const SCENARIOS = [observed, mining, landslide] as unknown as Scenario[];

export const ha = (m2: number) => `${(m2 / 10_000).toFixed(1)} ha`;
export const shortDate = (iso: string) =>
	new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });

export type ObservedStage = 'baseline' | 'awaiting' | 'change' | 'within_noise';

export interface ObservedStatus {
	stage: ObservedStage;
	/** First pass whose confirmed change exceeds the null-test upper bound, or -1. */
	firstChange: number;
}

/** A change counts only when its area exceeds what the baseline-pair null test could produce by itself. */
export function observedStatus(s: ObservedScenario, i: number): ObservedStatus {
	const beyond = (m: ObservedScenario['metrics'][number]) =>
		m !== null && m.disturbed_m2 + m.new_water_m2 > m.expected_false_upper_m2;
	const firstChange = s.metrics.findIndex(beyond);
	const m = s.metrics[i];
	const stage: ObservedStage =
		i < 2 ? 'baseline' : m === null ? 'awaiting' : beyond(m) ? 'change' : 'within_noise';
	return { stage, firstChange };
}

/** Detected patches confirmed on pass i (one entry per patch), vegetation loss first, largest first. */
export function observedPatches(s: ObservedScenario, i: number): ObservedPatch[] {
	const seen = new Map<string, ObservedPatch>();
	for (const f of s.geojson.features) {
		const p = f.properties as ObservedPatch | null;
		if (p?.patch_id && p.epoch === i && !seen.has(p.patch_id)) seen.set(p.patch_id, p);
	}
	const order = { disturbed: 0, new_water: 1 };
	return [...seen.values()].sort((a, b) => order[a.kind] - order[b.kind] || b.area_m2 - a.area_m2);
}

/** The patch with this id, or null (also null for the simulated modules, which have no patch ids). */
export function findPatch(s: Scenario, id: string | null): ObservedPatch | null {
	if (!id || s.module !== 'observed') return null;
	for (const f of s.geojson.features) {
		const p = f.properties as ObservedPatch | null;
		if (p?.patch_id === id) return p;
	}
	return null;
}

/** Short reader-facing name, e.g. "Change patch 1" or "New water 2". */
export const patchLabel = (p: ObservedPatch) =>
	`${p.kind === 'disturbed' ? 'Change patch' : 'New water'} ${p.patch_id.split('-')[1]}`;

export type ComplianceLevel = 'compliant' | 'watch' | 'breach';

export interface Compliance {
	level: ComplianceLevel;
	/** First pass on which the breach rule fired, or -1. */
	firstBreach: number;
	reasons: string[];
}

/** Breach: cleared land beyond the permit plus its tolerance band exceeds the limit. Watch: any clearing past the band, or the ground beside the permit sinking. */
export function compliance(s: MiningScenario, i: number): Compliance {
	const t = s.thresholds;
	const m = s.metrics[i];
	const firstBreach = s.metrics.findIndex(
		(x) => x.outside_beyond_tolerance_m2 >= t.breach_outside_m2
	);
	const reasons: string[] = [];
	if (m.outside_beyond_tolerance_m2 > 0)
		reasons.push(
			`${ha(m.outside_beyond_tolerance_m2)} cleared more than ${t.tolerance_m} m outside the permit, up to ${m.max_distance_outside_m} m beyond it (limit ${ha(t.breach_outside_m2)})`
		);
	if (m.max_subsidence_outside_cm >= t.subsidence_watch_cm)
		reasons.push(
			`ground beside the permit moved ${m.max_subsidence_outside_cm.toFixed(1)} cm away from the satellite since the first pass, a sign of bank slumping`
		);
	if (m.low_coherence_outside_m2 > 0 && m.outside_beyond_tolerance_m2 > 0)
		reasons.push(
			`InSAR coherence collapsed over ${ha(m.low_coherence_outside_m2)} outside the permit, where the surface is being disturbed between passes`
		);
	const level: ComplianceLevel =
		m.outside_beyond_tolerance_m2 >= t.breach_outside_m2
			? 'breach'
			: m.outside_beyond_tolerance_m2 > 0 || m.max_subsidence_outside_cm >= t.subsidence_watch_cm
				? 'watch'
				: 'compliant';
	return { level, firstBreach, reasons };
}

export type ForensicStage = 'monitoring' | 'early_warning' | 'linked' | 'unexplained';

export interface Evidence {
	text: string;
	supports: boolean;
}

export interface Forensics {
	stage: ForensicStage;
	slideEpoch: number;
	diversionEpoch: number;
	lagDays: number;
	evidence: Evidence[];
	alternatives: Array<{
		title: string;
		verdict: 'Ruled out' | 'Unlikely' | 'Not tested';
		reason: string;
	}>;
}

/** Links a downstream channel shift to an earlier slide upstream on the same river, within distance and time limits. */
export function forensics(s: LandslideScenario, i: number): Forensics {
	const t = s.thresholds;
	const L = s.linkage;
	const slideEpoch = s.metrics.findIndex((m) => m.landslide_m2 >= t.landslide_min_m2);
	const diversionEpoch = s.metrics.findIndex(
		(m) => m.channel_shift_m >= t.channel_shift_m && m.new_channel_m2 >= t.new_channel_min_m2
	);
	const lagDays =
		slideEpoch >= 0 && diversionEpoch >= 0
			? s.epochs[diversionEpoch].day - s.epochs[slideEpoch].day
			: 0;
	const linkable =
		slideEpoch >= 0 &&
		diversionEpoch > slideEpoch &&
		L.slide_is_upstream &&
		L.river_distance_km <= t.link_max_km &&
		lagDays <= t.link_max_days;

	let stage: ForensicStage = 'monitoring';
	if (diversionEpoch >= 0 && i >= diversionEpoch) stage = linkable ? 'linked' : 'unexplained';
	else if (slideEpoch >= 0 && i >= slideEpoch) stage = 'early_warning';

	const slide = slideEpoch >= 0 ? s.metrics[slideEpoch] : undefined;
	const now = s.metrics[i];
	const evidence: Evidence[] = [];
	if (slide) {
		evidence.push({
			text: `${ha(slide.landslide_m2)} of slope lost more than ${t.landslide_drop_db} dB of radar return on ${shortDate(s.epochs[slideEpoch].date)}: forest stripped to bare debris.`,
			supports: true
		});
		if (slide.coherence_at_slide !== null)
			evidence.push({
				text: `InSAR coherence on the slide fell to ${slide.coherence_at_slide.toFixed(2)} across that pass (below ${t.coherence_min}): the ground surface was rearranged, not just wetted.`,
				supports: true
			});
		evidence.push({
			text: `A lake of ${ha(now.impoundment_m2)} is ponding behind the debris, so the slide is blocking the river.`,
			supports: now.impoundment_m2 > 0
		});
	}
	if (L.precursor_creep_cm > 0)
		evidence.push({
			text: `On the pass before the failure (${shortDate(s.epochs[L.precursor_pass].date)}), InSAR measured the same slope creeping ${L.precursor_creep_cm.toFixed(1)} cm away from the satellite.`,
			supports: true
		});
	if (diversionEpoch >= 0 && i >= diversionEpoch)
		evidence.push({
			text: `${L.river_distance_km.toFixed(1)} km downstream, the channel moved up to ${now.channel_shift_m} m: ${ha(now.new_channel_m2)} of new channel, ${ha(now.abandoned_channel_m2)} abandoned.`,
			supports: true
		});

	const control = Math.max(...s.metrics.map((m) => Math.abs(m.control_reach_water_change_pct)));
	return {
		stage,
		slideEpoch,
		diversionEpoch,
		lagDays,
		evidence,
		alternatives: [
			{
				title: 'Monsoon flood across the basin',
				verdict: control < 10 ? 'Ruled out' : 'Unlikely',
				reason: `Water area in the reach above the lake changed by at most ${control.toFixed(0)}%; a basin-wide flood would widen the river everywhere.`
			},
			{
				title: 'River dredging or sand mining',
				verdict: 'Unlikely',
				reason:
					'No cleared or excavated ground appears along the new channel, and the shift began only after the upstream slide.'
			},
			{
				title: 'Gradual meander migration',
				verdict: 'Ruled out',
				reason: `The channel moved ${now.channel_shift_m} m within one 12-day interval; natural meanders move metres per year.`
			}
		]
	};
}
