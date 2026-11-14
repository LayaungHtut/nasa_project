<script lang="ts">
	import { appState } from '$lib/stores/appState.svelte';
	import { ha, shortDate, slopeLabel } from '$lib/data/scenarios';
	import type { SlopeCandidate, SlopeScenario } from '$lib/types/scenario';
	import { Mountain, Info, ExternalLink } from 'lucide-svelte';

	let { scenario }: { scenario: SlopeScenario } = $props();
	let i = $derived(appState.epochIndex);
	let m = $derived(scenario.metrics[i]);
	let epoch = $derived(scenario.epochs[i]);
	let t = $derived(scenario.thresholds);
	let u = $derived(scenario.uncertainty);
	let p = $derived(scenario.provenance);
	let cands = $derived(scenario.candidates);
	let total = $derived(cands.reduce((a, c) => a + c.area_m2, 0));
	let picked = $derived(appState.selectedCandidate ?? cands[0] ?? null);

	const cmYr = (v: number) => `${v > 0 ? '+' : ''}${v.toFixed(1)} cm/yr`;

	// Cumulative LOS chart: picked candidate against the flat reference, both in cm.
	const W = 300;
	const H = 110;
	const PAD = 22;
	let chart = $derived.by(() => {
		const series = [picked?.series_cm ?? [], scenario.reference_series_cm];
		const vals = series.flat().filter((v): v is number => v !== null);
		const span = Math.max(2, ...vals.map(Math.abs));
		const n = scenario.epochs.length;
		const x = (k: number) => PAD + (k / Math.max(1, n - 1)) * (W - PAD - 4);
		const y = (v: number) => H / 2 - (v / span) * (H / 2 - 8);
		const path = (s: Array<number | null>) =>
			s
				.map((v, k) => (v === null ? null : `${x(k).toFixed(1)},${y(v).toFixed(1)}`))
				.filter(Boolean)
				.join(' ');
		return { span, x, y, cand: path(series[0]), ref: path(series[1]) };
	});

	function pick(c: SlopeCandidate) {
		appState.selectPatch(c.candidate_id);
	}
</script>

<section
	class="rounded-lg border p-3.5 text-[11px] leading-relaxed text-white shadow-lg {cands.length
		? 'border-neon-yellow/80 bg-deep-blue'
		: 'border-yonder-500/50 bg-electric-blue/35'}"
	role="status"
	aria-live="polite"
>
	<div class="flex items-start gap-2.5">
		<Mountain class="mt-0.5 h-5 w-5 shrink-0 text-neon-yellow" />
		<div class="min-w-0">
			<div class="flex flex-wrap items-center gap-2">
				<h3 class="text-sm font-black tracking-wide uppercase">
					{cands.length ? 'Slopes moving beyond noise' : 'No slope moving beyond noise'}
				</h3>
				<span
					class="rounded border border-neon-yellow/70 px-1.5 py-0.5 font-mono text-[9px] font-bold tracking-wider text-neon-yellow uppercase"
				>
					Real NISAR data
				</span>
			</div>
			<p class="mt-0.5 text-slate-100">
				Track {p.track}
				{p.orbit_direction} · Frame {p.frame} · pair {shortDate(epoch.coherence_pair![0])} → {shortDate(
					epoch.date
				)}
			</p>
			<p class="font-mono text-[9px] break-all text-slate-300" title="GUNW granule of this pair">
				{epoch.gunw_granule_id}
			</p>
		</div>
	</div>
	<ul class="mt-2 list-disc space-y-1 pl-5 text-slate-100">
		<li>
			{cands.length}
			{cands.length === 1 ? 'patch' : 'patches'} of ground steeper than {t.slope_min_deg}° ({ha(
				total
			)} in all) moved faster than {(t.sigma_k * u.rate_sigma_cm_yr).toFixed(1)} cm/yr along the line
			of sight, {t.sigma_k}× the {u.rate_sigma_cm_yr.toFixed(1)} cm/yr scatter on flat reference ground,
			over all {scenario.epochs.length} pairs.
		</li>
		<li>
			This pair: {m.measured_pct}% of the window could be read; flat ground scattered by {m.reference_scatter_cm ??
				'–'} cm{m.gap_before_days > 0
				? `; ${m.gap_before_days} days before it were not measured`
				: ''}.
		</li>
		<li>
			A moving steep slope is a landslide indicator to check, not a confirmed slide: mining cuts,
			dumping and erosion move ground too.
		</li>
	</ul>
</section>

