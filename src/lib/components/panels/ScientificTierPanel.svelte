<script lang="ts">
	import { appState } from '$lib/stores/appState.svelte';
	import { api } from '$lib/api/client';
	import { resolve } from '$app/paths';
	import {
		Satellite,
		Cpu,
		Bot,
		AlertTriangle,
		ExternalLink,
		Info,
		CheckCircle2,
		RefreshCw
	} from 'lucide-svelte';

	let event = $derived(appState.selectedEvent);
	let isAiLoading = $state(false);
	let aiExplanation = $state<string | null>(null);

	// Load initial AI explanation lazily when component mounts or event changes
	$effect(() => {
		const currentEvent = appState.selectedEvent;
		if (currentEvent) {
			aiExplanation = currentEvent.ai_explanation;
		}
	});

	async function refreshExplanation() {
		const eventId = appState.selectedEvent.id;
		isAiLoading = true;
		try {
			const res = await api.explainEvent(eventId);
			if (appState.selectedEvent.id === eventId) aiExplanation = res.ai_explanation;
		} catch (err) {
			console.error('AI explanation failed:', err);
		} finally {
			isAiLoading = false;
		}
	}
</script>

<div class="space-y-3 font-sans text-xs">
	<!-- DATA STATUS BANNER (SCIENTIFIC INTEGRITY — Brand Guide p. 7 & 9 WCAG contrast) -->
	{#if event.data_status === 'SYNTHETIC_PLACEHOLDER'}
		<div class="rounded-lg border border-rocket-red bg-martian-red/90 p-3 text-white shadow-md">
			<div class="flex items-center gap-2 text-xs font-bold text-neon-yellow uppercase">
				<AlertTriangle class="h-4 w-4 shrink-0 text-neon-yellow" />
				<span>DATA STATUS: SYNTHETIC DEMO FIXTURE</span>
			</div>
			<p class="mt-1 text-[11px] leading-relaxed text-white">
				This dataset demonstrates the method with synthetic inputs. Its areas and shapes are not
				observations of a real event.
			</p>
		</div>
	{:else}
		<div
			class="flex items-center gap-2 rounded-lg border border-yonder-400/60 bg-electric-blue/45 p-2.5 text-xs text-white"
		>
			<CheckCircle2 class="h-4 w-4 shrink-0 text-neon-yellow" />
			<span class="font-bold tracking-wide uppercase">DATA STATUS: REAL NASA NISAR OBSERVATION</span
			>
		</div>
	{/if}

	<!-- TIER 1: NASA OBSERVATION -->
	<section
		class="brand-pattern-fiduciaries rounded-lg border border-slate-700/80 bg-deep-blue/95 p-3.5 shadow-lg backdrop-blur-sm"
		aria-labelledby="tier1-heading"
	>
		<div class="flex items-center justify-between border-b border-slate-800 pb-2">
			<div class="flex items-center gap-2">
				<span
					class="flex h-6 w-6 items-center justify-center rounded bg-electric-blue/50 text-neon-yellow"
				>
					<Satellite class="h-4 w-4" />
				</span>
				<h2 id="tier1-heading" class="text-[11px] font-bold tracking-wider text-white uppercase">
					Tier 1: NASA / ISRO Observation
				</h2>
			</div>
			<span
				class="rounded border px-1.5 py-0.5 font-mono text-[10px] font-bold {event.data_status ===
				'REAL'
					? 'border-neon-yellow/60 bg-electric-blue/50 text-neon-yellow'
					: 'border-rocket-red/60 bg-martian-red text-white'}"
			>
				{event.data_status === 'REAL' ? 'Calibrated L2 Data' : 'Cataloged Footprint'}
			</span>
		</div>

		<div class="font-mono-telemetry mt-2.5 grid grid-cols-2 gap-2 text-[11px]">
			<div>
				<span class="block text-[10px] text-slate-400 uppercase">Mission / Sensor</span>
				<span class="font-semibold text-white">
					{event.source_products[0]?.mission}
					{event.source_products[0]?.frequency_band}
				</span>
			</div>
			<div>
				<span class="block text-[10px] text-slate-400 uppercase">DAAC Source</span>
				<span class="font-semibold text-white">
					{event.source_products[0]?.daac} (Alaska Satellite Facility)
				</span>
			</div>
			<div>
				<span class="block text-[10px] text-slate-400 uppercase">Product Level</span>
				<span class="font-semibold text-yonder-400">
					{event.source_products[0]?.product} (Geocoded Covariance)
				</span>
			</div>
			<div>
				<span class="block text-[10px] text-slate-400 uppercase">Polarization</span>
				<span class="font-semibold text-white">
					{event.source_products[0]?.polarization ?? 'HH'} (Co-polar)
				</span>
			</div>
		</div>

		<div class="mt-2.5 rounded border border-slate-800 bg-slate-900/80 p-2 text-[10px]">
			<span class="block font-mono text-slate-400">Primary Granule ID:</span>
			<span class="font-mono break-all text-slate-200 select-all">
				{event.source_products[1]?.granule_id ?? event.source_products[0]?.granule_id}
			</span>
			{#if event.pending_real_source}
				<div class="mt-2 border-t border-slate-800/80 pt-1.5 text-[10px] text-yonder-300">
					<span class="font-bold">Catalog Candidate:</span>
					{event.pending_real_source.catalog_candidate_id} (ASF DAAC Track 40 / Frame 10)
				</div>
			{/if}
		</div>
	</section>

	<!-- TIER 2: YOUTHs ALGORITHMIC ANALYSIS -->
	<section
		class="brand-pattern-voronoi rounded-lg border border-yonder-500/40 bg-deep-blue/95 p-3.5 shadow-lg backdrop-blur-sm"
		aria-labelledby="tier2-heading"
	>
		<div class="flex items-center justify-between border-b border-yonder-900/60 pb-2">
			<div class="flex items-center gap-2">
				<span
					class="flex h-6 w-6 items-center justify-center rounded bg-electric-blue/50 text-yonder-400"
				>
					<Cpu class="h-4 w-4" />
				</span>
				<h2
					id="tier2-heading"
					class="text-[11px] font-bold tracking-wider text-yonder-300 uppercase"
				>
					Tier 2: YOUTHs Algorithmic Analysis
				</h2>
			</div>
			<span
				class="rounded border border-yonder-500/40 bg-electric-blue/35 px-1.5 py-0.5 font-mono text-[10px] text-white"
			>
				Deterministic Remote Sensing
			</span>
		</div>

		<!-- Metrics Grid -->
		<div class="mt-3 grid grid-cols-2 gap-3">
			<div class="rounded-md border border-yonder-800/70 bg-slate-900/80 p-2.5">
				<div class="text-[10px] font-semibold tracking-wide text-slate-300 uppercase">
					{event.phenomenon === 'surface_deformation'
						? 'Strain Zone Area'
						: 'New Inundation Candidate'}
				</div>
				<div class="mt-1 flex items-baseline gap-1.5">
					<span class="font-mono-telemetry text-xl font-extrabold text-yonder-400">
						{event.results.change_area_km2}
					</span>
					<span class="font-mono-telemetry text-xs text-slate-300">km²</span>
				</div>
				{#if event.results.changed_pixels}
					<div class="font-mono-telemetry mt-0.5 text-[10px] text-slate-300">
						{event.results.changed_pixels} pixels
					</div>
				{/if}
				{#if event.results.valid_fraction !== undefined}
					<div class="font-mono-telemetry text-[9px] font-bold text-neon-yellow">
						{(event.results.valid_fraction * 100).toFixed(0)}% valid data coverage
					</div>
				{/if}
			</div>

			<div class="rounded-md border border-yonder-800/70 bg-slate-900/80 p-2.5">
				<div class="text-[10px] font-semibold tracking-wide text-slate-300 uppercase">
					{event.results.confidence_type === 'heuristic_detection_score'
						? 'Heuristic Detection Score'
						: 'Detection Score'}
				</div>
				<div class="mt-1 flex items-baseline gap-1.5">
					<span class="font-mono-telemetry text-xl font-extrabold text-neon-yellow">
						{event.results.confidence.toFixed(3)}
					</span>
					<span class="font-mono-telemetry text-xs text-slate-300">/ 1.0</span>
				</div>
				<div class="mt-1 text-[9px] leading-tight text-slate-300">
					Heuristic based on data completeness and total candidate pixel count. Not a probability of
					flooding.
				</div>
			</div>
		</div>

		<!-- Method Specs -->
		<div class="font-mono-telemetry mt-2.5 space-y-1 text-[11px] text-slate-200">
			<div class="flex justify-between">
				<span class="text-slate-400">Method:</span>
				<span class="ml-2 truncate text-right text-white">{event.processing.method}</span>
			</div>
			{#if event.processing.threshold_db}
				<div class="flex justify-between">
					<span class="text-slate-400">Scene threshold:</span>
					<span class="font-bold text-neon-yellow">{event.processing.threshold_db} dB</span>
				</div>
			{/if}
			{#if event.processing.speckle_filter}
				<div class="flex justify-between">
					<span class="text-slate-400">Filter:</span>
					<span class="text-white">{event.processing.speckle_filter}</span>
				</div>
			{/if}
			{#if event.statistics_url}
				<div class="flex justify-between border-t border-slate-800/80 pt-1">
					<span class="text-slate-400">Pipeline Stats:</span>
					<a
						href={resolve('/data/[...path]', { path: `processed/${event.id}/statistics.json` })}
						target="_blank"
						class="brand-link-secondary flex items-center gap-1 text-[10px]"
					>
						<span>statistics.json</span>
						<ExternalLink class="h-3 w-3" />
					</a>
				</div>
			{/if}
		</div>

		{#if event.statistics?.water_loss_area_km2}
			<div
				class="mt-2.5 rounded border border-rocket-red/60 bg-martian-red/40 p-2.5 text-[11px] leading-relaxed text-white"
			>
				<div class="font-mono-telemetry flex items-center justify-between">
					<span class="font-bold text-neon-yellow">Apparent Water Loss:</span>
					<span class="font-bold text-white"
						>{event.statistics.water_loss_area_km2} km² ({event.statistics.water_loss_pixels?.toLocaleString()}
						cells)</span
					>
				</div>
				<p class="mt-1 text-[10px] text-slate-200">
					Fewer pixels met the water threshold on the second date. Surface roughness is a possible
					cause; independent evidence is needed to establish a water-level change.
				</p>
			</div>
		{/if}

		{#if event.statistics}
			<dl class="mt-3 grid grid-cols-2 gap-2 text-[11px]">
				<div>
					<dt class="text-slate-400">Baseline classified water</dt>
					<dd class="font-mono font-bold text-white">
						{event.statistics.baseline_water_area_km2} km²
					</dd>
				</div>
				<div>
					<dt class="text-slate-400">Repeat classified water</dt>
					<dd class="font-mono font-bold text-white">
						{event.statistics.post_event_water_area_km2} km²
					</dd>
				</div>
			</dl>
		{/if}
		<div class="mt-3 flex flex-wrap gap-3 text-[11px]">
			<a
				href={resolve('/api/events/[id]', { id: event.id })}
				download={`${event.id}.json`}
				class="brand-link-secondary">Download observation record</a
			>
			<a
				href={resolve('/api/events/[id]/geometry', { id: event.id })}
				download={`${event.id}.geojson`}
				class="brand-link-secondary">Download candidate polygons</a
			>
		</div>

		<!-- Limitations Trigger (Martian Red + White AAA 9.38:1 per Brand Guide p. 9) -->
		<button
			type="button"
			onclick={() => {
				appState.isLimitationsModalOpen = true;
			}}
			class="mt-3 flex w-full items-center justify-center gap-1.5 rounded border border-rocket-red/80 bg-martian-red py-1.5 text-[11px] font-bold tracking-wider text-white uppercase transition-colors hover:bg-rocket-red"
		>
			<AlertTriangle class="h-4 w-4 text-neon-yellow" />
			<span>View Scientific Limitations & Failure Modes</span>
		</button>
	</section>

	<!-- TIER 3: OBSERVATION SUMMARY (Brand Guide p. 12: Electric Blue content section) -->
	<section
		class="brand-pattern-orbits rounded-lg border border-yonder-400/50 bg-electric-blue/35 p-3.5 shadow-lg backdrop-blur-sm"
		aria-labelledby="tier3-heading"
	>
		<div class="flex items-center justify-between border-b border-yonder-700/70 pb-2">
			<div class="flex items-center gap-2">
				<span
					class="flex h-6 w-6 items-center justify-center rounded bg-deep-blue text-neon-yellow"
				>
					<Bot class="h-4 w-4" />
				</span>
				<h2 id="tier3-heading" class="text-[11px] font-bold tracking-wider text-white uppercase">
					Tier 3: Observation Summary
				</h2>
			</div>
			<div class="flex items-center gap-1.5">
				<span
					class="flex items-center gap-1 rounded border border-neon-yellow/50 bg-deep-blue px-1.5 py-0.5 font-mono text-[10px] font-bold text-neon-yellow"
				>
					<CheckCircle2 class="h-3 w-3 text-neon-yellow" />
					Template
				</span>
				<button
					type="button"
					onclick={refreshExplanation}
					disabled={isAiLoading}
					class="text-white hover:text-neon-yellow disabled:opacity-50"
					title="Refresh observation summary"
					aria-label="Refresh observation summary"
				>
					<RefreshCw class="h-4 w-4 {isAiLoading ? 'animate-spin' : ''}" />
				</button>
			</div>
		</div>

		<div class="mt-2.5 text-xs leading-relaxed text-white">
			{#if isAiLoading}
				<div class="flex items-center gap-2 py-3 text-xs text-neon-yellow">
					<RefreshCw class="h-4 w-4 animate-spin" />
					<span>Loading the observation summary...</span>
				</div>
			{:else}
				<p class="break-words">{aiExplanation}</p>
			{/if}
		</div>

		<div
			class="mt-2.5 flex items-center gap-1.5 rounded border border-yonder-700/70 bg-deep-blue/90 px-2.5 py-1.5 text-[10px] text-slate-200"
		>
			<Info class="h-4 w-4 shrink-0 text-neon-yellow" />
			<span
				>Prepared from the observation record using a deterministic template. No live AI model is
				used.</span
			>
		</div>
	</section>
</div>
