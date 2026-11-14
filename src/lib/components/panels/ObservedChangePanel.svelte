<script lang="ts">
	import { appState } from '$lib/stores/appState.svelte';
	import { ha, observedStatus, shortDate } from '$lib/data/scenarios';
	import type { ObservedScenario } from '$lib/types/scenario';
	import { Satellite, Info, Scale, ExternalLink } from 'lucide-svelte';

	let { scenario }: { scenario: ObservedScenario } = $props();
	let i = $derived(appState.epochIndex);
	let m = $derived(scenario.metrics[i]);
	let st = $derived(observedStatus(scenario, i));
	let epoch = $derived(scenario.epochs[i]);
	let t = $derived(scenario.thresholds);
	let u = $derived(scenario.uncertainty);
	let p = $derived(scenario.provenance);
	let base = $derived(scenario.epochs.slice(0, 2).map((e) => shortDate(e.date)));

	const heading = {
		change: 'Surface change detected',
		within_noise: 'No change beyond noise',
		awaiting: 'Awaiting a second pass',
		baseline: 'Baseline pass'
	};
	const pct = (r: number) => `${(r * 100).toFixed(r < 0.01 ? 2 : 1)}%`;
</script>

<section
	class="rounded-lg border p-3.5 text-[11px] leading-relaxed text-white shadow-lg {st.stage ===
	'change'
		? 'border-neon-yellow/80 bg-deep-blue'
		: 'border-yonder-500/50 bg-electric-blue/35'}"
	role="status"
	aria-live="polite"
