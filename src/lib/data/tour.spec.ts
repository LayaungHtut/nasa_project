import { describe, expect, it } from 'vitest';
import { SCENARIOS } from './scenarios';
import { TOUR_STEPS } from './tour';

describe('judge tour', () => {
	it('every step points at a real scenario pass and has no missing numbers', () => {
		for (const step of TOUR_STEPS) {
			const s = SCENARIOS.find((x) => x.id === step.scenarioId);
			expect(s, step.title).toBeDefined();
			expect(s!.epochs[step.epochIndex], step.title).toBeDefined();
			expect(`${step.headline} ${step.description}`, step.title).not.toMatch(
				/undefined|NaN|null|Day -1\b/
			);
		}
	});

	it('shows only real data and never calls it simulated or a demo', () => {
		for (const step of TOUR_STEPS) {
			const s = SCENARIOS.find((x) => x.id === step.scenarioId)!;
			expect(step.dataStatus, step.title).toBe(s.data_status);
			expect(s.data_status).toBe('REAL');
			expect(step.headline + step.description, step.title).not.toMatch(/simulated|\bdemo\b/i);
		}
	});

	it('never calls the change mining or illegal, or a moving slope a detected landslide', () => {
		for (const t of TOUR_STEPS)
			expect(t.headline + t.description).not.toMatch(
				/\billegal\b|mining detected|landslide detected/i
			);
	});
});
