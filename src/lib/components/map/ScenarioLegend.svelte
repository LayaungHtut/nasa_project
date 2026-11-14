<script lang="ts">
	import { appState } from '$lib/stores/appState.svelte';

	let s = $derived(appState.scenario);
	let layer = $derived(appState.layer);
	let vmax = $derived(s.module === 'mining' ? 5 : 3);
	let items = $derived(
		s.module === 'mining'
			? [
					{ color: '#eafe07', label: 'Permitted concession boundary', line: true },
					{ color: '#3987e5', label: 'New clearing inside the permit' },
					{ color: '#d95926', label: 'New clearing outside the permit' }
				]
			: [
					{ color: '#d95926', label: 'Detected landslide' },
					{ color: '#3987e5', label: 'Water ponding behind the debris' },
					{ color: '#199e70', label: 'New river channel / course' },
					{ color: '#8a94a8', label: 'Abandoned channel' },
					{ color: '#d3dcee', label: 'River course on the baseline pass', line: true }
				]
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
		<div class="font-bold text-white">Ground motion since the first pass (line of sight)</div>
		<div
			class="mt-1 h-2 rounded"
			style="background: linear-gradient(90deg, #d95926, #e9a07f, #8a94a8, #8fb8ee, #3987e5)"
		></div>
		<div class="flex justify-between text-[10px] text-slate-300">
			<span>−{vmax} cm away</span><span>+{vmax} cm toward</span>
		</div>
		<div class="text-[10px] text-slate-400">Blank where coherence &lt; 0.3: phase unreadable</div>
	{:else}
		<div class="font-bold text-white">
			Radar backscatter, {s.sensor.polarization} · {s.sensor.pixel_m} m pixels
		</div>
		<div class="mt-1 h-2 rounded" style="background: linear-gradient(90deg, #000, #fff)"></div>
		<div class="flex justify-between text-[10px] text-slate-300">
			<span>−28 dB water</span><span>−2 dB vegetation</span>
		</div>
	{/if}

	{#if appState.showOverlays}
		<ul class="mt-2 space-y-0.5 border-t border-yonder-500/30 pt-1.5">
			{#each items as item (item.label)}
				<li class="flex items-center gap-2">
					{#if item.line}
						<span class="h-0 w-3 shrink-0 border-t-2 border-dashed" style:border-color={item.color}
						></span>
					{:else}
						<span
							class="h-2.5 w-3 shrink-0 rounded-sm border"
							style:background-color="{item.color}66"
							style:border-color={item.color}
						></span>
					{/if}
					<span>{item.label}</span>
				</li>
			{/each}
		</ul>
	{/if}
</div>
