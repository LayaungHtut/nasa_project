<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import {
		Map as MapLibreMap,
		NavigationControl,
		ScaleControl,
		AttributionControl,
		setWorkerUrl,
		type StyleSpecification,
		type MapLayerMouseEvent,
		type ImageSource
	} from 'maplibre-gl';
	import mapWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
	import { appState } from '$lib/stores/appState.svelte';
	import { api } from '$lib/api/client';
	import { resolve } from '$app/paths';
	import type { OpticalEvidence } from '$lib/types/evidence';
	import ComparisonSlider from './ComparisonSlider.svelte';
	import PeriodPanel from './PeriodPanel.svelte';
	import MapLegend from './MapLegend.svelte';
	import LayerControls from './LayerControls.svelte';
	import { Loader2, AlertCircle } from 'lucide-svelte';

	let mapContainer = $state<HTMLDivElement | null>(null);
	let comparisonContainer = $state<HTMLDivElement | null>(null);
	let map = $state<MapLibreMap | null>(null);
	let comparisonMap = $state<MapLibreMap | null>(null);
	let layerRequest = 0;
	let isLoadingLayers = $state(false);
	let isMapLoaded = $state<boolean>(false);
	let opticalLoading = $state(false);
	let opticalError = $state(false);
	let opticalRequest = 0;
	let layersEventId = $state<string | null>(null);
	let hoveredFeature = $state<{
		name: string;
		class: string;
		area_km2?: number;
		backscatter_db?: number;
		confidence?: number;
	} | null>(null);

	let basemapUnavailable = $state(false);
	const FALLBACK_STYLE: StyleSpecification = {
		version: 8,
		sources: {},
		layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#07173f' } }]
	};

	onMount(() => {
		if (!mapContainer || !comparisonContainer) return;
		// Vite must emit the v6 worker as an asset; its default relative URL breaks
		// once the main library is bundled into a SvelteKit route chunk.
		setWorkerUrl(mapWorkerUrl);
		let primary: MapLibreMap | undefined;
		let secondary: MapLibreMap | undefined;
		let resizeObserver: ResizeObserver | undefined;
		appState.mapError = null;
		let cancelled = false;

		try {
			const initialCenter = appState.selectedEvent.location.center;
			const initialZoom = appState.selectedEvent.location.zoom;

			const m = new MapLibreMap({
				container: mapContainer,
				style: FALLBACK_STYLE,
				center: initialCenter,
				zoom: initialZoom,
				minZoom: 3,
				maxZoom: 17,
				attributionControl: false
			});
			primary = m;
			const comparison = new MapLibreMap({
				container: comparisonContainer,
				style: FALLBACK_STYLE,
				center: initialCenter,
				zoom: initialZoom,
				interactive: false,
				attributionControl: false
			});
			secondary = comparison;
			comparison.getCanvas().removeAttribute('tabindex');
			const syncCamera = () =>
				comparison.jumpTo({
					center: m.getCenter(),
					zoom: m.getZoom(),
					bearing: m.getBearing(),
					pitch: m.getPitch()
				});
			m.on('move', syncCamera);
			resizeObserver = new ResizeObserver(() => {
				m.resize();
				comparison.resize();
				syncCamera();
			});
			resizeObserver.observe(mapContainer);
			m.addControl(
				new AttributionControl({
					compact: true,
					customAttribution:
						'NASA/ISRO NISAR · Contains modified Copernicus Sentinel data (2026), via Earth Search'
				}),
				'bottom-right'
			);

			m.addControl(
				new NavigationControl({
					showCompass: true,
					showZoom: true,
					visualizePitch: true
				}),
				'top-right'
			);

			m.addControl(
				new ScaleControl({
					maxWidth: 100,
					unit: 'metric'
				}),
				'bottom-left'
			);

			let readyCount = 0;
			const ready = () => {
				if (++readyCount !== 2) return;
				map = m;
				comparisonMap = comparison;
				isMapLoaded = true;
				// Basemap loading never blocks the locally served science layers.
				void loadBasemap();
			};
			async function loadBasemap() {
				try {
					const response = await fetch('https://tiles.openfreemap.org/styles/dark', {
						signal: AbortSignal.timeout(8000)
					});
					if (!response.ok) throw new Error(`Basemap HTTP ${response.status}`);
					const basemapStyle = (await response.json()) as StyleSpecification;
					if (cancelled) return;
					for (const target of [m, comparison]) {
						target.setStyle(basemapStyle, {
							transformStyle: (previous, next) => ({
								...next,
								sources: { ...next.sources, ...previous?.sources },
								layers: [
									...next.layers,
									...(previous?.layers.filter((layer) => layer.id !== 'background') ?? [])
								]
							})
						});
					}
				} catch {
					if (!cancelled) basemapUnavailable = true;
				}
			}
			m.once('load', ready);
			comparison.once('load', ready);

			// Hover interactions on change polygons
			m.on('mousemove', 'inundation-fill', (e: MapLayerMouseEvent) => {
				if (e.features && e.features[0]) {
					m.getCanvas().style.cursor = 'pointer';
					const props = e.features[0].properties;
					hoveredFeature = {
						name: String(props.name ?? 'Inundation Feature'),
						class: String(props.class ?? 'new_inundation'),
						area_km2: props.area_km2 ? Number(props.area_km2) : undefined,
						backscatter_db: props.backscatter_db ? Number(props.backscatter_db) : undefined,
						confidence: props.confidence ? Number(props.confidence) : undefined
					};
				}
			});

			m.on('mouseleave', 'inundation-fill', () => {
				m.getCanvas().style.cursor = '';
				hoveredFeature = null;
			});
			m.on('click', (e) => {
				if (
					!['change_mask', 'optical_compare'].includes(appState.activeLayer) ||
					!m.getLayer('evidence-markers')
				)
					return;
				const features = m.queryRenderedFeatures(
					[
						[e.point.x - 6, e.point.y - 6],
						[e.point.x + 6, e.point.y + 6]
					],
					{ layers: ['evidence-markers', 'evidence-fill'] }
				);
				const id = features[0]?.properties.component;
				if (id !== undefined) appState.selectCandidate(Number(id));
			});
			m.on('mouseenter', 'evidence-markers', () => {
				m.getCanvas().style.cursor = 'pointer';
			});
			m.on('mouseleave', 'evidence-markers', () => {
				m.getCanvas().style.cursor = '';
			});
		} catch (err) {
			console.error('Failed to initialize MapLibre:', err);
			appState.mapError = 'WebGL map initialization failed.';
		}
		return () => {
			cancelled = true;
			layerRequest++;
			opticalRequest++;
			resizeObserver?.disconnect();
			secondary?.remove();
			primary?.remove();
			map = null;
			comparisonMap = null;
		};
	});

	// React to event changes (fly to new coordinates & reload GeoJSON)
	$effect(() => {
		const evt = appState.selectedEvent;
		if (map && isMapLoaded && evt) {
			map.flyTo({
				center: evt.location.center,
				zoom: evt.location.zoom,
				duration: 1800,
				essential: false
			});
			untrack(() => {
				void setupEventLayers().catch(() => {
					appState.mapError = 'Observation layers could not be loaded. Please reload to try again.';
				});
			});
		}
	});

	/** HV is only offered for the plain observation views; analysis layers sit on HH. */
	let channel = $derived(
		['compare', 'baseline', 'post'].includes(appState.activeLayer) ? appState.polarization : 'HH'
	);

	function observationUrls(event: typeof appState.selectedEvent, pol: 'HH' | 'HV') {
		const tiles = event.tiles;
		const hv = pol === 'HV' ? event.polarimetry?.layers : undefined;
		return {
			baseline: hv?.baseline_hv_url ?? tiles.baseline_preview_url ?? tiles.preview_url,
			post: hv?.post_event_hv_url ?? tiles.post_event_preview_url ?? tiles.preview_url
		};
	}

	// Swap the observation images in place when the channel changes
	$effect(() => {
		const pol = channel;
		if (!map || !comparisonMap || !isMapLoaded) return;
		const event = untrack(() => appState.selectedEvent);
		const coordinates =
			untrack(() => appState.opticalEvidence)?.corner_coordinates ??
			event.tiles?.corner_coordinates;
		if (!coordinates) return;
		const urls = observationUrls(event, pol);
		const targets: Array<[MapLibreMap, string, string | undefined]> = [
			[map, 'radar-baseline', urls.baseline],
			[map, 'radar-post', urls.post],
			[comparisonMap, 'comparison-post', urls.post]
		];
		for (const [target, id, url] of targets) {
			const source = target.getSource(id) as ImageSource | undefined;
			if (source && url && source.url !== url) source.updateImage({ url, coordinates });
		}
	});

	// Loading a dated optical image is independent of the radar layers. Cancel stale
	// loads so quick date/event switches cannot show the wrong image under a label.
	$effect(() => {
		const scene = appState.opticalScene;
		const evidence = appState.opticalEvidence;
		const enabled = appState.activeLayer === 'optical_compare';
		const target = comparisonMap;
		if (
			!target ||
			!isMapLoaded ||
			!scene ||
			!evidence ||
			!enabled ||
			layersEventId !== evidence.event_id
		)
			return;
		const request = ++opticalRequest;
		opticalLoading = true;
		opticalError = false;
		if (target.getLayer('comparison-optical-layer'))
			target.setLayoutProperty('comparison-optical-layer', 'visibility', 'none');
		const controller = new AbortController();
		let objectUrl: string | undefined;
		void (async () => {
			try {
				const response = await fetch(resolve('/data/[...path]', { path: scene.image_path }), {
					signal: controller.signal
				});
				if (!response.ok) throw new Error('Optical preview unavailable');
				const blob = await response.blob();
				objectUrl = URL.createObjectURL(blob);
				const image = new Image();
				image.src = objectUrl;
				await image.decode();
				if (request !== opticalRequest || controller.signal.aborted) return;
				// Use the decoded image to avoid a second network request inside MapLibre.
				if (target.getLayer('comparison-optical-layer'))
					target.removeLayer('comparison-optical-layer');
				if (target.getSource('comparison-optical')) target.removeSource('comparison-optical');
				target.addSource('comparison-optical', {
					type: 'image',
					coordinates: evidence.corner_coordinates
				});
				(target.getSource('comparison-optical') as ImageSource).updateImage({ image });
				target.addLayer(
					{
						id: 'comparison-optical-layer',
						type: 'raster',
						source: 'comparison-optical',
						paint: { 'raster-opacity': 1, 'raster-fade-duration': 0 }
					},
					target.getLayer('evidence-fill') ? 'evidence-fill' : undefined
				);
				opticalLoading = false;
				updateLayerVisibility();
			} catch {
				if (request === opticalRequest && !controller.signal.aborted) {
					opticalError = true;
					opticalLoading = false;
				}
			} finally {
				if (objectUrl) URL.revokeObjectURL(objectUrl);
			}
		})();
		return () => {
			controller.abort();
			if (objectUrl) URL.revokeObjectURL(objectUrl);
		};
	});

	$effect(() => {
		const focus = appState.candidateFocusRequest;
		if (!focus || !map || !isMapLoaded) return;
		const candidate = untrack(() => appState.selectedCandidate);
		if (candidate) map.flyTo({ center: candidate.centroid_lon_lat, zoom: 16.5, duration: 600 });
	});

	// Swap the time-series frame in place when the selected date changes
	$effect(() => {
		const url = appState.selectedEvent.timeseries?.dates[appState.seriesIndex]?.frame_url;
		if (!map || !isMapLoaded || !url) return;
		const source = map.getSource('radar-series') as ImageSource | undefined;
		const coordinates = untrack(
			() =>
				appState.opticalEvidence?.corner_coordinates ??
				appState.selectedEvent.tiles?.corner_coordinates
		);
		if (source && coordinates && source.url !== url) source.updateImage({ url, coordinates });
	});

	// Swap the two period images in place when the chosen passes change
	$effect(() => {
		const range = appState.periodRange;
		const dates = appState.selectedEvent.timeseries?.dates;
		if (!map || !comparisonMap || !isMapLoaded || !range || !dates) return;
		const coordinates = untrack(
			() =>
				appState.opticalEvidence?.corner_coordinates ??
				appState.selectedEvent.tiles?.corner_coordinates
		);
		if (!coordinates) return;
		const targets: Array<[MapLibreMap, string, string]> = [
			[map, 'radar-period-from', dates[range.from].frame_url],
			[comparisonMap, 'comparison-period-to', dates[range.to].frame_url]
		];
		for (const [target, id, url] of targets) {
			const source = target.getSource(id) as ImageSource | undefined;
			if (source && source.url !== url) source.updateImage({ url, coordinates });
		}
	});

	// React to layer toggles & opacity
	$effect(() => {
		if (!map || !isMapLoaded) return;
		updateLayerVisibility();
	});

	async function setupEventLayers() {
		if (!map || !isMapLoaded) return;

		const event = appState.selectedEvent;
		const request = ++layerRequest;
		layersEventId = null;
		isLoadingLayers = true;
		let geojson;
		try {
			geojson = await api.getGeometry(event.id);
		} finally {
			if (request === layerRequest) isLoadingLayers = false;
		}
		if (
			request !== layerRequest ||
			!map ||
			!comparisonMap ||
			event.id !== appState.selectedEvent.id
		)
			return;
		hoveredFeature = null;
		const evidence = appState.opticalEvidence;
		for (const target of [map, comparisonMap]) {
			for (const id of ['evidence-selected', 'evidence-markers', 'evidence-line', 'evidence-fill'])
				if (target.getLayer(id)) target.removeLayer(id);
			for (const id of ['candidate-evidence', 'candidate-markers'])
				if (target.getSource(id)) target.removeSource(id);
		}
		if (comparisonMap.getLayer('comparison-optical-layer'))
			comparisonMap.removeLayer('comparison-optical-layer');
		if (comparisonMap.getSource('comparison-optical'))
			comparisonMap.removeSource('comparison-optical');
		if (comparisonMap.getLayer('comparison-post-layer'))
			comparisonMap.removeLayer('comparison-post-layer');
		if (comparisonMap.getSource('comparison-post')) comparisonMap.removeSource('comparison-post');
		if (comparisonMap.getLayer('comparison-period-to-layer'))
			comparisonMap.removeLayer('comparison-period-to-layer');
		if (comparisonMap.getSource('comparison-period-to'))
			comparisonMap.removeSource('comparison-period-to');

		// Remove existing custom sources/layers if present
		const layerIds = [
			'inundation-glow',
			'inundation-fill',
			'inundation-line',
			'permanent-water-fill',
			'permanent-water-line',
			'aoi-boundary-line',
			'radar-baseline-layer',
			'radar-post-layer',
			'radar-difference-layer',
			'radar-series-layer',
			'radar-period-from-layer',
			'field-timing-layer',
			'landcover-layer',
			'water-loss-layer'
		];
		layerIds.forEach((id) => {
			if (map?.getLayer(id)) map.removeLayer(id);
		});
		if (map.getSource('event-geometry')) {
			map.removeSource('event-geometry');
		}
		if (map.getSource('event-aoi')) {
			map.removeSource('event-aoi');
		}
		if (map.getSource('radar-baseline')) {
			map.removeSource('radar-baseline');
		}
		if (map.getSource('radar-post')) {
			map.removeSource('radar-post');
		}
		if (map.getSource('radar-difference')) {
			map.removeSource('radar-difference');
		}
		if (map.getSource('radar-series')) {
			map.removeSource('radar-series');
		}
		if (map.getSource('field-timing')) {
			map.removeSource('field-timing');
		}
		if (map.getSource('radar-period-from')) map.removeSource('radar-period-from');
		for (const id of ['landcover', 'water-loss']) if (map.getSource(id)) map.removeSource(id);

		// Add Raster Radar Overlays if corner coordinates exist
		const tiles = event.tiles;
		const imageCoordinates = evidence?.corner_coordinates ?? tiles?.corner_coordinates;
		if (tiles?.corner_coordinates) {
			const { baseline: baselineUrl, post: postUrl } = observationUrls(
				event,
				untrack(() => channel)
			);

			if (baselineUrl) {
				map.addSource('radar-baseline', {
					type: 'image',
					url: baselineUrl,
					coordinates: imageCoordinates!
				});
				map.addLayer({
					id: 'radar-baseline-layer',
					type: 'raster',
					source: 'radar-baseline',
					paint: { 'raster-opacity': appState.opacity }
				});
			}

			if (postUrl) {
				comparisonMap.addSource('comparison-post', {
					type: 'image',
					url: postUrl,
					coordinates: imageCoordinates!
				});
				comparisonMap.addLayer({
					id: 'comparison-post-layer',
					type: 'raster',
					source: 'comparison-post',
					paint: { 'raster-opacity': appState.opacity, 'raster-fade-duration': 0 }
				});
				map.addSource('radar-post', {
					type: 'image',
					url: postUrl,
					coordinates: imageCoordinates!
				});
				map.addLayer({
					id: 'radar-post-layer',
					type: 'raster',
					source: 'radar-post',
					paint: { 'raster-opacity': appState.opacity }
				});
			}

			const differenceUrl = event.polarimetry?.layers.difference_hh_url;
			if (differenceUrl) {
				map.addSource('radar-difference', {
					type: 'image',
					url: differenceUrl,
					coordinates: imageCoordinates!
				});
				map.addLayer({
					id: 'radar-difference-layer',
					type: 'raster',
					source: 'radar-difference',
					layout: { visibility: 'none' },
					paint: { 'raster-opacity': appState.opacity, 'raster-resampling': 'nearest' }
				});
			}

			const seriesFrames = event.timeseries?.dates;
			if (seriesFrames?.length) {
				map.addSource('radar-series', {
					type: 'image',
					url: seriesFrames[untrack(() => appState.seriesIndex)].frame_url,
					coordinates: imageCoordinates!
				});
				map.addLayer({
					id: 'radar-series-layer',
					type: 'raster',
					source: 'radar-series',
					layout: { visibility: 'none' },
					paint: { 'raster-opacity': appState.opacity, 'raster-fade-duration': 0 }
				});
				// Period mode: any two passes, swiped like the two-date comparison
				const range = untrack(() => appState.periodRange);
				if (range) {
					for (const [target, id, url] of [
						[map, 'radar-period-from', seriesFrames[range.from].frame_url],
						[comparisonMap, 'comparison-period-to', seriesFrames[range.to].frame_url]
					] as const) {
						target.addSource(id, { type: 'image', url, coordinates: imageCoordinates! });
						target.addLayer({
							id: `${id}-layer`,
							type: 'raster',
							source: id,
							layout: { visibility: 'none' },
							paint: { 'raster-opacity': appState.opacity, 'raster-fade-duration': 0 }
						});
					}
				}
			}

			// Land cover, with the two-date apparent water loss above it
			const landcover = event.timeseries?.landcover_map;
			if (landcover) {
				for (const [id, url] of [
					['landcover', landcover.map_url],
					['water-loss', landcover.water_loss_url]
				] as const) {
					map.addSource(id, { type: 'image', url, coordinates: imageCoordinates! });
					map.addLayer({
						id: `${id}-layer`,
						type: 'raster',
						source: id,
						layout: { visibility: 'none' },
						paint: { 'raster-opacity': appState.opacity, 'raster-resampling': 'nearest' }
					});
				}
			}

			const timingUrl = event.timeseries?.pixel_season.map_url;
			if (timingUrl) {
				map.addSource('field-timing', {
					type: 'image',
					url: timingUrl,
					coordinates: imageCoordinates!
				});
				map.addLayer({
					id: 'field-timing-layer',
					type: 'raster',
					source: 'field-timing',
					layout: { visibility: 'none' },
					paint: { 'raster-opacity': appState.opacity, 'raster-resampling': 'nearest' }
				});
			}
		}

		// Add AOI Bounding Box GeoJSON
		const bbox = appState.selectedEvent.location.bbox;
		const aoiPolygon = {
			type: 'Feature' as const,
			properties: { name: 'NISAR Observation AOI' },
			geometry: {
				type: 'Polygon' as const,
				coordinates: [
					[
						[bbox[0], bbox[1]],
						[bbox[2], bbox[1]],
						[bbox[2], bbox[3]],
						[bbox[0], bbox[3]],
						[bbox[0], bbox[1]]
					]
				]
			}
		};

		map.addSource('event-aoi', {
			type: 'geojson',
			data: aoiPolygon
		});

		map.addLayer({
			id: 'aoi-boundary-line',
			type: 'line',
			source: 'event-aoi',
			paint: {
				'line-color': '#f59e0b',
				'line-width': 1.5,
				'line-dasharray': [3, 2],
				'line-opacity': 0.85
			}
		});

		// Add Main Change Event GeoJSON
		map.addSource('event-geometry', {
			type: 'geojson',
			data: geojson
		});

		// Permanent water fill
		map.addLayer({
			id: 'permanent-water-fill',
			type: 'fill',
			source: 'event-geometry',
			filter: ['==', 'class', 'permanent_water'],
			paint: {
				'fill-color': '#0369a1',
				'fill-opacity': 0.75
			}
		});

		map.addLayer({
			id: 'permanent-water-line',
			type: 'line',
			source: 'event-geometry',
			filter: ['==', 'class', 'permanent_water'],
			paint: {
				'line-color': '#38bdf8',
				'line-width': 1,
				'line-opacity': 0.7
			}
		});

		// Inundation glow / heatmap effect under layer
		map.addLayer({
			id: 'inundation-glow',
			type: 'line',
			source: 'event-geometry',
			filter: ['!=', 'class', 'permanent_water'],
			paint: {
				'line-color': '#2e96f5',
				'line-width': 8,
				'line-opacity': 0.45,
				'line-blur': 4
			}
		});

		// Inundation polygon fill (Detected change)
		map.addLayer({
			id: 'inundation-fill',
			type: 'fill',
			source: 'event-geometry',
			filter: ['!=', 'class', 'permanent_water'],
			paint: {
				'fill-color': '#2e96f5',
				'fill-opacity': appState.opacity * 0.85
			}
		});

		// Inundation crisp boundary line
		map.addLayer({
			id: 'inundation-line',
			type: 'line',
			source: 'event-geometry',
			filter: ['!=', 'class', 'permanent_water'],
			paint: {
				'line-color': '#67e8f9',
				'line-width': 1.8,
				'line-opacity': 0.95
			}
		});

		if (evidence) {
			addEvidenceLayers(map, evidence);
			addEvidenceLayers(comparisonMap, evidence);
		}
		layersEventId = event.id;
		updateLayerVisibility();
	}

	function addEvidenceLayers(target: MapLibreMap, evidence: OpticalEvidence) {
		target.addSource('candidate-evidence', { type: 'geojson', data: evidence.geometry });
		target.addSource('candidate-markers', {
			type: 'geojson',
			data: {
				type: 'FeatureCollection',
				features: evidence.candidates.map((candidate) => ({
					type: 'Feature',
					properties: { component: candidate.component },
					geometry: { type: 'Point', coordinates: candidate.centroid_lon_lat }
				}))
			}
		});
		target.addLayer({
			id: 'evidence-fill',
			type: 'fill',
			source: 'candidate-evidence',
			paint: { 'fill-color': '#fbbf24', 'fill-opacity': 0.16 }
		});
		target.addLayer({
			id: 'evidence-line',
			type: 'line',
			source: 'candidate-evidence',
			paint: { 'line-color': '#fbbf24', 'line-width': 1.5 }
		});
		target.addLayer({
			id: 'evidence-markers',
			type: 'circle',
			source: 'candidate-markers',
			paint: {
				'circle-radius': 5,
				'circle-color': '#0f172a',
				'circle-stroke-color': '#fbbf24',
				'circle-stroke-width': 1.5
			}
		});
		target.addLayer({
			id: 'evidence-selected',
			type: 'line',
			source: 'candidate-evidence',
			filter: ['==', 'component', -1],
			paint: { 'line-color': '#ffffff', 'line-width': 3 }
		});
	}

	function updateLayerVisibility() {
		if (!map || !isMapLoaded) return;

		const mode = appState.activeLayer;
		const opacity = appState.opacity;
		const evidenceMode = mode === 'optical_compare';

		// Radar raster layers
		const hasBaseline = Boolean(map.getLayer('radar-baseline-layer'));
		const hasPost = Boolean(map.getLayer('radar-post-layer'));

		if (hasBaseline && hasPost) {
			if (mode === 'baseline' || (evidenceMode && appState.radarReference === 'baseline')) {
				map.setLayoutProperty('radar-baseline-layer', 'visibility', 'visible');
				map.setLayoutProperty('radar-post-layer', 'visibility', 'none');
				map.setPaintProperty('radar-baseline-layer', 'raster-opacity', opacity);
			} else if (
				mode === 'post' ||
				mode === 'field_timing' ||
				mode === 'landcover' ||
				mode === 'change_mask' ||
				mode === 'difference' ||
				evidenceMode
			) {
				map.setLayoutProperty('radar-baseline-layer', 'visibility', 'none');
				map.setLayoutProperty('radar-post-layer', 'visibility', 'visible');
				map.setPaintProperty('radar-post-layer', 'raster-opacity', opacity);
			} else if (mode === 'compare') {
				map.setLayoutProperty('radar-baseline-layer', 'visibility', 'visible');
				map.setLayoutProperty('radar-post-layer', 'visibility', 'none');
				map.setPaintProperty('radar-baseline-layer', 'raster-opacity', opacity);
			} else if (mode === 'series' || mode === 'period') {
				map.setLayoutProperty('radar-baseline-layer', 'visibility', 'none');
				map.setLayoutProperty('radar-post-layer', 'visibility', 'none');
			}
		}
		if (map.getLayer('radar-series-layer')) {
			map.setLayoutProperty(
				'radar-series-layer',
				'visibility',
				mode === 'series' ? 'visible' : 'none'
			);
			map.setPaintProperty('radar-series-layer', 'raster-opacity', opacity);
		}
		for (const [target, id] of [
			[map, 'radar-period-from-layer'],
			[comparisonMap, 'comparison-period-to-layer']
		] as const) {
			if (!target?.getLayer(id)) continue;
			target.setLayoutProperty(id, 'visibility', mode === 'period' ? 'visible' : 'none');
			target.setPaintProperty(id, 'raster-opacity', opacity);
		}
		for (const [id, on] of [
			['landcover-layer', mode === 'landcover'],
			['water-loss-layer', mode === 'landcover' && appState.showWaterLoss]
		] as const) {
			if (!map.getLayer(id)) continue;
			map.setLayoutProperty(id, 'visibility', on ? 'visible' : 'none');
			// The loss overlay stays opaque so it reads over any class colour.
			map.setPaintProperty(id, 'raster-opacity', id === 'water-loss-layer' ? 1 : opacity);
		}
		if (map.getLayer('field-timing-layer')) {
			map.setLayoutProperty(
				'field-timing-layer',
				'visibility',
				mode === 'field_timing' ? 'visible' : 'none'
			);
			map.setPaintProperty('field-timing-layer', 'raster-opacity', opacity);
		}
		if (map.getLayer('radar-difference-layer')) {
			map.setLayoutProperty(
				'radar-difference-layer',
				'visibility',
				mode === 'difference' ? 'visible' : 'none'
			);
			map.setPaintProperty('radar-difference-layer', 'raster-opacity', opacity);
		}
		if (comparisonMap?.getLayer('comparison-post-layer')) {
			comparisonMap.setLayoutProperty(
				'comparison-post-layer',
				'visibility',
				mode === 'compare' ? 'visible' : 'none'
			);
			comparisonMap.setPaintProperty('comparison-post-layer', 'raster-opacity', opacity);
		}
		if (comparisonMap?.getLayer('comparison-optical-layer'))
			comparisonMap.setLayoutProperty(
				'comparison-optical-layer',
				'visibility',
				evidenceMode && !opticalLoading && !opticalError ? 'visible' : 'none'
			);
		for (const target of [map, comparisonMap]) {
			if (!target) continue;
			for (const id of [
				'evidence-fill',
				'evidence-line',
				'evidence-markers',
				'evidence-selected'
			]) {
				if (target.getLayer(id))
					target.setLayoutProperty(
						id,
						'visibility',
						evidenceMode || mode === 'change_mask' ? 'visible' : 'none'
					);
			}
			if (target.getLayer('evidence-selected'))
				target.setFilter('evidence-selected', [
					'==',
					'component',
					appState.selectedCandidateId ?? -1
				]);
		}

		if (map.getLayer('inundation-fill')) {
			if (mode !== 'change_mask' || appState.opticalEvidence) {
				// Keep observations separate from our classification output.
				map.setLayoutProperty('inundation-fill', 'visibility', 'none');
				map.setLayoutProperty('inundation-line', 'visibility', 'none');
				map.setLayoutProperty('inundation-glow', 'visibility', 'none');
			} else {
				map.setLayoutProperty('inundation-fill', 'visibility', 'visible');
				map.setLayoutProperty('inundation-line', 'visibility', 'visible');
				map.setLayoutProperty('inundation-glow', 'visibility', 'visible');
				map.setPaintProperty('inundation-fill', 'fill-opacity', opacity * 0.85);
			}
		}
	}

	function resetCamera() {
		if (map) {
			map.flyTo({
				center: appState.selectedEvent.location.center,
				zoom: appState.selectedEvent.location.zoom,
				duration: 1200
			});
		}
	}
