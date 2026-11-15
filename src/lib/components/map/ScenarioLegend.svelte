<script lang="ts">
	import { appState } from '$lib/stores/appState.svelte';

	let s = $derived(appState.scenario);
	let layer = $derived(appState.layer);
	let vmax = $derived(s.module === 'slope' ? s.thresholds.display_cm_yr : 0);
	let items = $derived(
		s.module === 'observed'
			? [
					{ color: '#d95926', label: 'Vegetation loss / new bare ground' },
					{ color: '#3987e5', label: 'New open water' }
				]
			: [{ color: '#199e70', label: 'Steep slope moving beyond noise (to check, not confirmed)' }]
	);
</script>

<div
	class="rounded-lg border border-yonder-500/40 bg-deep-blue/95 p-2.5 text-[11px] text-slate-200 shadow-xl backdrop-blur-md"
>
	{#if layer === 'coherence'}
		<div class="font-bold text-white">InSAR coherence (12-day pair)</div>
		<div
			class="mt-1 h-2 rounded"
			style="background: linear-gradient(90deg, #07173f, #0042a6, #3987e5, #cfe3fb)"
		></div>
		<div class="flex justify-between text-[10px] text-slate-300">
			<span>0 changed</span><span>1 unchanged</span>
		</div>
	{:else if layer === 'deformation'}
		<div class="font-bold text-white">Mean line-of-sight rate, pairs up to this date</div>
		<div
			class="mt-1 h-2 rounded"
			style="background: linear-gradient(90deg, #d95926, #e9a07f, #8a94a8, #8fb8ee, #3987e5)"
		></div>
		<div class="flex justify-between text-[10px] text-slate-300">
			<span>−{vmax} cm/yr away</span><span>+{vmax} cm/yr toward</span>
		</div>
		<div class="text-[10px] text-slate-400">
			Blank where fewer than 60% of those pairs could be read (coherence &lt; 0.3 or no unwrapped
			component)
		</div>
	{:else}
		<div class="font-bold text-white">Radar backscatter, HV · 20 m pixels</div>
		<div class="mt-1 h-2 rounded" style="background: linear-gradient(90deg, #000, #fff)"></div>
		<div class="flex justify-between text-[10px] text-slate-300">
			<span>−28 dB water</span><span>−2 dB vegetation</span>
		</div>
	{/if}

	{#if appState.showOverlays}
		<ul class="mt-2 space-y-0.5 border-t border-yonder-500/30 pt-1.5">
			{#each items as item (item.label)}
				<li class="flex items-center gap-2">
					<span
						class="h-2.5 w-3 shrink-0 rounded-sm border"
						style:background-color="{item.color}66"
						style:border-color={item.color}
					></span>
					<span>{item.label}</span>
				</li>
			{/each}
		</ul>
	{/if}
</div>
