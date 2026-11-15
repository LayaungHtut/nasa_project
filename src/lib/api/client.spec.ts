import { describe, it, expect } from 'vitest';
import { api } from './client';
import { YANGON_FIXTURE_GEOJSON } from '$lib/data/fixtures';

describe('Resilient API Client', () => {
	it('should return curated events catalog with fallback', async () => {
		const events = await api.getEvents();
		expect(events.length).toBeGreaterThanOrEqual(3);
		expect(events[0].id).toBe('demo-yangon-fixture');
	});

	it('should fetch single event details correctly for demo-yangon-fixture', async () => {
		const event = await api.getEvent('demo-yangon-fixture');
		expect(event.id).toBe('demo-yangon-fixture');
		expect(event.data_status).toBe('SYNTHETIC_PLACEHOLDER');
		expect(event.location.country).toBe('Myanmar');
		expect(event.results.change_area_km2).toBe(1.528);
	});

	it('should fetch event geometry correctly for demo-yangon-fixture', async () => {
		const geojson = await api.getGeometry('demo-yangon-fixture');
		expect(geojson).toEqual(YANGON_FIXTURE_GEOJSON);
	});

	it('does not substitute another event geometry for an unknown identifier', async () => {
		await expect(api.getGeometry('missing-event')).rejects.toThrow('Geometry unavailable');
	});

	it('should generate verified grounded explanation for synthetic fixture', async () => {
		const explanation = await api.explainEvent('demo-yangon-fixture');
		expect(explanation.ai_explanation).toContain('1.528');
		expect(explanation.verification.cites_exact_area).toBe(true);
		expect(explanation.verification.grounded_numbers.area_km2).toBe(1.528);
	});
});
