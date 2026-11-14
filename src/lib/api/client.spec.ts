import { describe, it, expect } from 'vitest';
import { api } from './client';
import realGeometry from '../../../data/processed/yangon-track40-frame10/change.geojson?raw';

describe('Resilient API Client', () => {
	it('should return curated events catalog with fallback', async () => {
		const events = await api.getEvents();
		expect(events.length).toBeGreaterThanOrEqual(3);
		expect(events[0].id).toBe('yangon-track40-frame10');
		expect(events[0].data_status).toBe('REAL');
	});

	it('should fetch single event details correctly for yangon-track40-frame10', async () => {
		const event = await api.getEvent('yangon-track40-frame10');
		expect(event.id).toBe('yangon-track40-frame10');
		expect(event.data_status).toBe('REAL');
		expect(event.location.country).toBe('Myanmar');
		expect(event.results.change_area_km2).toBe(0.056);
		expect(event.results.confidence).toBe(0.639);
	});

	it('should fetch single event details correctly for demo-yangon-fixture', async () => {
		const event = await api.getEvent('demo-yangon-fixture');
		expect(event.id).toBe('demo-yangon-fixture');
		expect(event.data_status).toBe('SYNTHETIC_PLACEHOLDER');
		expect(event.location.country).toBe('Myanmar');
		expect(event.results.change_area_km2).toBe(1.528);
	});

	it('should fetch event geometry correctly for yangon-track40-frame10', async () => {
		const geojson = await api.getGeometry('yangon-track40-frame10');
		expect(geojson).toEqual(JSON.parse(realGeometry));
	});

	it('does not substitute another event geometry for an unknown identifier', async () => {
		await expect(api.getGeometry('missing-event')).rejects.toThrow('Geometry unavailable');
	});

	it('should generate verified grounded explanation for real event', async () => {
		const explanation = await api.explainEvent('yangon-track40-frame10');
		expect(explanation.ai_explanation).toContain('0.056');
		expect(explanation.verification.cites_exact_area).toBe(true);
		expect(explanation.verification.grounded_numbers.area_km2).toBe(0.056);
	});

	it('should generate verified grounded explanation for synthetic fixture', async () => {
		const explanation = await api.explainEvent('demo-yangon-fixture');
		expect(explanation.ai_explanation).toContain('1.528');
		expect(explanation.verification.cites_exact_area).toBe(true);
		expect(explanation.verification.grounded_numbers.area_km2).toBe(1.528);
	});
});
