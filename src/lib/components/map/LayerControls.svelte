<script lang="ts">
	import { appState, type LayerViewMode } from '$lib/stores/appState.svelte';
	import { Layers, Eye, Maximize2, Sparkles, SplitSquareVertical } from 'lucide-svelte';

	let { onResetCamera }: { onResetCamera?: () => void } = $props();

	const layers: Array<{ id: LayerViewMode; label: string; icon: typeof Layers; hint: string }> = [
		{
			id: 'compare',
			label: 'Swipe Compare',
			icon: SplitSquareVertical,
			hint: 'Interactive Before/After slider'
		},
		{
			id: 'baseline',
			label: 'Baseline SAR',
			icon: Layers,
			hint: 'First acquired radar observation'
		},
		{ id: 'post', label: 'Repeat SAR', icon: Layers, hint: 'Second acquired radar observation' },
		{
			id: 'change_mask',
			label: 'Change Candidates',
			icon: Sparkles,
			hint: 'Threshold-based candidates; not confirmed flooding'
		}
	];
</script>

<div
	class="flex flex-wrap items-center gap-1.5 rounded-lg border border-yonder-500/40 bg-deep-blue/95 p-1.5 shadow-xl backdrop-blur-md"
>
	<div class="flex flex-wrap items-center gap-1">
		{#each layers as layer (layer.id)}
			{@const Icon = layer.icon}
			<button
				type="button"
				onclick={() => {
					appState.activeLayer = layer.id;
					if (layer.id === 'baseline') appState.selectedObservationIndex = 0;
					if (layer.id === 'post') appState.selectedObservationIndex = 1;
				}}
				title={layer.hint}
				aria-label={layer.label}
				aria-pressed={appState.activeLayer === layer.id}
				class="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-bold tracking-wide uppercase transition-all {appState.activeLayer ===
				layer.id
					? 'border border-neon-yellow/70 bg-electric-blue/70 text-neon-yellow shadow-[0_0_10px_rgba(46,150,245,0.25)]'
					: 'border border-transparent text-slate-300 hover:bg-electric-blue/30 hover:text-white'}"
			>
				<Icon class="h-4 w-4" />
				<span class="hidden sm:inline">{layer.label}</span>
			</button>
		{/each}
	</div>

	<div class="mx-1 hidden h-4 w-[1px] bg-yonder-500/30 md:block"></div>

	<!-- Opacity slider -->
	<div class="hidden items-center gap-2 px-2 text-xs text-slate-300 lg:flex">
		<Eye class="h-4 w-4 text-yonder-400" />
		<input
			type="range"
			min="0.2"
			max="1.0"
			step="0.05"
			bind:value={appState.opacity}
			class="h-1.5 w-16 cursor-pointer appearance-none rounded-lg bg-electric-blue/50 accent-neon-yellow"
			title={`Layer Opacity: ${(appState.opacity * 100).toFixed(0)}%`}
		/>
		<span class="font-mono-telemetry w-7 text-[11px] text-white">
			{(appState.opacity * 100).toFixed(0)}%
		</span>
	</div>

	<!-- Reset camera button -->
	{#if onResetCamera}
		<button
			type="button"
			onclick={onResetCamera}
			title="Recenter Camera on Event AOI"
			class="rounded-md border border-yonder-500/40 bg-electric-blue/30 p-1.5 text-slate-200 transition-colors hover:border-neon-yellow hover:text-neon-yellow"
		>
			<Maximize2 class="h-4 w-4" />
		</button>
	{/if}
</div>
