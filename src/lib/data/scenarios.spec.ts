import { describe, expect, it } from 'vitest';
import {
	SCENARIOS,
	findPatch,
	observedPatches,
	observedStatus,
	patchLabel,
	slopeLabel
} from './scenarios';
import type { ObservedScenario, SlopeScenario } from '$lib/types/scenario';

const slopes = SCENARIOS.find((s) => s.module === 'slope') as SlopeScenario;
const observed = SCENARIOS.find((s) => s.module === 'observed') as ObservedScenario;

describe('real Hpakant observations', () => {
	it("lists each pass's patches once, and their areas add up to the pass totals", () => {
		observed.metrics.forEach((m, i) => {
			const patches = observedPatches(observed, i);
			if (!m) return expect(patches).toEqual([]);
			const sum = (kind: string) =>
				patches.filter((p) => p.kind === kind).reduce((a, p) => a + p.area_m2, 0);
			expect(sum('disturbed')).toBe(m.disturbed_m2);
			expect(sum('new_water')).toBe(m.new_water_m2);
			expect(new Set(patches.map((p) => p.patch_id)).size).toBe(patches.length);
			expect(patches.every((p) => p.hv_db.length === observed.epochs.length)).toBe(true);
		});
	});

	it('orders vegetation loss before water, largest first, and finds patches by id', () => {
		const patches = observedPatches(observed, observed.epochs.length - 1);
		const kinds = patches.map((p) => p.kind);
		expect(kinds.indexOf('new_water')).toBeGreaterThan(kinds.lastIndexOf('disturbed'));
		const loss = patches.filter((p) => p.kind === 'disturbed').map((p) => p.area_m2);
		expect(loss).toEqual([...loss].sort((a, b) => b - a));
		expect(findPatch(observed, patches[0].patch_id)).toEqual(patches[0]);
		expect(patchLabel(patches[0])).toBe('Change patch 1');
		expect(findPatch(observed, 'nope')).toBeNull();
		expect(findPatch(slopes, patches[0].patch_id)).toBeNull();
	});

	it('is labelled real and traces every pass to a NISAR granule', () => {
		expect(observed.data_status).toBe('REAL');
		for (const e of observed.epochs)
			expect(e.granule_id).toMatch(/^NISAR_L2_PR_GCOV_\d{3}_062_D_075_/);
		expect(observed.provenance.gcov_granules).toEqual(observed.epochs.map((e) => e.granule_id));
		expect(observed.epochs.every((e) => e.displacement_url === null)).toBe(true);
	});

	it('only reports change after baseline and confirmation passes', () => {
		const stages = observed.epochs.map((_, i) => observedStatus(observed, i).stage);
		expect(stages.slice(0, 3)).toEqual(['baseline', 'baseline', 'awaiting']);
		expect(observed.metrics.slice(0, 3)).toEqual([null, null, null]);
	});

	it('counts change only beyond what the null test allows', () => {
		const i = observed.epochs.length - 1;
		const m = observed.metrics[i]!;
		const quiet = {
			...observed,
			metrics: observed.metrics.map((x) =>
				x ? { ...x, disturbed_m2: 0, new_water_m2: x.expected_false_upper_m2 } : x
			)
		};
		expect(observedStatus(quiet, i).stage).toBe('within_noise');
		expect(observedStatus(quiet, i).firstChange).toBe(-1);
		expect(m.expected_false_upper_m2).toBeGreaterThanOrEqual(m.expected_false_m2);
	});
});

describe('real Hpakant slope motion', () => {
	it('is labelled real and traces every pair to a GUNW and every backdrop to a GCOV granule', () => {
		expect(slopes.data_status).toBe('REAL');
		for (const e of slopes.epochs) {
			expect(e.gunw_granule_id).toMatch(/^NISAR_L2_PR_GUNW_\d{3}_062_D_075_/);
			expect(e.granule_id).toMatch(/^NISAR_L2_PR_GCOV_\d{3}_062_D_075_/);
			expect(e.coherence_pair![1]).toBe(e.date);
		}
		expect(slopes.provenance.gunw_granules).toEqual(slopes.epochs.map((e) => e.gunw_granule_id));
	});

	it('flags only steep ground moving beyond k times the reference scatter, largest first', () => {
		const t = slopes.thresholds;
		const limit = t.sigma_k * slopes.uncertainty.rate_sigma_cm_yr;
		for (const c of slopes.candidates) {
			expect(c.slope_deg).toBeGreaterThanOrEqual(t.slope_min_deg - 5); // patch median; edge pixels pass individually
			expect(Math.abs(c.rate_cm_yr)).toBeGreaterThan(limit * 0.9);
			expect(c.direction).toBe(c.rate_cm_yr > 0 ? 'toward' : 'away');
			expect(c.series_cm).toHaveLength(slopes.epochs.length);
		}
		const areas = slopes.candidates.map((c) => c.area_m2);
		expect(areas).toEqual([...areas].sort((a, b) => b - a));
		const ids = new Set(slopes.geojson.features.map((f) => f.properties?.patch_id));
		expect(ids).toEqual(new Set(slopes.candidates.map((c) => c.candidate_id)));
		expect(slopeLabel(slopes.candidates[0] ?? { candidate_id: 's-1' })).toBe('Moving slope 1');
	});
});

describe('scenario records', () => {
	it('are all real NISAR data with one metrics row per epoch', () => {
		for (const s of SCENARIOS) {
			expect(s.data_status).toBe('REAL');
			expect(s.metrics).toHaveLength(s.epochs.length);
		}
	});
});
