<script lang="ts">
	import { onMount } from 'svelte';
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
		type ExpressionSpecification
	} from 'maplibre-gl';
	import mapWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
	import { appState, type ScenarioLayer } from '$lib/stores/appState.svelte';
	import { shortDate } from '$lib/data/scenarios';
	import ComparisonSlider from './ComparisonSlider.svelte';
	import ScenarioLegend from './ScenarioLegend.svelte';
	import { Layers, SplitSquareHorizontal, Waves, Activity, AlertCircle } from 'lucide-svelte';

	let mapContainer = $state<HTMLDivElement | null>(null);
	let comparisonContainer = $state<HTMLDivElement | null>(null);
	let map = $state<MapLibreMap | null>(null);
	let comparisonMap = $state<MapLibreMap | null>(null);
	let basemapUnavailable = $state(false);

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

	const layerButtons: Array<{ id: ScenarioLayer; label: string; icon: typeof Layers }> = [
		{ id: 'sar', label: 'Radar pass', icon: Layers },
		{ id: 'compare', label: 'Before / after', icon: SplitSquareHorizontal },
		{ id: 'coherence', label: 'InSAR coherence', icon: Waves },
		{ id: 'deformation', label: 'InSAR deformation', icon: Activity }
	];

	const FALLBACK_STYLE: StyleSpecification = {
		version: 8,
		sources: {},
		layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#07173f' } }]
	};
	// Overlay colours: dark-surface categorical steps (validated), neon yellow reserved for the legal boundary.
	const KIND_COLOR = [
		'match',
		['get', 'kind'],
		'excavation_inside',
		'#3987e5',
		'excavation_outside',
		'#d95926',
		'landslide',
		'#d95926',
		'impoundment',
		'#3987e5',
		'new_channel',
		'#199e70',
		'abandoned_channel',
		'#8a94a8',
		'river_after',
		'#199e70',
		'#d3dcee'
	] as const;

	function addOverlays(m: MapLibreMap) {
		const empty = { type: 'FeatureCollection' as const, features: [] };
		m.addSource('overlays', { type: 'geojson', data: empty });
		m.addLayer({
			id: 'overlay-fill',
			type: 'fill',
			source: 'overlays',
			filter: baseFilter('overlay-fill'),
			paint: { 'fill-color': KIND_COLOR as never, 'fill-opacity': 0.42 }
		});
		m.addLayer({
			id: 'overlay-outline',
			type: 'line',
			source: 'overlays',
			filter: baseFilter('overlay-outline'),
			paint: { 'line-color': KIND_COLOR as never, 'line-width': 1.5 }
		});
		m.addLayer({
			id: 'overlay-rivers',
			type: 'line',
			source: 'overlays',
			filter: baseFilter('overlay-rivers'),
			paint: {
				'line-color': KIND_COLOR as never,
				'line-width': 2,
				'line-dasharray': [
					'case',
					['==', ['get', 'kind'], 'river_before'],
					['literal', [2, 2]],
					['literal', [1, 0]]
				]
			}
		});
		m.addLayer({
			id: 'permit-line',
			type: 'line',
			source: 'overlays',
			filter: baseFilter('permit-line'),
			paint: { 'line-color': '#eafe07', 'line-width': 2.5, 'line-dasharray': [3, 1.5] }
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
				customAttribution: 'Simulated NISAR-like radar layers (not observations) · Team YOUTHs'
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

	// Features without an epoch (the permit, the baseline river) always show; the rest only on their pass.
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
			for (const id of ['overlay-fill', 'overlay-outline', 'overlay-rivers', 'permit-line']) {
				m.setFilter(id, ['all', baseFilter(id), filter]);
				m.setLayoutProperty(id, 'visibility', show ? 'visible' : 'none');
			}
			// Over InSAR, detections become outlines so they do not hide the measurement beneath.
			m.setPaintProperty('overlay-fill', 'fill-opacity', insarUrl ? 0.08 : 0.42);
		}
	});

	function baseFilter(id: string): ExpressionSpecification {
		if (id === 'overlay-rivers') return ['==', ['geometry-type'], 'LineString'];
		if (id === 'permit-line') return ['==', ['get', 'kind'], 'permit'];
		if (id === 'overlay-outline')
			return ['all', ['==', ['geometry-type'], 'Polygon'], ['!=', ['get', 'kind'], 'permit']];
		return ['all', ['==', ['geometry-type'], 'Polygon'], ['!=', ['get', 'kind'], 'permit']];
	}

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

	<!-- Layer controls -->
	<div
		class="absolute top-3 left-3 z-30 max-w-[calc(100%-4.5rem)] rounded-lg border border-yonder-500/40 bg-deep-blue/95 p-1.5 shadow-xl backdrop-blur-md"
	>
		<div class="flex gap-1 overflow-x-auto sm:flex-wrap" role="group" aria-label="Map layer">
			{#each layerButtons as b (b.id)}
				{@const active = appState.layer === b.id}
				<button
					type="button"
					aria-pressed={active}
					onclick={() => (appState.layer = b.id)}
					class="flex shrink-0 items-center gap-1.5 rounded-md px-2.5 py-1.5 text-[11px] font-bold tracking-wider whitespace-nowrap uppercase transition-colors {active
						? 'border border-neon-yellow/70 bg-electric-blue/60 text-neon-yellow'
						: 'border border-transparent text-slate-200 hover:bg-electric-blue/30 hover:text-white'}"
				>
					<b.icon class="h-3.5 w-3.5" />
					<span>{b.label}</span>
				</button>
			{/each}
		</div>
		<label
			class="mt-1.5 flex cursor-pointer items-center gap-2 px-2 pb-0.5 text-[11px] text-slate-200"
		>
			<input type="checkbox" bind:checked={appState.showOverlays} class="accent-neon-yellow" />
			<span>Show boundaries and detections</span>
		</label>
		<div
			class="mx-2 mt-1 mb-0.5 hidden rounded border border-rocket-red bg-martian-red px-1.5 py-0.5 font-mono text-[9px] font-bold tracking-wider text-white uppercase sm:inline-block"
		>
			Simulated scenario · not a satellite observation
		</div>
	</div>

	{#if insarMissing}
		<div
			class="absolute top-1/2 left-1/2 z-30 w-72 -translate-x-1/2 -translate-y-1/2 rounded-lg border border-yonder-400/60 bg-deep-blue/95 p-3 text-center text-xs text-slate-100 shadow-xl"
		>
			InSAR compares two passes. Pick a later pass on the timeline to see the
			{appState.layer === 'coherence' ? 'coherence' : 'deformation'} between it and the pass before.
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
