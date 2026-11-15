<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import {
		Map as MapLibreMap,
		NavigationControl,
		ScaleControl,
		AttributionControl,
		setWorkerUrl,
		type StyleSpecification,
		type MapLayerMouseEvent
	} from 'maplibre-gl';
	import mapWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
	import { appState } from '$lib/stores/appState.svelte';
	import { api } from '$lib/api/client';
	import ComparisonSlider from './ComparisonSlider.svelte';
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
					customAttribution: 'NASA/ISRO NISAR'
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
		} catch (err) {
			console.error('Failed to initialize MapLibre:', err);
			appState.mapError = 'WebGL map initialization failed.';
		}
		return () => {
			cancelled = true;
			layerRequest++;
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

	function observationUrls(event: typeof appState.selectedEvent) {
		const tiles = event.tiles;
		return {
			baseline: tiles.baseline_preview_url ?? tiles.preview_url,
			post: tiles.post_event_preview_url ?? tiles.preview_url
		};
	}

	// React to layer toggles & opacity
	$effect(() => {
		if (!map || !isMapLoaded) return;
		updateLayerVisibility();
	});

	async function setupEventLayers() {
		if (!map || !isMapLoaded) return;

		const event = appState.selectedEvent;
		const request = ++layerRequest;
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
		if (comparisonMap.getLayer('comparison-post-layer'))
			comparisonMap.removeLayer('comparison-post-layer');
		if (comparisonMap.getSource('comparison-post')) comparisonMap.removeSource('comparison-post');
		// Remove existing custom sources/layers if present
		const layerIds = [
			'inundation-glow',
			'inundation-fill',
			'inundation-line',
			'permanent-water-fill',
			'permanent-water-line',
			'aoi-boundary-line',
			'radar-baseline-layer',
			'radar-post-layer'
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
		// Add Raster Radar Overlays if corner coordinates exist
		const tiles = event.tiles;
		const imageCoordinates = tiles?.corner_coordinates;
		if (imageCoordinates) {
			const { baseline: baselineUrl, post: postUrl } = observationUrls(event);

			if (baselineUrl) {
				map.addSource('radar-baseline', {
					type: 'image',
					url: baselineUrl,
					coordinates: imageCoordinates
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
					coordinates: imageCoordinates
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
					coordinates: imageCoordinates
				});
				map.addLayer({
					id: 'radar-post-layer',
					type: 'raster',
					source: 'radar-post',
					paint: { 'raster-opacity': appState.opacity }
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

		updateLayerVisibility();
	}

	function updateLayerVisibility() {
		if (!map || !isMapLoaded) return;

		const mode = appState.activeLayer;
		const opacity = appState.opacity;

		// Radar raster layers
		const hasBaseline = Boolean(map.getLayer('radar-baseline-layer'));
		const hasPost = Boolean(map.getLayer('radar-post-layer'));

		if (hasBaseline && hasPost) {
			if (mode === 'baseline') {
				map.setLayoutProperty('radar-baseline-layer', 'visibility', 'visible');
				map.setLayoutProperty('radar-post-layer', 'visibility', 'none');
				map.setPaintProperty('radar-baseline-layer', 'raster-opacity', opacity);
			} else if (mode === 'post' || mode === 'change_mask') {
				map.setLayoutProperty('radar-baseline-layer', 'visibility', 'none');
				map.setLayoutProperty('radar-post-layer', 'visibility', 'visible');
				map.setPaintProperty('radar-post-layer', 'raster-opacity', opacity);
			} else if (mode === 'compare') {
				map.setLayoutProperty('radar-baseline-layer', 'visibility', 'visible');
				map.setLayoutProperty('radar-post-layer', 'visibility', 'none');
				map.setPaintProperty('radar-baseline-layer', 'raster-opacity', opacity);
			}
		}
		if (comparisonMap?.getLayer('comparison-post-layer')) {
			comparisonMap.setLayoutProperty(
				'comparison-post-layer',
				'visibility',
				mode === 'compare' ? 'visible' : 'none'
			);
			comparisonMap.setPaintProperty('comparison-post-layer', 'raster-opacity', opacity);
		}
		if (map.getLayer('inundation-fill')) {
			if (mode !== 'change_mask') {
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
		style:visibility={appState.activeLayer === 'compare' ? 'visible' : 'hidden'}
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

	{#if basemapUnavailable}
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
	{#if appState.activeLayer === 'compare'}
		<ComparisonSlider />
	{/if}

	<!-- Floating Top-Left Controls: Layer toggles -->
	<div class="absolute top-4 left-4 z-20 max-w-[calc(100%-2rem)]">
		<LayerControls onResetCamera={resetCamera} />
	</div>

	<!-- Floating Bottom-Left: Map Legend -->
	<div class="absolute bottom-6 left-4 z-20 hidden max-w-xs sm:block">
		<MapLegend />
	</div>
	<!-- Phones: the legend folds away so it does not cover the small map -->
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
