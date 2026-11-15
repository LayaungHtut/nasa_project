<script lang="ts">
	import { appState } from '$lib/stores/appState.svelte';
	let event = $derived(appState.selectedEvent);
	let threshold = $derived(event.processing.threshold_db);
	let mode = $derived(appState.activeLayer);
	let range = $derived(event.tiles.display_range_db ?? [-25, -5]);
</script>

<div
	class="rounded-lg border border-yonder-500/40 bg-deep-blue/95 p-3 text-xs text-slate-200 shadow-xl backdrop-blur-md"
>
	<p class="font-semibold text-white">Radar backscatter preview</p>
	<div class="mt-2 flex justify-between gap-6 text-[10px] text-slate-300">
		<span>{range[0]} dB or lower</span><span>{range[1]} dB or higher</span>
	</div>
	<div class="mt-1 h-2 rounded bg-gradient-to-r from-black to-white"></div>
	<p class="mt-2 max-w-60 text-[10px] leading-relaxed text-slate-300">
		Both dates use the same grayscale range. Dark pixels have lower radar return; darkness alone
		does not identify water.
	</p>
	{#if threshold !== undefined}<p class="mt-2 font-mono text-neon-yellow">
			Scene threshold: {threshold} dB
		</p>{/if}
	{#if mode === 'change_mask'}
		<p class="mt-2 flex items-center gap-2 text-white">
			<span class="h-3 w-3 rounded-sm bg-yonder-400"></span>New-inundation candidates
		</p>
	{/if}
</div>
