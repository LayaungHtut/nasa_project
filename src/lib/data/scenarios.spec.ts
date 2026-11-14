import { describe, expect, it } from 'vitest';
import { SCENARIOS, compliance, forensics } from './scenarios';
import type { LandslideScenario, MiningScenario } from '$lib/types/scenario';

const mining = SCENARIOS.find((s) => s.module === 'mining') as MiningScenario;
const landslide = SCENARIOS.find((s) => s.module === 'landslide') as LandslideScenario;

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
	it('are all labelled simulated and have one image per pass', () => {
		for (const s of SCENARIOS) {
			expect(s.data_status).toBe('SIMULATED');
			expect(s.metrics).toHaveLength(s.epochs.length);
			expect(s.epochs[0].coherence_url).toBeNull();
		}
	});
});
