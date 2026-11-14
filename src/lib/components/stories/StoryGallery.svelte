<script lang="ts">
	import { formatAcquisitionDate } from '$lib/data/presentation';
	import { appState } from '$lib/stores/appState.svelte';
	import { MapPin, Calendar, ArrowRight } from 'lucide-svelte';

	let { onSelectEvent }: { onSelectEvent?: (id: string) => void } = $props();

	function handleSelect(id: string) {
		appState.selectEvent(id);
		if (onSelectEvent) onSelectEvent(id);
	}
</script>

<div class="grid grid-cols-1 gap-4 md:grid-cols-3">
	{#each appState.events as evt (evt.id)}
		{@const isSelected = appState.selectedEventId === evt.id}
		<div
			class="brand-pattern-voronoi group relative flex flex-col justify-between rounded-xl border transition-all duration-200 {isSelected
				? 'border-neon-yellow/80 bg-deep-blue shadow-[0_0_25px_rgba(46,150,245,0.3)]'
				: 'border-yonder-500/40 bg-deep-blue/90 hover:border-yonder-400 hover:bg-deep-blue'}"
		>
			<div class="p-4 sm:p-5">
				<!-- Top row: Product badge + data status + location -->
				<div class="flex items-center justify-between gap-2 text-xs">
					<div class="flex items-center gap-1.5">
						<span
							class="rounded border border-yonder-500/50 bg-electric-blue/50 px-2 py-0.5 font-mono text-[11px] font-semibold text-white"
						>
							NISAR {evt.source_products[0]?.product}
						</span>
						{#if evt.data_status === 'REAL'}
							<span
								class="rounded border border-neon-yellow/70 bg-deep-blue px-1.5 py-0.5 font-mono text-[9px] font-bold text-neon-yellow"
							>
								REAL
							</span>
						{:else}
							<span
								class="rounded border border-rocket-red bg-martian-red px-1.5 py-0.5 font-mono text-[9px] font-bold text-white"
							>
								SYNTHETIC
							</span>
						{/if}
					</div>
					<div class="flex items-center gap-1 text-slate-300">
						<MapPin class="h-3 w-3 text-neon-yellow" />
						<span class="max-w-[120px] truncate">{evt.location.country}</span>
					</div>
				</div>

				<!-- Headline & Subtitle -->
				<h3
					class="mt-3 text-sm font-bold text-white transition-colors group-hover:text-neon-yellow"
				>
					{evt.title}
				</h3>
				<p class="mt-1 line-clamp-2 text-xs leading-relaxed text-slate-300">
					{evt.subtitle}
				</p>

				<!-- Metrics strip -->
				<div class="mt-4 grid grid-cols-2 gap-2 border-t border-yonder-500/30 pt-3">
					<div>
						<span class="block font-mono text-[10px] text-slate-300 uppercase">
							{evt.phenomenon === 'surface_deformation' ? 'Strain Zone' : 'Candidate Area'}
						</span>
						<span class="font-mono-telemetry text-sm font-extrabold text-yonder-400">
							{evt.results.change_area_km2} km²
						</span>
					</div>
					<div>
						<span class="block font-mono text-[10px] text-slate-300 uppercase">
							Detection Score
						</span>
						<span class="font-mono-telemetry text-sm font-extrabold text-neon-yellow">
							{evt.results.confidence.toFixed(3)} / 1
						</span>
					</div>
				</div>

				<!-- Observation Dates -->
				<div class="font-mono-telemetry mt-3 flex items-center gap-1.5 text-[11px] text-slate-300">
					<Calendar class="h-3 w-3 text-yonder-400" />
					<span>
						{formatAcquisitionDate(evt.observation_dates.baseline)}
						→
						{formatAcquisitionDate(evt.observation_dates.post_event)}
					</span>
				</div>
			</div>

			<!-- Select CTA -->
			<div class="border-t border-yonder-500/30 bg-deep-blue/80 p-3">
				<button
					type="button"
					onclick={() => handleSelect(evt.id)}
					class="flex w-full items-center justify-center gap-1.5 rounded-md py-1.5 text-xs transition-all {isSelected
						? 'brand-btn-primary shadow-md'
						: 'border border-yonder-500/50 bg-electric-blue/40 font-bold tracking-wider text-white uppercase hover:border-neon-yellow hover:text-neon-yellow'}"
				>
					<span>{isSelected ? 'Currently Exploring' : 'Load Event on Map'}</span>
					<ArrowRight class="h-4 w-4" />
				</button>
			</div>
		</div>
	{/each}
</div>
