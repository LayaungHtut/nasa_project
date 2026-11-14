<script lang="ts">
	import { appState } from '$lib/stores/appState.svelte';
	import { Lightbulb, Eye } from 'lucide-svelte';
	import type { DriverHypothesis } from '$lib/types/api';

	let drivers = $derived(appState.selectedEvent.drivers ?? []);

	const badge: Record<DriverHypothesis['support'], string> = {
		'best supported': 'border-neon-yellow/70 bg-deep-blue text-neon-yellow',
		possible: 'border-yonder-500/60 bg-electric-blue/50 text-white',
		'weakly supported': 'border-yonder-500/30 bg-deep-blue/80 text-slate-300'
	};

	function inspectHypothesisOnMap(id: string) {
		appState.polarization = 'HH';
		if (id === 'paddy-growth') {
			appState.activeLayer = 'difference';
		} else if (id === 'edge-inundation') {
			appState.activeLayer = 'change_mask';
		} else {
			appState.activeLayer = 'compare';
			appState.sliderPosition = 50;
		}
	}

	function mapActionLabel(id: string): string {
		if (id === 'paddy-growth') return 'Show HH Change Map (brightening paddy belt)';
		if (id === 'edge-inundation') return 'Show Shoreline Change Candidates';
		return 'Compare Before / After HH on Reservoir';
	}
</script>

{#if drivers.length}
	<section
		class="brand-pattern-waves rounded-lg border border-yonder-500/40 bg-deep-blue/95 p-3.5 text-[11px] leading-relaxed shadow-lg"
		aria-labelledby="drivers-heading"
	>
		<h2
			id="drivers-heading"
			class="flex items-center gap-2 text-[11px] font-bold tracking-wider text-white uppercase"
		>
			<Lightbulb class="h-4 w-4 text-neon-yellow" />
			What could be driving the change?
		</h2>
		<p class="mt-2 text-slate-200">
			These are hypotheses, not findings. Each one lists the recorded evidence for and against it,
			and the observation that would settle it.
		</p>

		<div class="mt-3 space-y-2">
			{#each drivers as driver (driver.id)}
				<details class="group rounded border border-yonder-500/30 bg-deep-blue/90 p-2.5">
					<summary class="cursor-pointer list-none">
						<div class="flex items-start justify-between gap-2">
							<span class="font-semibold text-white">{driver.title}</span>
							<span
								class="shrink-0 rounded border px-1.5 py-0.5 font-mono text-[9px] font-bold uppercase {badge[
									driver.support
								]}">{driver.support}</span
							>
						</div>
						<span class="mt-0.5 block text-[10px] text-slate-300">Explains: {driver.explains}</span>
					</summary>
					<div class="mt-2 space-y-2 text-slate-200">
						<div>
							<p class="font-semibold text-neon-yellow">Evidence for</p>
							<ul class="mt-0.5 list-disc space-y-1 pl-4">
								{#each driver.evidence_for as item (item)}<li>{item}</li>{/each}
							</ul>
						</div>
						<div>
							<p class="font-semibold text-yonder-400">Evidence against or missing</p>
							<ul class="mt-0.5 list-disc space-y-1 pl-4">
								{#each driver.evidence_against as item (item)}<li>{item}</li>{/each}
							</ul>
						</div>
						<p>
							<span class="font-semibold text-neon-yellow">How to test:</span>
							{driver.how_to_test}
						</p>
						<button
							type="button"
							onclick={() => inspectHypothesisOnMap(driver.id)}
							class="mt-1.5 inline-flex items-center gap-1.5 rounded border border-yonder-500/50 bg-electric-blue/50 px-2.5 py-1 text-[10px] font-bold tracking-wide text-white uppercase transition-colors hover:border-neon-yellow hover:text-neon-yellow"
						>
							<Eye class="h-3 w-3 text-neon-yellow" />
							<span>{mapActionLabel(driver.id)}</span>
						</button>
					</div>
				</details>
			{/each}
		</div>
	</section>
{/if}
