<script lang="ts">
	import { appState, type ScenarioLayer } from '$lib/stores/appState.svelte';
	import { Layers, SplitSquareHorizontal, Waves, Activity, ChevronDown } from 'lucide-svelte';

	const layerButtons: Array<{ id: ScenarioLayer; label: string; icon: typeof Layers }> = [
		{ id: 'sar', label: 'Radar pass', icon: Layers },
		{ id: 'compare', label: 'Before / after', icon: SplitSquareHorizontal },
		{ id: 'coherence', label: 'InSAR coherence', icon: Waves },
		{ id: 'deformation', label: 'InSAR deformation', icon: Activity }
	];
</script>

<details
	open
	class="group absolute top-3 left-3 z-30 max-w-[calc(100%-4.5rem)] rounded-lg border border-yonder-500/40 bg-deep-blue/95 p-1.5 shadow-xl backdrop-blur-md"
>
	<summary
		class="flex cursor-pointer list-none items-center gap-2 rounded-md px-2 py-1.5 text-[11px] font-bold tracking-wider text-white uppercase hover:bg-electric-blue/30 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-neon-yellow [&::-webkit-details-marker]:hidden"
	>
		<Layers class="h-3.5 w-3.5 shrink-0 text-neon-yellow" />
		<span class="shrink-0">Map controls</span>
		<span
			class="max-w-40 truncate font-normal tracking-normal text-slate-300 normal-case group-open:hidden"
		>
			{layerButtons.find((button) => button.id === appState.layer)?.label}
		</span>
		<ChevronDown
			class="ml-auto h-3.5 w-3.5 shrink-0 text-neon-yellow transition-transform group-open:rotate-180"
		/>
	</summary>
	<div class="mt-1 flex gap-1 overflow-x-auto sm:flex-wrap" role="group" aria-label="Map layer">
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
		class="mx-2 mt-1 mb-0.5 hidden rounded border border-neon-yellow/60 bg-electric-blue/50 px-1.5 py-0.5 font-mono text-[9px] font-bold tracking-wider text-neon-yellow uppercase sm:inline-block"
	>
		Real NISAR observations · ASF DAAC
	</div>
</details>
