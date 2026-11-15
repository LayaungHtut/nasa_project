<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import {
		Map as MapLibreMap,
		NavigationControl,
		ScaleControl,
		AttributionControl,
		LngLatBounds,
		setWorkerUrl,
		type StyleSpecification,
		type ImageSource,
		type GeoJSONSource,
		type ExpressionSpecification,
		type MapMouseEvent
	} from 'maplibre-gl';
	import mapWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
	import { appState } from '$lib/stores/appState.svelte';
	import { findPatch, ha, patchLabel, shortDate } from '$lib/data/scenarios';
	import ComparisonSlider from './ComparisonSlider.svelte';
	import ScenarioLegend from './ScenarioLegend.svelte';
	import MapLayerControls from './MapLayerControls.svelte';
	import { AlertCircle } from 'lucide-svelte';

	let mapContainer = $state<HTMLDivElement | null>(null);
	let comparisonContainer = $state<HTMLDivElement | null>(null);
	let map = $state<MapLibreMap | null>(null);
	let comparisonMap = $state<MapLibreMap | null>(null);
	let basemapUnavailable = $state(false);
	/** Detected patch under the pointer (real Hpakant data only), for the hover label. */
	let hover = $state<{ id: string; x: number; y: number } | null>(null);
	// Only patches of the pass on screen; a label left over from another pass or module is dropped.
	let hoverPatch = $derived.by(() => {
		const p = hover ? findPatch(appState.scenario, hover.id) : null;
		return p && p.epoch === appState.epochIndex ? p : null;
	});

	let scenario = $derived(appState.scenario);
	let epoch = $derived(scenario.epochs[appState.epochIndex]);
	let baseline = $derived(scenario.epochs[0]);
	let compare = $derived(appState.layer === 'compare');
	let insarUrl = $derived(
		appState.layer === 'coherence'
			? epoch.coherence_url
			: appState.layer === 'deformation'
				? epoch.displacement_url
				: null
	);
	let insarMissing = $derived(
		(appState.layer === 'coherence' || appState.layer === 'deformation') && !insarUrl
	);

	const FALLBACK_STYLE: StyleSpecification = {
		version: 8,
		sources: {},
		layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#07173f' } }]
	};
	// Overlay colours: dark-surface categorical steps (validated); green stays clear of the LOS ramp's orange and blue.
	const KIND_COLOR = [
		'match',
		['get', 'kind'],
		'disturbed',
		'#d95926',
		'new_water',
		'#3987e5',
		'slope_motion',
		'#199e70',
		'#d3dcee'
	] as const;

	const POLYGONS: ExpressionSpecification = ['==', ['geometry-type'], 'Polygon'];

	function addOverlays(m: MapLibreMap) {
		const empty = { type: 'FeatureCollection' as const, features: [] };
		m.addSource('overlays', { type: 'geojson', data: empty });
		m.addLayer({
			id: 'overlay-fill',
			type: 'fill',
			source: 'overlays',
			filter: POLYGONS,
			paint: { 'fill-color': KIND_COLOR as never, 'fill-opacity': 0.42 }
		});
		m.addLayer({
			id: 'overlay-outline',
			type: 'line',
			source: 'overlays',
			filter: POLYGONS,
			paint: { 'line-color': KIND_COLOR as never, 'line-width': 1.5 }
		});
		// Hover and selection rings for inspectable (real-data) patches; white so they read over both colours.
		m.addLayer({
			id: 'patch-hover',
			type: 'line',
			source: 'overlays',
			filter: patchFilter(null),
			paint: { 'line-color': '#ffffff', 'line-width': 1.5, 'line-opacity': 0.8 }
		});
		m.addLayer({
			id: 'patch-selected',
			type: 'line',
			source: 'overlays',
			filter: patchFilter(null),
			paint: { 'line-color': '#ffffff', 'line-width': 3 }
		});
	}

	function addImage(m: MapLibreMap, id: string, opacity = 1) {
		m.addSource(id, {
			type: 'image',
			url: scenario.epochs[0].sar_url,
			coordinates: scenario.location.image_coordinates
		});
		m.addLayer({
			id: `${id}-layer`,
			type: 'raster',
			source: id,
			paint: {
				'raster-opacity': opacity,
				'raster-resampling': 'nearest',
				'raster-fade-duration': 0
			}
		});
	}

	function patchFilter(id: string | null): ExpressionSpecification {
		return ['==', ['get', 'patch_id'], id ?? ''];
	}

	/** Inspectable patches under a point, with a few pixels of slack so small patches can be tapped. */
	function patchAt(e: MapMouseEvent): string | null {
		if (!map) return null;
		const { x, y } = e.point;
		const hits = map.queryRenderedFeatures(
			[
				[x - 4, y - 4],
				[x + 4, y + 4]
			],
			{ layers: ['overlay-fill'] }
		);
		const id = hits.find((f) => typeof f.properties?.patch_id === 'string')?.properties.patch_id;
		return typeof id === 'string' ? id : null;
	}

	function onPatchHover(e: MapMouseEvent) {
		const id = patchAt(e);
		hover = id ? { id, x: e.point.x, y: e.point.y } : null;
		if (map) map.getCanvas().style.cursor = id ? 'pointer' : '';
	}

	function clearHover() {
		hover = null;
		if (map) map.getCanvas().style.cursor = '';
	}

	/** Click a patch to inspect it; click elsewhere to clear the selection. */
	function onMapClick(e: MapMouseEvent) {
		if (compare || !appState.showOverlays) return;
		const id = patchAt(e);
		if (id) appState.selectPatch(id);
		else if (appState.selectedPatchId) appState.selectPatch(null);
	}

	onMount(() => {
		if (!mapContainer || !comparisonContainer) return;
		// Vite must emit the worker as an asset; its default relative URL breaks once bundled.
		setWorkerUrl(mapWorkerUrl);
		appState.mapError = null;
		let cancelled = false;
		const view = { center: scenario.location.center, zoom: scenario.location.zoom };
		const m = new MapLibreMap({
			container: mapContainer,
			style: FALLBACK_STYLE,
			...view,
			minZoom: 4,
			maxZoom: 17,
			attributionControl: false
		});
		const c = new MapLibreMap({
			container: comparisonContainer,
			style: FALLBACK_STYLE,
			...view,
			interactive: false,
			attributionControl: false
		});
		c.getCanvas().removeAttribute('tabindex');
		const sync = () =>
			c.jumpTo({
				center: m.getCenter(),
				zoom: m.getZoom(),
				bearing: m.getBearing(),
				pitch: m.getPitch()
			});
		m.on('move', sync);
		const resizeObserver = new ResizeObserver(() => {
			m.resize();
			c.resize();
			sync();
		});
		resizeObserver.observe(mapContainer);
		m.addControl(
			new AttributionControl({
				compact: true,
				customAttribution:
					'NASA-ISRO NISAR L2 GCOV/GUNW via ASF DAAC · NASADEM (LP DAAC) · Team YOUTHs'
			}),
			'bottom-right'
		);
		m.addControl(new NavigationControl({ visualizePitch: true }), 'top-right');
		m.addControl(new ScaleControl({ maxWidth: 100, unit: 'metric' }), 'bottom-right');
		m.on('error', (e) => {
			const sourceId = (e as { sourceId?: string }).sourceId;
			if (sourceId && sourceId !== 'openmaptiles')
				appState.mapError = 'A radar layer failed to load.';
		});

		let ready = 0;
		const onLoad = () => {
			if (++ready < 2) return;
			// Start the attribution collapsed; it still opens from its (i) button.
			m.getContainer()
				.querySelector('.maplibregl-ctrl-attrib')
				?.classList.remove('maplibregl-compact-show');
			addImage(m, 'sar');
			addImage(m, 'insar');
			addOverlays(m);
			addImage(c, 'sar');
			addOverlays(c);
			m.on('mousemove', 'overlay-fill', onPatchHover);
			m.on('mouseleave', 'overlay-fill', clearHover);
			m.on('click', onMapClick);
			map = m;
			comparisonMap = c;
			void loadBasemap();
		};
		async function loadBasemap() {
			try {
				const response = await fetch('https://tiles.openfreemap.org/styles/dark', {
					signal: AbortSignal.timeout(8000)
				});
				if (!response.ok) throw new Error(`Basemap HTTP ${response.status}`);
				const style = (await response.json()) as StyleSpecification;
				if (cancelled) return;
				for (const target of [m, c])
					target.setStyle(style, {
						transformStyle: (previous, next) => ({
							...next,
							sources: { ...next.sources, ...previous?.sources },
							layers: [
								...next.layers,
								...(previous?.layers.filter((layer) => layer.id !== 'background') ?? [])
							]
						})
					});
			} catch {
				if (!cancelled) basemapUnavailable = true;
			}
		}
		m.once('load', onLoad);
		c.once('load', onLoad);

		return () => {
			cancelled = true;
			resizeObserver.disconnect();
			m.remove();
			c.remove();
			map = null;
			comparisonMap = null;
		};
	});

	// Re-frame the map when the module changes.
	$effect(() => {
		const coords = scenario.location.image_coordinates;
		if (!map) return;
		const bounds = coords.reduce((b, p) => b.extend(p), new LngLatBounds(coords[0], coords[0]));
		map.fitBounds(bounds, { padding: 40, duration: 900 });
	});

	// Overlay data for the selected scenario.
	$effect(() => {
		const data = scenario.geojson;
		for (const m of [map, comparisonMap])
			(m?.getSource('overlays') as GeoJSONSource)?.setData(data);
	});

	// Features without an epoch (moving-slope candidates, measured over all pairs) always show; the rest only on their pass.
	$effect(() => {
		const i = appState.epochIndex;
		const filter: ExpressionSpecification = [
			'any',
			['!', ['has', 'epoch']],
			['==', ['get', 'epoch'], i]
		];
		for (const [m, show] of [
			[map, appState.showOverlays && !compare],
			[comparisonMap, appState.showOverlays]
		] as const) {
			if (!m) continue;
			for (const id of ['overlay-fill', 'overlay-outline']) {
				m.setFilter(id, ['all', POLYGONS, filter]);
				m.setLayoutProperty(id, 'visibility', show ? 'visible' : 'none');
			}
			// Over InSAR, detections become outlines so they do not hide the measurement beneath.
			m.setPaintProperty('overlay-fill', 'fill-opacity', insarUrl ? 0.08 : 0.42);
		}
	});

	// Radar images: the main map shows the selected pass (or the baseline on the left of the swipe).
	$effect(() => {
		const coordinates = scenario.location.image_coordinates;
		if (!map || !comparisonMap) return;
		(map.getSource('sar') as ImageSource).updateImage({
			url: compare ? baseline.sar_url : epoch.sar_url,
			coordinates
		});
		(comparisonMap.getSource('sar') as ImageSource).updateImage({
			url: epoch.sar_url,
			coordinates
		});
		if (insarUrl)
			(map.getSource('insar') as ImageSource).updateImage({ url: insarUrl, coordinates });
		map.setLayoutProperty('insar-layer', 'visibility', insarUrl ? 'visible' : 'none');
	});

	// Hover and selection rings.
	$effect(() => {
		const selected =
			appState.selectedPatch?.patch_id ?? appState.selectedCandidate?.candidate_id ?? null;
		const hovered = hoverPatch?.patch_id ?? null;
		for (const [m, show] of [
			[map, appState.showOverlays && !compare],
			[comparisonMap, appState.showOverlays]
		] as const) {
			if (!m) continue;
			m.setFilter('patch-selected', patchFilter(selected));
			m.setFilter('patch-hover', patchFilter(m === map && hovered !== selected ? hovered : null));
			for (const id of ['patch-selected', 'patch-hover'])
				m.setLayoutProperty(id, 'visibility', show ? 'visible' : 'none');
		}
	});

	// Zoom to a patch when one is picked (map or panel), not when the pass changes.
	$effect(() => {
		void appState.patchFocus;
		untrack(() => {
			const p = appState.selectedPatch ?? appState.selectedCandidate;
			if (!map || !p) return;
			const [w, s, e, n] = p.bbox;
			map.fitBounds(
				[
					[w, s],
					[e, n]
				],
				{ padding: 80, maxZoom: 15, duration: 900 }
			);
		});
	});
