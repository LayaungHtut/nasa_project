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

	it('labels every step with the true data status of the screen it shows', () => {
		for (const step of TOUR_STEPS) {
			const s = SCENARIOS.find((x) => x.id === step.scenarioId)!;
			expect(step.dataStatus, step.title).toBe(s.data_status);
			if (s.data_status === 'SIMULATED')
				expect(step.headline + step.description).toMatch(/simulated/i);
		}
	});

	it('starts with the real data and never calls the change mining or illegal', () => {
		expect(TOUR_STEPS[1].dataStatus).toBe('REAL');
		const real = TOUR_STEPS.filter((t) => t.dataStatus === 'REAL').map(
			(t) => t.headline + t.description
		);
		for (const text of real) expect(text).not.toMatch(/\billegal\b|mining detected/i);
	});
});
