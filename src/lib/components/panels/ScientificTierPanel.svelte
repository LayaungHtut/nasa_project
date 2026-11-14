<script lang="ts">
	import { appState } from '$lib/stores/appState.svelte';
	import { api } from '$lib/api/client';
	import { resolve } from '$app/paths';
	import { getSensitivityForEvent, TESTED_THRESHOLDS_DB } from '$lib/data/sensitivity';
	import {
		Satellite,
		Cpu,
		Bot,
		AlertTriangle,
		ExternalLink,
		Info,
		CheckCircle2,
		RefreshCw,
		Sliders
	} from 'lucide-svelte';

	let event = $derived(appState.selectedEvent);
	let sensitivityPoints = $derived(getSensitivityForEvent(event.id));
	let selectedFilterSize = $state<3 | 5>(3);
	let selectedThresholdIndex = $state<number>(3); // Default to index 3 (-9.54 dB served)
	let activeSensitivity = $derived(
		sensitivityPoints.find(
			(p) =>
				p.filter_size === selectedFilterSize &&
				p.threshold_db === TESTED_THRESHOLDS_DB[selectedThresholdIndex]
		)
	);
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

		{#if event.id === 'yangon-track40-frame10'}
			<div
				class="mt-3 rounded-lg border border-yonder-400/50 bg-electric-blue/35 p-3 text-[11px] leading-relaxed text-white"
			>
				<strong class="text-neon-yellow">Evidence status: unconfirmed water-change candidate</strong
				>
				<p class="mt-1">
					The recorded sensitivity sweep found that candidate area varies substantially with the
					threshold and filter window. The displayed area is one configuration's estimate, not a
					precise measurement of flooding.
				</p>
				<p class="mt-2">
					<strong>What to do next:</strong> inspect the dated optical comparison below, seek reservoir
					records, and check rainfall and wind conditions on both acquisition dates.
				</p>
			</div>
		{/if}

		{#if activeSensitivity}
			<section
				class="mt-3 rounded-lg border border-yonder-500/40 bg-slate-900/90 p-3 text-[11px] leading-relaxed"
				aria-labelledby="sensitivity-explorer-heading"
			>
				<div class="flex items-center justify-between gap-2">
					<h3
						id="sensitivity-explorer-heading"
						class="flex items-center gap-1.5 font-semibold text-white"
					>
						<Sliders class="h-4 w-4 text-neon-yellow" />
						<span>Interactive Parameter Sensitivity Sweep</span>
					</h3>
					{#if activeSensitivity.is_served}
						<span
							class="rounded border border-neon-yellow/60 bg-electric-blue/50 px-1.5 py-0.5 font-mono text-[9px] font-bold text-neon-yellow uppercase"
						>
							Served Config
						</span>
					{:else}
						<button
							type="button"
							onclick={() => {
								selectedFilterSize = 3;
								selectedThresholdIndex = 3;
							}}
							class="rounded border border-yonder-500/50 bg-deep-blue px-1.5 py-0.5 font-mono text-[9px] font-bold text-neon-yellow hover:border-neon-yellow"
						>
							Reset to Served (-9.54 dB, 3×3)
						</button>
					{/if}
				</div>
				<p class="mt-1 text-[10px] text-slate-300">
					Explore all 14 real-raster pipeline runs from Investigation 2 to see how threshold and
					speckle filter choices change the areas.
				</p>

				<!-- Filter Window Toggle + Threshold Slider -->
				<div class="mt-2.5 space-y-2.5 rounded border border-slate-800 bg-deep-blue p-2.5">
					<div class="flex items-center justify-between">
						<span class="text-[10px] text-slate-300">Lee Speckle Filter Window:</span>
						<div
							class="inline-flex rounded border border-slate-700 bg-slate-900 p-0.5 font-mono text-[10px]"
						>
							<button
								type="button"
								onclick={() => (selectedFilterSize = 3)}
								aria-pressed={selectedFilterSize === 3}
								class="rounded px-2 py-0.5 transition-colors {selectedFilterSize === 3
									? 'bg-neon-yellow font-bold text-deep-blue'
									: 'text-slate-300 hover:text-white'}"
							>
								3×3 (Served)
							</button>
							<button
								type="button"
								onclick={() => (selectedFilterSize = 5)}
								aria-pressed={selectedFilterSize === 5}
								class="rounded px-2 py-0.5 transition-colors {selectedFilterSize === 5
									? 'bg-neon-yellow font-bold text-deep-blue'
									: 'text-slate-300 hover:text-white'}"
							>
								5×5
							</button>
						</div>
					</div>

					<div>
						<div class="flex items-center justify-between text-[10px]">
							<label for="sensitivity-threshold-slider" class="text-slate-300">
								Water Cutoff Threshold:
							</label>
							<span class="font-mono font-bold text-neon-yellow">
								{activeSensitivity.threshold_db.toFixed(2)} dB
							</span>
						</div>
						<input
							id="sensitivity-threshold-slider"
							type="range"
							min="0"
							max={TESTED_THRESHOLDS_DB.length - 1}
							step="1"
							bind:value={selectedThresholdIndex}
							aria-valuetext={`${activeSensitivity.threshold_db} dB`}
							class="mt-1.5 h-1.5 w-full cursor-pointer appearance-none rounded-lg bg-slate-800 accent-neon-yellow"
						/>
						<div class="mt-1 flex justify-between font-mono text-[9px] text-slate-400">
							{#each TESTED_THRESHOLDS_DB as t (t)}
								<span class={t === -9.54 ? 'font-bold text-neon-yellow' : ''}>
									{t === -9.54 ? '-9.54*' : t.toFixed(0)}
								</span>
							{/each}
						</div>
					</div>
				</div>

				<!-- Resulting Areas for Selected Parameter Combination -->
				<div class="mt-2.5 grid grid-cols-2 gap-2 font-mono text-[10px]">
					<div class="rounded border border-slate-800 bg-deep-blue p-2">
						<span class="block font-sans text-[9px] text-slate-300 uppercase">
							New Inundation Candidate
						</span>
						<span class="text-sm font-bold text-yonder-400">
							{activeSensitivity.new_inundation_km2.toFixed(3)} km²
						</span>
						<div class="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
							<div
								class="h-full bg-yonder-400 transition-all"
								style:width={`${Math.min(100, (activeSensitivity.new_inundation_km2 / 1.508) * 100)}%`}
							></div>
						</div>
					</div>
					<div class="rounded border border-slate-800 bg-deep-blue p-2">
						<span class="block font-sans text-[9px] text-slate-300 uppercase">
							Apparent Water Loss
						</span>
						<span class="text-sm font-bold text-neon-yellow">
							{activeSensitivity.water_loss_km2.toFixed(3)} km²
						</span>
						<div class="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
							<div
								class="h-full bg-neon-yellow transition-all"
								style:width={`${Math.min(100, (activeSensitivity.water_loss_km2 / 18.217) * 100)}%`}
							></div>
						</div>
					</div>
					<div class="rounded border border-slate-800/80 bg-deep-blue/80 px-2 py-1.5">
						<span class="block font-sans text-[9px] text-slate-400">Baseline water (Aug 27)</span>
						<span class="text-white">{activeSensitivity.baseline_water_km2.toFixed(3)} km²</span>
					</div>
					<div class="rounded border border-slate-800/80 bg-deep-blue/80 px-2 py-1.5">
						<span class="block font-sans text-[9px] text-slate-400">Repeat water (Sep 8)</span>
						<span class="text-white">{activeSensitivity.post_water_km2.toFixed(3)} km²</span>
					</div>
				</div>
			</section>
		{/if}

		{#if event.independent_validation}
			{@const validation = event.independent_validation}
			{@const pair = validation.exploratory}
			<section
				class="mt-3 rounded-lg border border-slate-700 bg-slate-900/80 p-3 text-[11px] leading-relaxed"
				aria-labelledby="optical-validation-heading"
			>
				<h3 id="optical-validation-heading" class="font-semibold text-white">
					Independent optical check
				</h3>
				<p class="mt-1 font-semibold text-neon-yellow">
					Check completed; water change remains unconfirmed.
				</p>
				<p class="mt-2 text-slate-200">
					Within ±{validation.primary_window_days} days of each radar date,
					{validation.primary_joint_clear_pixels}/{validation.candidate_pixels} candidate cells are clear
					in both optical scenes. Clouds prevent a close-date change check.
				</p>
				<p class="mt-2 text-slate-200">
					Wider ±{pair.window_days}-day check: {pair.baseline_date.slice(0, 10)}
					({pair.baseline_offset_days.toFixed(2)} days from baseline radar) and
					{pair.repeat_date.slice(0, 10)} (+{pair.repeat_offset_days.toFixed(2)} days from repeat radar).
				</p>
				<dl
					class="mt-2 grid grid-cols-3 gap-2 rounded border border-slate-800 bg-deep-blue p-2 text-center"
				>
					<div>
						<dt class="text-slate-300">Land → water</dt>
						<dd class="font-mono text-base font-bold text-yonder-400">
							{pair.land_to_water_pixels}
						</dd>
					</div>
					<div>
						<dt class="text-slate-300">Land → land</dt>
						<dd class="font-mono text-base font-bold text-white">{pair.land_to_land_pixels}</dd>
					</div>
					<div>
						<dt class="text-slate-300">Unknown</dt>
						<dd class="font-mono text-base font-bold text-neon-yellow">{pair.unknown_pixels}</dd>
					</div>
				</dl>
				<p class="mt-2 text-slate-300">
					Counts use the 10 m radar grid. Sentinel-2 classification is a 20 m reference, not field
					ground truth. Timing differences prevent confirmation of the radar-date change; land
					classifications at other times do not prove radar errors.
				</p>
				<div class="mt-2.5 flex flex-wrap gap-3 text-[11px]">
					<a
						href={resolve('/data/[...path]', { path: validation.figure_path })}
						target="_blank"
						rel="noreferrer"
						class="brand-link-secondary">View dated optical overlays</a
					>
					<a
						href={resolve('/data/[...path]', { path: validation.report_path })}
						download="hlawga-optical-validation.json"
						class="brand-link-secondary">Download validation evidence</a
					>
				</div>
			</section>
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
			{#if event.data_status === 'REAL' && event.timeseries}
				<a
					href={resolve('/api/events/[id]/report', { id: event.id })}
					download={`${event.id}-report.html`}
					class="brand-link-secondary">Download analysis report</a
				>
			{/if}
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
