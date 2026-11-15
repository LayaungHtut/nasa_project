import fs from 'node:fs';
import path from 'node:path';
import { presentEvent } from '$lib/data/presentation';
import type { ChangeEvent, PipelineStatistics, GeoJsonFeatureCollection } from '$lib/types/api';

const REPO_ROOT = process.cwd();
const FIXTURES_PATH = path.resolve(REPO_ROOT, 'data', 'fixtures', 'events.json');
const PROCESSED_DIR = path.resolve(REPO_ROOT, 'data', 'processed');

/**
 * Loads all authoritative ChangeEvents.
 * Implements ONE SOURCE OF TRUTH:
 * 1. Base events loaded from data/fixtures/events.json.
 * 2. Overridden and populated with real pipeline outputs from data/processed/<id>/metadata.json and statistics.json.
 * 3. Enriched with presentation storytelling without mutating scientific statistics.
 */
export async function getAuthoritativeEvents(): Promise<ChangeEvent[]> {
	const eventsMap = new Map<string, ChangeEvent>();

	// 1. Load baseline catalog fixtures from data/fixtures/events.json
	if (fs.existsSync(FIXTURES_PATH)) {
		try {
			const fixtureContent = JSON.parse(fs.readFileSync(FIXTURES_PATH, 'utf-8'));
			if (Array.isArray(fixtureContent.events)) {
				for (const evt of fixtureContent.events) {
					eventsMap.set(evt.id, evt as ChangeEvent);
				}
			}
		} catch (err) {
			console.error('Failed to read data/fixtures/events.json:', err);
		}
	}

	// 2. Scan data/processed/*/metadata.json for authoritative pipeline runs
	if (fs.existsSync(PROCESSED_DIR)) {
		try {
			const entries = fs.readdirSync(PROCESSED_DIR, { withFileTypes: true });
			for (const entry of entries) {
				if (entry.isDirectory()) {
					const eventId = entry.name;
					const metadataPath = path.resolve(PROCESSED_DIR, eventId, 'metadata.json');
					const statsPath = path.resolve(PROCESSED_DIR, eventId, 'statistics.json');

					if (fs.existsSync(metadataPath)) {
						try {
							const metadataRaw = JSON.parse(fs.readFileSync(metadataPath, 'utf-8'));
							const existing = eventsMap.get(eventId);

							// Normalize location fields
							const loc = metadataRaw.location || {};
							const center = loc.center || existing?.location?.center || [0, 0];
							const bbox = loc.bbox || existing?.location?.bbox || [0, 0, 0, 0];
							const normalizedLocation = {
								...existing?.location,
								...loc,
								name: loc.name || existing?.location?.name || eventId,
								country: loc.country || existing?.location?.country || 'Myanmar',
								region: loc.region || existing?.location?.region || 'Yangon Region',
								coordinates: loc.coordinates || [center[0], center[1]],
								center: center,
								bbox: bbox,
								zoom: existing?.location?.zoom || 12
							};

							const metadata: ChangeEvent = {
								...existing,
								...metadataRaw,
								location: normalizedLocation
							};

							// Attach statistics.json if present
							if (fs.existsSync(statsPath)) {
								try {
									const stats = JSON.parse(
										fs.readFileSync(statsPath, 'utf-8')
									) as PipelineStatistics;
									metadata.statistics = stats;
								} catch (statsErr) {
									console.warn(`Could not read statistics.json for ${eventId}:`, statsErr);
								}
							}

							eventsMap.set(eventId, metadata);
						} catch (metaErr) {
							console.error(`Failed to parse metadata.json for ${eventId}:`, metaErr);
						}
					}
				}
			}
		} catch (dirErr) {
			console.error('Failed to read data/processed directory:', dirErr);
		}
	}

	// 3. Attach curated presentation metadata (storylines, subtitles)
	const events: ChangeEvent[] = [];
	for (const evt of eventsMap.values()) {
		const enriched = presentEvent({
			...evt,
			subtitle: evt.subtitle ?? `${evt.title} (${evt.data_status})`,
			summary: evt.summary ?? evt.title
		});
		events.push(enriched);
	}

	// Real observations first, synthetic scenarios after
	events.sort((a, b) => {
		if (a.data_status === 'REAL' && b.data_status !== 'REAL') return -1;
		if (b.data_status === 'REAL' && a.data_status !== 'REAL') return 1;
		return 0;
	});

	return events;
}

/**
 * Retrieves a single authoritative ChangeEvent by ID.
 */
export async function getAuthoritativeEvent(id: string): Promise<ChangeEvent | null> {
	const events = await getAuthoritativeEvents();
	return events.find((e) => e.id === id) ?? null;
}

/**
 * Retrieves authoritative GeoJSON polygons for an event directly from data/processed/<id>/change.geojson.
 */
export async function getAuthoritativeGeometry(
	id: string
): Promise<GeoJsonFeatureCollection | null> {
	const geojsonPath = path.resolve(PROCESSED_DIR, id, 'change.geojson');
	if (fs.existsSync(geojsonPath)) {
		try {
			return JSON.parse(fs.readFileSync(geojsonPath, 'utf-8')) as GeoJsonFeatureCollection;
		} catch (err) {
			console.error(`Failed to read GeoJSON for ${id}:`, err);
		}
	}
	return null;
}
