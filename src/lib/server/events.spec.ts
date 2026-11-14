import { describe, expect, it } from 'vitest';
import { getAuthoritativeEvent } from './events';
import { CURATED_EVENTS } from '$lib/data/fixtures';
import {
	explainObservation,
	observationTimeline,
	formatAcquisitionDate
} from '$lib/data/presentation';
import metadata from '../../../data/processed/yangon-track40-frame10/metadata.json';
import statistics from '../../../data/processed/yangon-track40-frame10/statistics.json';
import comparison from '../../../data/validation/yangon-track40-frame10/comparison.json';
import { independentValidation } from '$lib/data/validation';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { gunzipSync } from 'node:zlib';

describe('Observation provenance across presentation layers', () => {
	it('keeps acquisition dates in UTC and labels non-observational scenes explicitly', () => {
		expect(formatAcquisitionDate('2026-09-08T23:02:39Z')).toBe('Sep 8, 2026');
		expect(formatAcquisitionDate('SYNTHETIC-NO-REAL-ACQUISITION')).toBe('Synthetic scene');
	});
	it('serves pipeline metrics unchanged and derives both timeline scenes from their sources', async () => {
		const event = await getAuthoritativeEvent(metadata.id);
		expect(event?.results).toEqual(metadata.results);
		expect(event?.statistics).toEqual(statistics);
		expect(event?.observation_dates.all_observations?.map((scene) => scene.granule_id)).toEqual(
			metadata.source_products.map((source) => source.granule_id)
		);
		expect(event?.observation_dates.all_observations?.map((scene) => scene.phase)).toEqual([
			'baseline',
			'repeat'
		]);
	});

	it('keeps offline and server narratives consistent without duplicating the real event', async () => {
		const matching = CURATED_EVENTS.filter((event) => event.id === metadata.id);
		const served = await getAuthoritativeEvent(metadata.id);
		expect(matching).toHaveLength(1);
		expect(matching[0].curated_story).toEqual(served?.curated_story);
		expect(matching[0].ai_explanation).toEqual(served?.ai_explanation);
	});

	it('updates narrated numbers when the underlying record changes and retains uncertainty', () => {
		const event = structuredClone(CURATED_EVENTS[0]);
		event.results.change_area_km2 = 0.125;
		event.results.confidence = 0.512;
		const explanation = explainObservation(event);
		expect(explanation).toContain('0.125 km²');
		expect(explanation).toContain('0.512');
		expect(explanation).not.toContain('0.056');
		expect(explanation).toContain('unconfirmed');
		expect(explanation).toContain('not a probability');
		expect(explanation).toContain(`${statistics.water_loss_area_km2} km²`);
	});

	it('does not invent acquisition dates for an undated synthetic scene', () => {
		const event = structuredClone(CURATED_EVENTS[0]);
		event.observation_dates.baseline = 'SYNTHETIC-NO-REAL-ACQUISITION';
		event.observation_dates.post_event = 'SYNTHETIC-NO-REAL-ACQUISITION';
		expect(observationTimeline(event)).toEqual([]);
	});

	it('keeps the audit tied to the archived mask, geometry and unmodified pipeline result', async () => {
		const event = await getAuthoritativeEvent(metadata.id);
		const hash = (data: Uint8Array) => createHash('sha256').update(data).digest('hex');
		expect(
			hash(gunzipSync(readFileSync('data/validation/yangon-track40-frame10/candidate-mask.npy.gz')))
		).toBe(comparison.candidate_mask_sha256);
		expect(
			hash(
				Buffer.from(
					JSON.stringify(
						JSON.parse(readFileSync('data/processed/yangon-track40-frame10/change.geojson', 'utf8'))
					)
				)
			)
		).toBe(comparison.candidate_geometry_sha256);
		expect(event?.results).toEqual(comparison.results_snapshot);
		expect(event?.independent_validation?.primary_joint_clear_pixels).toBe(0);
		expect(event?.independent_validation?.exploratory.joint_clear_pixels).toBe(110);
		expect(event?.independent_validation?.status).toBe('unconfirmed');
		expect(CURATED_EVENTS.find((item) => item.id === metadata.id)?.independent_validation).toEqual(
			event?.independent_validation
		);
	});

	it('does not attach an old audit to different processing, dates, or synthetic data', () => {
		const original = CURATED_EVENTS.find((event) => event.id === metadata.id)!;
		const changed = structuredClone(original);
		changed.processing.threshold_db = -12;
		expect(independentValidation(changed)).toBeUndefined();
		const redated = structuredClone(original);
		redated.observation_dates.post_event = '2026-09-20T23:02:39Z';
		expect(independentValidation(redated)).toBeUndefined();
		expect(
			independentValidation({ ...original, data_status: 'SYNTHETIC_PLACEHOLDER' })
		).toBeUndefined();
	});
});
