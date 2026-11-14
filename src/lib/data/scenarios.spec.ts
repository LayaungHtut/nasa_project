import { describe, expect, it } from 'vitest';
import { SCENARIOS, compliance, forensics, observedStatus } from './scenarios';
import type { LandslideScenario, MiningScenario, ObservedScenario } from '$lib/types/scenario';

const mining = SCENARIOS.find((s) => s.module === 'mining') as MiningScenario;
const landslide = SCENARIOS.find((s) => s.module === 'landslide') as LandslideScenario;
const observed = SCENARIOS.find((s) => s.module === 'observed') as ObservedScenario;

describe('real Hpakant observations', () => {
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

describe('mining compliance', () => {
	it('moves from compliant to watch to breach as digging crosses the permit', () => {
		const levels = mining.epochs.map((_, i) => compliance(mining, i).level);
		expect(levels).toEqual(['compliant', 'compliant', 'watch', 'breach', 'breach']);
		expect(compliance(mining, 0).firstBreach).toBe(3);
	});

	it('explains a breach with measured numbers', () => {
		const c = compliance(mining, 4);
		expect(c.reasons.length).toBeGreaterThanOrEqual(2);
		expect(c.reasons[0]).toContain(`${mining.metrics[4].max_distance_outside_m} m beyond`);
		expect(c.reasons.join(' ')).not.toMatch(/NaN|undefined/);
	});
});

describe('landslide forensics', () => {
	it('watches, then warns at the slide, then links the diversion to it', () => {
		const stages = landslide.epochs.map((_, i) => forensics(landslide, i).stage);
		expect(stages).toEqual(['monitoring', 'monitoring', 'early_warning', 'linked']);
		const f = forensics(landslide, 3);
		expect(f.lagDays).toBe(12);
		expect(f.evidence.every((e) => !/NaN|undefined/.test(e.text))).toBe(true);
		expect(f.alternatives.find((a) => a.title.startsWith('Monsoon'))?.verdict).toBe('Ruled out');
	});

	it('refuses to link a slide that is downstream of the shift or too far away', () => {
		const downstream = {
			...landslide,
			linkage: { ...landslide.linkage, slide_is_upstream: false }
		};
		expect(forensics(downstream, 3).stage).toBe('unexplained');
		const far = { ...landslide, linkage: { ...landslide.linkage, river_distance_km: 50 } };
		expect(forensics(far, 3).stage).toBe('unexplained');
	});
});

describe('scenario records', () => {
	it('label the demos simulated and have one image per pass', () => {
		for (const s of SCENARIOS) {
			expect(s.data_status).toBe(s.module === 'observed' ? 'REAL' : 'SIMULATED');
			expect(s.metrics).toHaveLength(s.epochs.length);
			if (s.module !== 'observed') expect(s.epochs[0].coherence_url).toBeNull();
		}
	});
});
