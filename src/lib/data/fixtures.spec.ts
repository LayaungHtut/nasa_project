import { describe, it, expect } from 'vitest';
import {
	CURATED_EVENTS,
	YANGON_FIXTURE_GEOJSON,
	BAGO_FLOOD_GEOJSON,
	DELTA_GEOJSON,
	SAGAING_GEOJSON
} from './fixtures';

describe('Curated NISAR Scientific Fixtures', () => {
	it('should contain synthetic fixtures honestly tagged as SYNTHETIC_PLACEHOLDER', () => {
		const demoEvent = CURATED_EVENTS.find((e) => e.id === 'demo-yangon-fixture');
		expect(demoEvent).toBeDefined();
		if (!demoEvent) return;

		expect(demoEvent.data_status).toBe('SYNTHETIC_PLACEHOLDER');
		expect(demoEvent.phenomenon).toBe('flood_extent_change');
		expect(demoEvent.results.change_area_km2).toBe(1.528);
		expect(demoEvent.results.confidence).toBe(1.0);
		expect(demoEvent.processing.threshold_db).toBe(-17.0);
		expect(demoEvent.source_products.length).toBe(2);
		expect(demoEvent.source_products[0].mission).toBe('NISAR');
		expect(demoEvent.source_products[0].track).toBe(40);
		expect(demoEvent.source_products[0].granule_id).toContain('NISAR_L2_PR_GCOV');
	});

	it('should contain the Bago Flood event with valid coordinates and metrics', () => {
		const bago = CURATED_EVENTS.find((e) => e.id === 'bago-flood-2026');
		expect(bago).toBeDefined();
		if (!bago) return;

		expect(bago.data_status).toBe('SYNTHETIC_PLACEHOLDER');
		expect(bago.phenomenon).toBe('flood_extent_change');
		expect(bago.results.change_area_km2).toBe(42.7);
		expect(bago.results.confidence).toBeGreaterThan(0.7);
		expect(bago.results.confidence).toBeLessThanOrEqual(1.0);
		expect(bago.source_products.length).toBeGreaterThanOrEqual(2);
		expect(bago.source_products[0].mission).toBe('NISAR');
		expect(bago.source_products[0].product).toBe('GCOV');
		expect(bago.processing.method).toBe('backscatter_threshold_change_detection_v1');
		expect(bago.processing.limitations.length).toBeGreaterThanOrEqual(3);
	});

	it('should provide valid GeoJSON polygons for all collections', () => {
		expect(YANGON_FIXTURE_GEOJSON.type).toBe('FeatureCollection');
		expect(YANGON_FIXTURE_GEOJSON.features.length).toBeGreaterThan(0);

		expect(BAGO_FLOOD_GEOJSON.type).toBe('FeatureCollection');
		expect(BAGO_FLOOD_GEOJSON.features.length).toBeGreaterThanOrEqual(2);

		const permWater = BAGO_FLOOD_GEOJSON.features.find(
			(f) => f.properties.class === 'permanent_water'
		);
		const inundation = BAGO_FLOOD_GEOJSON.features.find(
			(f) => f.properties.class === 'new_inundation'
		);
		expect(permWater).toBeDefined();
		expect(inundation).toBeDefined();

		expect(DELTA_GEOJSON.type).toBe('FeatureCollection');
		expect(DELTA_GEOJSON.features.length).toBeGreaterThan(0);

		expect(SAGAING_GEOJSON.type).toBe('FeatureCollection');
		expect(SAGAING_GEOJSON.features.length).toBeGreaterThan(0);
	});

	it('should have grounded explanations referencing quantitative results', () => {
		for (const evt of CURATED_EVENTS) {
			expect(evt.ai_explanation).toBeTruthy();
			expect(evt.ai_explanation).toContain(evt.results.change_area_km2.toString());
		}
	});
});
