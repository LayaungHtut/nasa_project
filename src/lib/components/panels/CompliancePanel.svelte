<script lang="ts">
	import { appState } from '$lib/stores/appState.svelte';
	import { compliance, ha, shortDate } from '$lib/data/scenarios';
	import type { MiningScenario } from '$lib/types/scenario';
	import { ShieldAlert, ShieldCheck, TriangleAlert } from 'lucide-svelte';

	let { scenario }: { scenario: MiningScenario } = $props();
	let i = $derived(appState.epochIndex);
	let m = $derived(scenario.metrics[i]);
	let c = $derived(compliance(scenario, i));
	let epoch = $derived(scenario.epochs[i]);
	let t = $derived(scenario.thresholds);

	const banner = {
		breach: 'border-rocket-red bg-martian-red',
		watch: 'border-neon-yellow/80 bg-deep-blue',
		compliant: 'border-yonder-500/50 bg-electric-blue/35'
	};
</script>

<section
	class="rounded-lg border p-3.5 text-[11px] leading-relaxed text-white shadow-lg {banner[c.level]}"
	role={c.level === 'breach' ? 'alert' : 'status'}
	aria-live="polite"
>
	<div class="flex items-start gap-2.5">
		{#if c.level === 'breach'}
			<ShieldAlert class="mt-0.5 h-5 w-5 shrink-0" />
		{:else if c.level === 'watch'}
			<TriangleAlert class="mt-0.5 h-5 w-5 shrink-0 text-neon-yellow" />
		{:else}
			<ShieldCheck class="mt-0.5 h-5 w-5 shrink-0 text-yonder-300" />
		{/if}
		<div class="min-w-0">
			<div class="flex flex-wrap items-center gap-2">
				<h3 class="text-sm font-black tracking-wide uppercase">
					{c.level === 'breach'
						? 'Compliance Breach Alert'
						: c.level === 'watch'
							? 'Compliance Watch'
							: 'Within permit'}
				</h3>
				<span
					class="rounded border border-white/60 px-1.5 py-0.5 font-mono text-[9px] font-bold tracking-wider uppercase"
				>
					Simulated
				</span>
			</div>
			<p class="mt-0.5 text-slate-100">
				{scenario.permit.permit_id} · {scenario.permit.operator} · pass of {shortDate(epoch.date)} (Day
				{epoch.day})
			</p>
		</div>
	</div>

	{#if c.reasons.length}
		<ul class="mt-2 list-disc space-y-1 pl-5 text-slate-100">
			{#each c.reasons as r (r)}<li>{r}.</li>{/each}
		</ul>
	{:else}
		<p class="mt-2 text-slate-100">
			All new clearing on this pass lies inside the permit (allowing a {t.tolerance_m} m band for geolocation
			error and speckle).
		</p>
	{/if}

	{#if c.level === 'breach'}
		<p class="mt-2 rounded border border-white/40 bg-deep-blue/60 p-2">
			<strong>Automated action:</strong> notify head office and the permitting authority; schedule a
			ground or drone inspection of the area outside the boundary. First triggered on the pass of
			{shortDate(scenario.epochs[c.firstBreach].date)}.
		</p>
	{/if}
</section>

<section
	class="brand-pattern-waves rounded-lg border border-yonder-500/40 bg-deep-blue/95 p-3.5 text-[11px] leading-relaxed shadow-lg"
>
	<h3 class="text-[11px] font-bold tracking-wider text-white uppercase">Measured on this pass</h3>
	<div class="mt-2 grid grid-cols-2 gap-2">
		{#each [{ v: ha(m.inside_m2), k: 'new clearing inside the permit' }, { v: ha(m.outside_m2), k: 'new clearing outside it' }, { v: `${m.max_distance_outside_m} m`, k: 'furthest digging beyond the boundary' }, { v: `${m.max_subsidence_outside_cm.toFixed(1)} cm`, k: 'ground sinking beside the permit (InSAR)' }] as tile (tile.k)}
			<div class="rounded border border-yonder-500/30 bg-deep-blue/90 p-2">
				<div class="font-mono-telemetry text-base font-bold text-white">{tile.v}</div>
				<div class="text-[10px] text-slate-300">{tile.k}</div>
			</div>
		{/each}
	</div>

	<table class="mt-3 w-full text-left">
		<caption class="mb-1 text-left text-[10px] text-slate-300">
			Every pass, compared with the baseline. Select a row to view it.
		</caption>
		<thead class="text-[10px] text-slate-300">
			<tr
				><th class="py-1">Pass</th><th>Inside</th><th>Beyond {t.tolerance_m} m band</th><th
					>Status</th
				></tr
			>
		</thead>
		<tbody class="font-mono-telemetry">
			{#each scenario.metrics as row, idx (idx)}
				{@const level = compliance(scenario, idx).level}
				<tr
					class="border-t border-yonder-500/20 {idx === i ? 'text-neon-yellow' : 'text-slate-200'}"
				>
					<td class="py-1">
						<button
							type="button"
							class="underline-offset-2 hover:underline"
							onclick={() => (appState.epochIndex = idx)}
						>
							Day {scenario.epochs[idx].day}
						</button>
					</td>
					<td>{ha(row.inside_m2)}</td>
					<td>{ha(row.outside_beyond_tolerance_m2)}</td>
					<td
						class="font-sans text-[10px] font-bold uppercase {level === 'breach'
							? 'text-[#ff7f5c]'
							: ''}"
					>
						{level}
					</td>
				</tr>
			{/each}
		</tbody>
	</table>
	<p class="mt-2 text-[10px] text-slate-400">
		Breach rule: more than {ha(t.breach_outside_m2)} of new clearing beyond the {t.tolerance_m} m band.
		Watch: any clearing beyond the band, or {t.subsidence_watch_cm} cm of sinking beside the permit.
	</p>
</section>
