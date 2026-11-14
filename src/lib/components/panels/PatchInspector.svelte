<script lang="ts">
	import { appState } from '$lib/stores/appState.svelte';
	import { ha, observedPatches, patchLabel, shortDate } from '$lib/data/scenarios';
	import type { ObservedScenario } from '$lib/types/scenario';
	import { MousePointerClick, X } from 'lucide-svelte';

	let { scenario }: { scenario: ObservedScenario } = $props();
	let i = $derived(appState.epochIndex);
	let patches = $derived(observedPatches(scenario, i));
	let p = $derived(appState.selectedPatch);
	let m = $derived(scenario.metrics[i]);
	let t = $derived(scenario.thresholds);
	const date = (k: number) => shortDate(scenario.epochs[k].date);
	// Same colours as the map overlays.
	const SWATCH = { disturbed: '#d95926', new_water: '#3987e5' };
	/** Water detections this close to the HH threshold are flagged as marginal. */
	const MARGINAL_DB = 1;
</script>

{#if patches.length}
	<section
		class="rounded-lg border border-yonder-500/40 bg-deep-blue/95 p-3.5 text-[11px] text-slate-200 shadow-lg"
		aria-labelledby="patches-heading"
	>
		<h3
			id="patches-heading"
			class="flex items-center gap-2 text-[11px] font-bold tracking-wider text-white uppercase"
		>
			<MousePointerClick class="h-4 w-4 text-neon-yellow" />
			<span>Detected patches on {date(i)}</span>
		</h3>
		<p class="mt-1 text-slate-300">Pick one here or click it on the map to inspect it.</p>
		<ul class="mt-2 grid grid-cols-1 gap-1.5 sm:grid-cols-2">
			{#each patches as x (x.patch_id)}
				{@const active = p?.patch_id === x.patch_id}
				<li>
					<button
						type="button"
						aria-pressed={active}
						onclick={() => appState.selectPatch(active ? null : x.patch_id)}
						class="flex w-full items-center gap-2 rounded-md border px-2 py-1.5 text-left transition-colors {active
							? 'border-neon-yellow/80 bg-electric-blue/60 text-white'
							: 'border-yonder-500/40 bg-electric-blue/20 text-slate-100 hover:border-yonder-300'}"
					>
						<span
							class="h-2.5 w-2.5 shrink-0 rounded-sm"
							style:background-color={SWATCH[x.kind]}
							aria-hidden="true"
						></span>
						<span class="min-w-0 flex-1 truncate">{patchLabel(x)}</span>
						<span class="font-mono text-[10px] text-slate-300">{ha(x.area_m2)}</span>
					</button>
				</li>
			{/each}
		</ul>
	</section>
{/if}

{#if p && m}
	{@const now = p.kind === 'disturbed' ? p.hv_db[i] : p.hh_db[i]}
	{@const margin = t.water_db - p.hh_db[i]}
	<section
		class="rounded-lg border border-neon-yellow/70 bg-deep-blue p-3.5 text-[11px] leading-relaxed text-slate-100 shadow-lg"
		aria-labelledby="patch-heading"
		aria-live="polite"
	>
		<div class="flex items-start justify-between gap-2">
			<div>
				<h3 id="patch-heading" class="text-sm font-black tracking-wide text-white uppercase">
					{patchLabel(p)}
				</h3>
				<p class="text-slate-300">
					{p.kind === 'disturbed' ? 'Vegetation loss / new bare ground' : 'New open water'} · confirmed
					{date(p.epoch)} · {p.centroid[1].toFixed(4)}°N, {p.centroid[0].toFixed(4)}°E
				</p>
			</div>
			<button
				type="button"
				onclick={() => appState.selectPatch(null)}
				class="rounded p-1 text-slate-300 hover:bg-electric-blue/40 hover:text-white"
				aria-label="Close patch details"
			>
				<X class="h-4 w-4" />
			</button>
		</div>

		<dl class="font-mono-telemetry mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-[10px]">
			<dt class="text-slate-400">Area</dt>
			<dd class="text-right text-white">{ha(p.area_m2)}</dd>
			{#if p.kind === 'disturbed'}
				<dt class="text-slate-400">HV baseline → now</dt>
				<dd class="text-right text-white">
					{p.baseline_db.toFixed(1)} → {now.toFixed(1)} dB
				</dd>
				<dt class="text-slate-400">Median drop</dt>
				<dd class="text-right text-white">
					{p.drop_db_median?.toFixed(1)} dB (rule ≥ {t.drop_db})
				</dd>
			{:else}
				<dt class="text-slate-400">HH baseline → now</dt>
				<dd class="text-right text-white">
					{p.baseline_db.toFixed(1)} → {now.toFixed(1)} dB
				</dd>
				<dt class="text-slate-400">Water threshold</dt>
				<dd class="text-right text-white">
					HH &lt; {t.water_db} dB ({margin.toFixed(1)} dB below)
				</dd>
			{/if}
			{#if p.coherence !== null && scenario.epochs[i].coherence_pair}
				{@const pair = scenario.epochs[i].coherence_pair!}
				<dt class="text-slate-400">Coherence {shortDate(pair[0])}→{shortDate(pair[1])}</dt>
				<dd class="text-right text-white">
					{p.coherence.toFixed(2)}{m.coherence_reference !== null
						? ` (stable ground ${m.coherence_reference.toFixed(2)})`
						: ''}
				</dd>
			{/if}
			<dt class="text-slate-400">Also confirmed on</dt>
			<dd class="text-right text-white">
				{p.seen_on
					.filter((k) => k !== p.epoch)
					.map(date)
					.join(', ') || 'no other pass'}
			</dd>
		</dl>

		<ul class="mt-2 list-disc space-y-1 pl-4 text-slate-200">
			{#if p.kind === 'disturbed'}
				<li>
					Surface change consistent with excavation or clearing. Mine-waste slides, landslides and
					soil-moisture change can look the same to the radar.
				</li>
			{:else}
				<li>
					Open water can be a flooded pit, a settling pond, a shifted river or seasonal flooding;
					the radar cannot tell which.
				</li>
				{#if margin < MARGINAL_DB}
					<li>
						<strong class="text-white">Marginal detection:</strong> HH is within {MARGINAL_DB} dB of the
						threshold, so speckle or wind on the water could tip it either way.
					</li>
				{/if}
			{/if}
			{#if p.kind === 'disturbed' && p.coherence !== null && p.coherence < t.coherence_low}
				<li>
					Coherence below {t.coherence_low} over this pair suggests the surface was reworked between its
					two passes.
				</li>
			{/if}
			<li>
				Patch medians after the per-pass reference offset; outlines can differ from pass to pass.
			</li>
		</ul>
	</section>
{/if}