</script>

<div class="absolute inset-0 overflow-hidden bg-slate-950">
	<!-- MapLibre canvas container -->
	<div bind:this={mapContainer} class="h-full w-full"></div>
	<div
		bind:this={comparisonContainer}
		class="pointer-events-none absolute inset-0"
		aria-hidden="true"
		data-testid="comparison-map"
		style:position="absolute"
		style:inset="0"
		style:visibility={['compare', 'period', 'optical_compare'].includes(appState.activeLayer)
			? 'visible'
			: 'hidden'}
		style:clip-path={`inset(0 0 0 ${appState.sliderPosition}%)`}
	></div>

	<!-- Loading indicator overlay -->
	{#if (!isMapLoaded || isLoadingLayers) && !appState.mapError}
		<div
			class="absolute inset-0 z-30 flex flex-col items-center justify-center bg-slate-950/80 backdrop-blur-sm"
		>
			<Loader2 class="h-8 w-8 animate-spin text-yonder-400" />
			<div class="font-mono-telemetry mt-3 text-xs tracking-wider text-slate-300 uppercase">
				Loading observation layers...
			</div>
		</div>
	{/if}

	{#if basemapUnavailable && !(appState.selectedCandidate && ['change_mask', 'optical_compare'].includes(appState.activeLayer))}
		<p
			class="absolute right-3 bottom-12 z-20 max-w-48 rounded bg-slate-950/90 p-2 text-[10px] text-amber-200"
		>
			Basemap unavailable. Radar observations remain available for comparison.
		</p>
	{/if}

	<!-- Error state -->
	{#if appState.mapError}
		<div
			class="absolute inset-0 z-30 flex flex-col items-center justify-center bg-slate-950/90 p-6 text-center"
		>
			<AlertCircle class="mb-2 h-10 w-10 text-rose-500" />
			<h3 class="text-sm font-bold text-white">Geospatial Display Warning</h3>
			<p class="mt-1 max-w-md text-xs text-slate-400">{appState.mapError}</p>
		</div>
	{/if}

	<!-- Comparison Split Slider (Active when layer is 'compare') -->
	{#if ['compare', 'period', 'optical_compare'].includes(appState.activeLayer)}
		<ComparisonSlider />
	{/if}

	<!-- Floating Top-Left Controls: Layer toggles -->
	<div class="absolute top-4 left-4 z-20 max-w-[calc(100%-2rem)]">
		<LayerControls onResetCamera={resetCamera} />
	</div>

	{#if appState.activeLayer === 'optical_compare' && (opticalLoading || opticalError)}
		<div
			role="status"
			class="absolute top-48 right-3 z-20 max-w-52 rounded border border-amber-700 bg-slate-950 p-3 text-xs text-amber-200"
		>
			{opticalLoading
				? 'Loading dated optical image…'
				: 'Optical image unavailable. Radar remains available. Choose another optical date or return to the radar views.'}
		</div>
	{/if}
	{#if appState.selectedCandidate && ['change_mask', 'optical_compare'].includes(appState.activeLayer)}
		<div
			class="absolute right-3 bottom-16 z-20 max-w-56 rounded border border-yonder-700 bg-slate-950/95 p-3 text-xs text-slate-200"
			role="status"
		>
			<p class="font-semibold text-yonder-200">
				Candidate {appState.selectedCandidate.component} · {appState.selectedCandidate.area_m2.toLocaleString()}
				m²
			</p>
			<p class="mt-1 text-amber-200">Unconfirmed water change</p>
			<a href="#candidate-evidence" class="mt-1 inline-block text-yonder-300 underline"
				>View selected candidate evidence</a
			>
		</div>
	{/if}

	{#if appState.activeLayer === 'period'}
		<div
			class="pointer-events-none absolute inset-x-3 top-3 bottom-3 z-20 flex flex-col justify-end sm:top-auto sm:bottom-6 sm:left-auto sm:w-80"
		>
			<PeriodPanel />
		</div>
	{/if}

	<!-- Floating Bottom-Left: Map Legend -->
	<div class="absolute bottom-6 left-4 z-20 hidden max-w-xs sm:block">
		<MapLegend />
	</div>
	<!-- Phones: the legend folds away so it does not cover the small map -->
	{#if appState.activeLayer !== 'period'}
		<details class="absolute bottom-3 left-3 z-20 max-w-[calc(100%-1.5rem)] sm:hidden">
			<summary
				class="w-fit cursor-pointer rounded border border-yonder-500/50 bg-deep-blue/95 px-2 py-1 text-[11px] font-bold text-white"
			>
				Legend
			</summary>
			<div class="mt-1 max-h-56 overflow-y-auto rounded-lg">
				<MapLegend />
			</div>
		</details>
	{/if}

	<!-- Floating Coordinate / Inspection Tooltip on Hover -->
	{#if hoveredFeature}
		<div
			class="absolute right-4 bottom-6 z-20 max-w-xs rounded-lg border border-yonder-500/40 bg-slate-950/90 p-3 text-xs text-slate-200 shadow-2xl backdrop-blur-md"
		>
			<div class="flex items-center gap-1.5 font-bold text-yonder-300">
				<span class="h-2 w-2 animate-ping rounded-full bg-yonder-400"></span>
				<span>{hoveredFeature.name}</span>
			</div>
			<div class="font-mono-telemetry mt-2 space-y-1 text-[11px] text-slate-300">
				{#if hoveredFeature.area_km2}
					<div class="flex justify-between">
						<span class="text-slate-500">Candidate Area:</span>
						<span class="font-bold text-white">{hoveredFeature.area_km2} km²</span>
					</div>
				{/if}
				{#if hoveredFeature.backscatter_db}
					<div class="flex justify-between">
						<span class="text-slate-500">SAR Backscatter:</span>
						<span class="text-yonder-300">{hoveredFeature.backscatter_db} dB</span>
					</div>
				{/if}
				{#if hoveredFeature.confidence}
					<div class="flex justify-between">
						<span class="text-slate-500">Heuristic score:</span>
						<span class="text-emerald-400">
							{hoveredFeature.confidence.toFixed(3)} / 1
						</span>
					</div>
				{/if}
			</div>
		</div>
	{/if}
</div>