</script>

<div class="absolute inset-0 overflow-hidden bg-deep-blue">
	<!-- MapLibre's own CSS sets position: relative on its container, so size it by height, not inset. -->
	<div bind:this={mapContainer} class="h-full w-full"></div>
	<!-- Hidden with visibility, not display, so the comparison map keeps a size to render into. -->
	<div
		bind:this={comparisonContainer}
		class="pointer-events-none z-10"
		style:position="absolute"
		style:inset="0"
		style:visibility={compare ? 'visible' : 'hidden'}
		style:clip-path={`inset(0 0 0 ${appState.sliderPosition}%)`}
		aria-hidden="true"
	></div>

	{#if compare}
		<ComparisonSlider
			leftLabel={baseline.label}
			leftDate={`Day ${baseline.day} · ${shortDate(baseline.date)}`}
			rightLabel={epoch.label}
			rightDate={`Day ${epoch.day} · ${shortDate(epoch.date)}`}
		/>
	{/if}

	<MapLayerControls />

	{#if insarMissing}
		<div
			class="absolute top-1/2 left-1/2 z-30 w-72 -translate-x-1/2 -translate-y-1/2 rounded-lg border border-yonder-400/60 bg-deep-blue/95 p-3 text-center text-xs text-slate-100 shadow-xl"
		>
			{#if scenario.module === 'observed' && appState.layer === 'deformation'}
				No deformation layer for the real data: dug ground decorrelates within 12 days, and the
				atmospheric and ionospheric corrections were not validated for this frame.
			{:else}
				InSAR compares two passes. Pick a later pass on the timeline to see the
				{appState.layer === 'coherence' ? 'coherence' : 'deformation'} between it and the pass before.
			{/if}
		</div>
	{/if}

	{#if hover && hoverPatch && !compare}
		<div
			class="pointer-events-none absolute z-30 rounded-md border border-yonder-400/60 bg-deep-blue/95 px-2 py-1 text-[11px] whitespace-nowrap text-white shadow-lg"
			style:left={`${hover.x + 12}px`}
			style:top={`${hover.y + 12}px`}
			style:transform={hover.x > (mapContainer?.clientWidth ?? 0) - 260
				? 'translateX(calc(-100% - 24px))'
				: undefined}
		>
			<strong>{ha(hoverPatch.area_m2)}</strong>
			<span class="text-slate-200">· {patchLabel(hoverPatch)} · click to inspect</span>
		</div>
	{/if}

	<div class="absolute bottom-8 left-3 z-30 hidden max-w-xs sm:block">
		<ScenarioLegend />
	</div>
	<details class="absolute bottom-3 left-3 z-30 max-w-[calc(100%-1.5rem)] sm:hidden">
		<summary
			class="cursor-pointer rounded-md border border-yonder-500/50 bg-deep-blue/95 px-2.5 py-1 text-[11px] font-bold text-white"
		>
			Legend
		</summary>
		<div class="mt-1"><ScenarioLegend /></div>
	</details>

	{#if appState.mapError || basemapUnavailable}
		<div
			class="absolute right-3 bottom-8 z-30 flex items-center gap-2 rounded-md border border-slate-600 bg-deep-blue/95 px-2.5 py-1.5 text-[11px] text-slate-200"
		>
			<AlertCircle class="h-3.5 w-3.5 text-neon-yellow" />
			<span>{appState.mapError ?? 'Basemap offline; radar layers still shown.'}</span>
		</div>
	{/if}
</div>
