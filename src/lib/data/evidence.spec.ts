import { describe, expect, it } from 'vitest';
import { opticalEvidence, timeGap } from './evidence';
import { CURATED_EVENTS } from './fixtures';

describe('Optical evidence provenance', () => {
	it('excludes unrelated events and changed processing', () => {
		const event = CURATED_EVENTS.find((item) => item.id === 'yangon-track40-frame10')!;
		expect(opticalEvidence(event)?.candidates).toHaveLength(46);
		expect(
			opticalEvidence({ ...event, processing: { ...event.processing, threshold_db: -12 } })
		).toBeUndefined();
		expect(opticalEvidence({ ...event, id: 'other-event' })).toBeUndefined();
	});
	it('reports signed timing relative to the chosen radar date', () => {
		const event = CURATED_EVENTS.find((item) => item.id === 'yangon-track40-frame10')!;
		const evidence = opticalEvidence(event)!;
		const sameDay = evidence.scenes.find((scene) => scene.datetime.startsWith('2026-09-08'))!;
		expect(timeGap(sameDay, 'repeat')).toBe('0.78 days before radar');
		expect(timeGap(sameDay, 'baseline')).toBe('11.22 days after radar');
		const supported = evidence.candidates.find((candidate) => candidate.component === 41)!;
		expect(supported.land_to_water_pixels).toBe(9);
		expect(supported.area_m2).toBe(900);
		expect(supported.references.find((ref) => ref.scene_id === sameDay.id)?.water_pixels).toBe(0);
	});
});