{#if cands.length}
	<section
		class="rounded-lg border border-yonder-500/40 bg-deep-blue/95 p-3.5 text-[11px] leading-relaxed text-slate-200 shadow-lg"
	>
		<h3 class="text-[11px] font-bold tracking-wider text-white uppercase">Moving slopes</h3>
		<ul class="mt-1.5 space-y-1">
			{#each cands as c (c.candidate_id)}
				{@const on = picked?.candidate_id === c.candidate_id}
				<li>
					<button
						type="button"
						aria-pressed={on}
						onclick={() => pick(c)}
						class="flex w-full flex-wrap items-baseline justify-between gap-x-2 rounded border px-2 py-1 text-left transition-colors {on
							? 'border-neon-yellow/70 bg-electric-blue/50 text-white'
							: 'border-yonder-500/30 hover:border-neon-yellow/60'}"
					>
						<span class="font-bold">{slopeLabel(c)}</span>
						<span class="font-mono text-[10px] tabular-nums">
							{cmYr(c.rate_cm_yr)} · {c.slope_deg}° · {ha(c.area_m2)}
						</span>
					</button>
				</li>
			{/each}
		</ul>
		{#if picked}
			<figure class="mt-2">
				<svg
					viewBox="0 0 {W} {H}"
					class="w-full"
					role="img"
					aria-label="Cumulative line-of-sight motion of {slopeLabel(
						picked
					)} and of flat reference ground, pair by pair"
				>
					<line x1={PAD} x2={W - 4} y1={H / 2} y2={H / 2} stroke="#3d4f7a" />
					<text x="2" y="10" fill="#cbd5e1" font-size="8">+{chart.span.toFixed(0)}</text>
					<text x="2" y={H - 2} fill="#cbd5e1" font-size="8">−{chart.span.toFixed(0)}</text>
					<line
						x1={chart.x(i)}
						x2={chart.x(i)}
						y1="4"
						y2={H - 4}
						stroke="#eafe07"
						stroke-dasharray="2 2"
					/>
					<polyline points={chart.ref} fill="none" stroke="#8a94a8" stroke-width="1.5" />
					<polyline points={chart.cand} fill="none" stroke="#199e70" stroke-width="2" />
				</svg>
				<figcaption class="text-[10px] text-slate-300">
					Cm toward (+) or away (−) from the satellite, summed pair by pair:
					<span class="font-bold text-[#34c38f]">{slopeLabel(picked)}</span>
					({Math.round(picked.sign_agreement * 100)}% of its {picked.pairs_measured} pairs agree in direction)
					versus
					<span class="font-bold text-slate-200">flat reference ground</span>. Gaps are pairs where
					too little of the patch could be read.
				</figcaption>
			</figure>
		{/if}
	</section>
{/if}

<section
	class="rounded-lg border border-yonder-500/40 bg-deep-blue/95 p-3.5 text-[11px] leading-relaxed text-slate-200 shadow-lg"
>
	<h3 class="flex items-center gap-2 text-[11px] font-bold tracking-wider text-white uppercase">
		<Info class="h-4 w-4 text-neon-yellow" />
		<span>Uncertainty and limits</span>
	</h3>
	<p class="mt-1.5">
		Rate scatter on {(u.reference_m2 / 1e6).toFixed(0)} km² of flat reference ground: {u.rate_sigma_cm_yr.toFixed(
			1
		)} cm/yr. {u.rate_coverage_pct}% of the window was read often enough to get a rate.
	</p>
	<ul class="mt-1.5 list-disc space-y-1 pl-4">
		{#each u.notes as n (n)}<li>{n}</li>{/each}
	</ul>
	<details class="mt-2">
		<summary class="cursor-pointer font-bold text-white">
			Data used: {p.gunw_granules.length} GUNW pairs, {p.gcov_granules.length} GCOV passes, NASADEM
		</summary>
		<p class="mt-1.5">
			Sign: {p.sign_convention.statement}.
			<a
				href="https://github.com/isce-framework/isce3/blob/develop/python/packages/nisar/workflows/solid_earth_tides.py"
				target="_blank"
				rel="noopener noreferrer"
				class="brand-link-secondary inline-flex items-center gap-1"
				>ISCE3 source<ExternalLink class="h-3 w-3" /></a
			>
		</p>
		<p class="mt-1">Slope: {p.dem.product}.</p>
		<ul class="mt-1.5 space-y-0.5 font-mono text-[9px] break-all text-slate-300">
			{#each [...p.gunw_granules, ...p.gcov_granules] as g (g)}<li>{g}</li>{/each}
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
