<script lang="ts">
	import { appState } from '$lib/stores/appState.svelte';
	import { forensics, ha, shortDate } from '$lib/data/scenarios';
	import type { LandslideScenario } from '$lib/types/scenario';
	import { Link2, TriangleAlert, Radar, Check, X, HelpCircle } from 'lucide-svelte';

	let { scenario }: { scenario: LandslideScenario } = $props();
	let i = $derived(appState.epochIndex);
	let f = $derived(forensics(scenario, i));
	let m = $derived(scenario.metrics[i]);
	let L = $derived(scenario.linkage);

	const banner = {
		linked: 'border-neon-yellow/80 bg-electric-blue/50',
		early_warning: 'border-rocket-red bg-martian-red',
		unexplained: 'border-yonder-400/60 bg-deep-blue',
		monitoring: 'border-yonder-500/50 bg-electric-blue/35'
	};
	const verdictClass = {
		'Ruled out': 'border-yonder-400/60 text-yonder-300',
		Unlikely: 'border-slate-500 text-slate-300',
		'Not tested': 'border-slate-600 text-slate-400'
	};
	// The forensic chain, in time order, using the measured pass of each step.
	let chain = $derived(
		[
			{
				epoch: L.precursor_pass,
				title: 'Slope creep',
				text: `${L.precursor_creep_cm.toFixed(1)} cm away from the satellite (InSAR)`
			},
			{
				epoch: f.slideEpoch,
				title: 'Landslide and dam',
				text: `${ha(scenario.metrics[f.slideEpoch]?.landslide_m2 ?? 0)} slope failure; river blocked`
			},
			{
				epoch: f.diversionEpoch,
				title: 'River diverted',
				text: `${scenario.metrics[f.diversionEpoch]?.channel_shift_m ?? 0} m shift, ${L.river_distance_km.toFixed(1)} km downstream`
			}
		].filter((c) => c.epoch >= 0)
	);
</script>

<section
	class="rounded-lg border p-3.5 text-[11px] leading-relaxed text-white shadow-lg {banner[f.stage]}"
	role={f.stage === 'early_warning' ? 'alert' : 'status'}
	aria-live="polite"
>
	<div class="flex items-start gap-2.5">
		{#if f.stage === 'linked'}
			<Link2 class="mt-0.5 h-5 w-5 shrink-0 text-neon-yellow" />
		{:else if f.stage === 'early_warning'}
			<TriangleAlert class="mt-0.5 h-5 w-5 shrink-0" />
		{:else}
			<Radar class="mt-0.5 h-5 w-5 shrink-0 text-yonder-300" />
		{/if}
		<div class="min-w-0">
			<div class="flex flex-wrap items-center gap-2">
				<h3 class="text-sm font-black tracking-wide uppercase">
					{f.stage === 'linked'
						? 'Automated Root-Cause Insight'
						: f.stage === 'early_warning'
							? 'Early warning: upstream landslide'
							: f.stage === 'unexplained'
								? 'River shift, cause not found'
								: 'Monitoring: no change'}
				</h3>
				<span
					class="rounded border border-white/60 px-1.5 py-0.5 font-mono text-[9px] font-bold tracking-wider uppercase"
				>
					Simulated
				</span>
			</div>
		</div>
	</div>
	<p class="mt-2 text-slate-100">
		{#if f.stage === 'linked'}
			The river moved {m.channel_shift_m} m on the pass of {shortDate(
				scenario.epochs[f.diversionEpoch].date
			)}. The likeliest cause is the landslide detected {f.lagDays} days earlier,
			{L.river_distance_km.toFixed(1)} km upstream on the same river, which blocked the channel and sent
			a pulse of water and sediment downstream.
		{:else if f.stage === 'early_warning'}
			A {ha(m.landslide_m2)} landslide has blocked the river and {ha(m.impoundment_m2)} of water is ponding
			behind it. Villages and fields downstream face a dam-break flood or a change of river course. Warn
			them now.
		{:else if f.stage === 'unexplained'}
			The channel moved, but no upstream slide fits the distance and timing limits ({scenario
				.thresholds.link_max_km} km,
			{scenario.thresholds.link_max_days} days).
		{:else}
			No landslide or channel change detected yet on this pass. Step through the timeline.
		{/if}
	</p>
</section>

{#if chain.length && f.stage !== 'monitoring'}
	<section
		class="rounded-lg border border-yonder-500/40 bg-deep-blue/95 p-3.5 text-[11px] shadow-lg"
	>
		<h3 class="text-[11px] font-bold tracking-wider text-white uppercase">Forensic timeline</h3>
		<ol class="mt-2 space-y-2 border-l-2 border-electric-blue pl-3">
			{#each chain as step (step.title)}
				{@const reached = i >= step.epoch}
				<li class={reached ? 'text-slate-100' : 'text-slate-400'}>
					<button
						type="button"
						class="text-left hover:text-neon-yellow"
						onclick={() => (appState.epochIndex = step.epoch)}
					>
						<span class="font-mono-telemetry font-bold {reached ? 'text-neon-yellow' : ''}">
							Day {scenario.epochs[step.epoch].day} · {shortDate(scenario.epochs[step.epoch].date)}
						</span>
						<span class="block font-semibold">{step.title}</span>
						<span class="block text-[10px]">{step.text}</span>
					</button>
				</li>
			{/each}
		</ol>
	</section>

	<section
		class="brand-pattern-waves rounded-lg border border-yonder-500/40 bg-deep-blue/95 p-3.5 text-[11px] leading-relaxed shadow-lg"
	>
		<h3 class="text-[11px] font-bold tracking-wider text-white uppercase">Evidence</h3>
		<ul class="mt-2 space-y-1.5">
			{#each f.evidence as e (e.text)}
				<li class="flex gap-2 text-slate-200">
					{#if e.supports}<Check
							class="mt-0.5 h-3.5 w-3.5 shrink-0 text-neon-yellow"
						/>{:else}<HelpCircle class="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-400" />{/if}
					<span>{e.text}</span>
				</li>
			{/each}
		</ul>
		{#if f.stage === 'linked'}
			<h3 class="mt-3 text-[11px] font-bold tracking-wider text-white uppercase">
				Other explanations checked
			</h3>
			<ul class="mt-2 space-y-2">
				{#each f.alternatives as a (a.title)}
					<li class="rounded border border-yonder-500/30 bg-deep-blue/90 p-2">
						<div class="flex items-center justify-between gap-2">
							<span class="flex items-center gap-1.5 font-semibold text-white">
								<X class="h-3 w-3 text-slate-400" />{a.title}
							</span>
							<span
								class="shrink-0 rounded border px-1.5 py-0.5 font-mono text-[9px] font-bold uppercase {verdictClass[
									a.verdict
								]}"
							>
								{a.verdict}
							</span>
						</div>
						<p class="mt-1 text-slate-300">{a.reason}</p>
					</li>
				{/each}
			</ul>
		{/if}
	</section>
{/if}