>
	<div class="flex items-start gap-2.5">
		<Satellite class="mt-0.5 h-5 w-5 shrink-0 text-neon-yellow" />
		<div class="min-w-0">
			<div class="flex flex-wrap items-center gap-2">
				<h3 class="text-sm font-black tracking-wide uppercase">{heading[st.stage]}</h3>
				<span
					class="rounded border border-neon-yellow/70 px-1.5 py-0.5 font-mono text-[9px] font-bold tracking-wider text-neon-yellow uppercase"
				>
					Real NISAR data
				</span>
			</div>
			<p class="mt-0.5 text-slate-100">
				Track {p.track}
				{p.orbit_direction} · Frame {p.frame} · pass of {shortDate(epoch.date)} (Day
				{epoch.day})
			</p>
			<p class="font-mono text-[9px] break-all text-slate-300" title="GCOV granule of this pass">
				{epoch.granule_id}
			</p>
		</div>
	</div>

	{#if st.stage === 'baseline'}
		<p class="mt-2 text-slate-100">
			The two baseline passes ({base.join(' and ')}) are averaged into the reference image that
			later passes are compared with.
		</p>
	{:else if st.stage === 'awaiting'}
		<p class="mt-2 text-slate-100">
			A change must appear on two consecutive passes to count, so this pass is only compared once
			the next one arrives.
		</p>
	{:else if m}
		<ul class="mt-2 list-disc space-y-1 pl-5 text-slate-100">
			<li>
				{ha(m.disturbed_m2)} of formerly vegetated ground lost more than {t.drop_db} dB of HV return{m.drop_db_median
					? ` (median drop ${m.drop_db_median} dB)`
					: ''}, in {m.clusters} patches of at least {ha(t.min_cluster_m2)}, confirmed on two
				consecutive passes.
			</li>
			<li>{ha(m.new_water_m2)} became open water (HH below {t.water_db} dB).</li>
			{#if m.coherence_disturbed !== null && m.coherence_reference !== null && epoch.coherence_pair}
				<li>
					InSAR coherence {shortDate(epoch.coherence_pair[0])} → {shortDate(
						epoch.coherence_pair[1]
					)}:
					{m.coherence_disturbed.toFixed(2)} over the changed ground versus {m.coherence_reference.toFixed(
						2
					)} on stable vegetated ground.
				</li>
			{/if}
			<li>
				The null test could produce up to {ha(m.expected_false_upper_m2)} of false change by itself (about
				{ha(m.expected_false_m2)} if errors on two passes are independent).
			</li>
		</ul>
	{/if}
</section>

<section
	class="rounded-lg border border-yonder-500/40 bg-deep-blue/95 p-3.5 text-[11px] leading-relaxed text-slate-200 shadow-lg"
>
	<h3 class="flex items-center gap-2 text-[11px] font-bold tracking-wider text-white uppercase">
		<Scale class="h-4 w-4 text-neon-yellow" />
		<span>What this does not show</span>
	</h3>
	<ul class="mt-1.5 list-disc space-y-1 pl-4">
		<li>
			<strong class="text-white">Not proof of mining.</strong> The radar sees vegetation loss, bare ground
			and water. Excavation is the likely cause in a jade-mining district, but mine-waste slides, landslides
			and monsoon moisture can look similar.
		</li>
		<li>
			<strong class="text-white">Nothing about legality.</strong> No verified concession boundaries were
			available, so permit compliance is not assessed. The permit-check module shows how that check works,
			on simulated data.
		</li>
		<li>
			<strong class="text-white">Not elevation loss.</strong> No InSAR deformation is shown here: dug
			ground decorrelates within 12 days, and atmospheric and ionospheric corrections were not validated
			for this frame.
		</li>
	</ul>
</section>

<section
	class="rounded-lg border border-yonder-500/40 bg-deep-blue/95 p-3.5 text-[11px] text-slate-200 shadow-lg"
>
	<h3 class="text-[11px] font-bold tracking-wider text-white uppercase">Pass by pass</h3>
	<table class="font-mono-telemetry mt-2 w-full text-left text-[10px]">
		<thead class="text-slate-400">
			<tr>
				<th class="py-0.5 font-normal">Pass</th>
				<th class="py-0.5 text-right font-normal">Changed</th>
				<th class="py-0.5 text-right font-normal">New water</th>
				<th class="py-0.5 text-right font-normal">Coherence</th>
			</tr>
		</thead>
		<tbody>
			{#each scenario.epochs as e, k (e.date)}
				{@const mk = scenario.metrics[k]}
				<tr class={k === i ? 'text-neon-yellow' : ''}>
					<td class="py-0.5">
						<button
							type="button"
							class="underline-offset-2 hover:underline"
							onclick={() => (appState.epochIndex = k)}
						>
							{shortDate(e.date)}
						</button>
					</td>
					<td class="py-0.5 text-right">{mk ? ha(mk.disturbed_m2) : k < 2 ? 'baseline' : '—'}</td>
					<td class="py-0.5 text-right">{mk ? ha(mk.new_water_m2) : ''}</td>
					<td class="py-0.5 text-right">{mk?.coherence_disturbed?.toFixed(2) ?? ''}</td>
				</tr>
			{/each}
		</tbody>
	</table>
</section>

<section
	class="rounded-lg border border-yonder-500/40 bg-deep-blue/95 p-3.5 text-[11px] leading-relaxed text-slate-200 shadow-lg"
>
	<h3 class="flex items-center gap-2 text-[11px] font-bold tracking-wider text-white uppercase">
		<Info class="h-4 w-4 text-neon-yellow" />
		<span>Uncertainty and limits</span>
	</h3>
	<p class="mt-1.5">
		{u.null_test} False-alarm rate on vegetated ground: {pct(u.single_pass_false_rate)} for one pass,
		about {pct(u.confirmed_false_rate)} when two consecutive passes must agree.
	</p>
	<ul class="mt-1.5 list-disc space-y-1 pl-4">
		{#each u.notes as n (n)}<li>{n}</li>{/each}
	</ul>
	<details class="mt-2">
		<summary class="cursor-pointer font-bold text-white">
			Data used: {p.gcov_granules.length} GCOV passes, {p.gunw_granules.length} GUNW pairs; {p
				.excluded.length} passes excluded
		</summary>
		<ul class="mt-1.5 space-y-1">
			{#each p.excluded as x (x.granule_id)}
				<li><span class="font-mono text-slate-300">{x.date}</span> excluded: {x.reason}.</li>
			{/each}
		</ul>
		<ul class="mt-1.5 space-y-0.5 font-mono text-[9px] break-all text-slate-300">
			{#each [...p.gcov_granules, ...p.gunw_granules] as g (g)}<li>{g}</li>{/each}
		</ul>
		<p class="mt-1.5">
			Search any ID in
			<a
				href="https://search.asf.alaska.edu/"
				target="_blank"
				rel="noopener noreferrer"
				class="brand-link-secondary inline-flex items-center gap-1"
				>ASF Vertex<ExternalLink class="h-3 w-3" /></a
			>
			to inspect or download it.
		</p>
	</details>
</section>
