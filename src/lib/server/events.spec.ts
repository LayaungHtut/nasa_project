import { describe, expect, it } from 'vitest';
import { getAuthoritativeEvent } from './events';
import { CURATED_EVENTS } from '$lib/data/fixtures';
import {
	explainObservation,
	observationTimeline,
	formatAcquisitionDate
} from '$lib/data/presentation';
import metadata from '../../../data/processed/demo-yangon-fixture/metadata.json';

describe('Observation provenance across presentation layers', () => {
	it('keeps acquisition dates in UTC and labels non-observational scenes explicitly', () => {
		expect(formatAcquisitionDate('2026-09-08T23:02:39Z')).toBe('Sep 8, 2026');
		expect(formatAcquisitionDate('SYNTHETIC-NO-REAL-ACQUISITION')).toBe('Synthetic scene');
	});
	it('serves pipeline metrics unchanged and does not invent dates for a synthetic run', async () => {
		const event = await getAuthoritativeEvent(metadata.id);
		expect(event?.results).toEqual(metadata.results);
		expect(event?.data_status).toBe('SYNTHETIC_PLACEHOLDER');
		expect(event?.observation_dates.all_observations).toEqual([]);
	});

	it('updates narrated numbers when the underlying record changes and retains uncertainty', () => {
		const event = structuredClone(CURATED_EVENTS[0]);
		const originalArea = event.results.change_area_km2;
		event.results.change_area_km2 = 0.125;
		event.results.confidence = 0.512;
		const explanation = explainObservation(event);
		expect(explanation).toContain('0.125 km²');
		expect(explanation).toContain('0.512');
		expect(explanation).not.toContain(`${originalArea} km²`);
		expect(explanation).toContain('unconfirmed');
		expect(explanation).toContain('not a probability');
	});

	it('does not invent acquisition dates for an undated synthetic scene', () => {
		const event = structuredClone(CURATED_EVENTS[0]);
		event.observation_dates.baseline = 'SYNTHETIC-NO-REAL-ACQUISITION';
		event.observation_dates.post_event = 'SYNTHETIC-NO-REAL-ACQUISITION';
		expect(observationTimeline(event)).toEqual([]);
	});
});
