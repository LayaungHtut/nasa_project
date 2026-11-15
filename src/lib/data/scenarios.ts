import type { ObservedPatch, ObservedScenario, Scenario } from '$lib/types/scenario';
import observed from './scenarios/hpakant-observed.json';
import slopes from './scenarios/hpakant-slopes.json';

/** Both modules are real NISAR: surface change (scripts/build_hpakant.py) and slope motion (scripts/build_slope.py). */
export const SCENARIOS = [observed, slopes] as unknown as Scenario[];

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

/** The surface-change patch with this id, or null (the slope module's candidates are looked up separately). */
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

/** Candidates largest first; the id is stable across rebuilds only while the inputs are unchanged. */
export const slopeLabel = (c: { candidate_id: string }) =>
	`Moving slope ${c.candidate_id.split('-')[1]}`;
