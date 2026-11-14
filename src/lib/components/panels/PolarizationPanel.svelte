<script lang="ts">
	import { appState } from '$lib/stores/appState.svelte';
	import { formatAcquisitionDate } from '$lib/data/presentation';
	import { resolve } from '$app/paths';
	import { Waves, AlertTriangle } from 'lucide-svelte';

	let event = $derived(appState.selectedEvent);
	let pol = $derived(event.polarimetry);
	let dateOf = (which: 'baseline' | 'repeat') =>
		formatAcquisitionDate(
			which === 'baseline' ? event.observation_dates.baseline : event.observation_dates.post_event
		);
	let worstHvRfi = $derived(
		pol?.dates.reduce((a, b) => (b.rfi_likelihood.HV > a.rfi_likelihood.HV ? b : a))
	);
	let unmitigated = $derived(
		pol
			? Object.values(pol.product_flags).every(
					(f) => !f.rfi_mitigation_applied && !f.noise_correction_applied
				)
			: false
	);

	function showOnMap(channel: 'HH' | 'HV') {
		appState.polarization = channel;
		appState.activeLayer = 'compare';
	}

	const SCALE_MIN_DB = -24;
	const SCALE_MAX_DB = 0;
	function dbToPercent(dbVal: number | null | undefined): number {
		if (dbVal === null || dbVal === undefined || Number.isNaN(dbVal)) return 0;
		const clamped = Math.max(SCALE_MIN_DB, Math.min(SCALE_MAX_DB, dbVal));
		return ((clamped - SCALE_MIN_DB) / (SCALE_MAX_DB - SCALE_MIN_DB)) * 100;
	}
</script>

{#if pol}
	<section
		class="brand-pattern-waves rounded-lg border border-yonder-500/40 bg-deep-blue/95 p-3.5 text-[11px] leading-relaxed shadow-lg"
		aria-labelledby="polarization-heading"
	>
		<h2
			id="polarization-heading"
			class="flex items-center gap-2 text-[11px] font-bold tracking-wider text-white uppercase"
		>
			<Waves class="h-4 w-4 text-yonder-400" />
			Which polarization shows the change?
		</h2>
		<p class="mt-2 text-slate-200">
			NISAR recorded two channels here. <strong class="text-yonder-400">HH</strong> (sent and
			received horizontally) is very sensitive to smooth water and to stems standing in water.
			<strong class="text-neon-yellow">HV</strong> (sent horizontally, received vertically) comes mostly
			from scattering inside vegetation, so over natural surfaces it is normally several dB weaker than
			HH.
		</p>

		<table class="mt-3 w-full text-left font-mono text-[10px]">
			<thead class="text-slate-300">
				<tr>
					<th class="font-normal">Median of study area</th>
					<th class="text-right font-normal">HH</th>
					<th class="text-right font-normal">HV</th>
					<th class="text-right font-normal">RFI HH / HV</th>
				</tr>
			</thead>
			<tbody class="text-white">
				{#each pol.dates as d (d.date)}
					<tr class="border-t border-yonder-500/20">
						<td class="py-1 font-sans text-slate-300">{dateOf(d.date)}</td>
						<td class="text-right text-yonder-400">{d.median_db.HH.toFixed(1)} dB</td>
						<td class="text-right text-neon-yellow">{d.median_db.HV.toFixed(1)} dB</td>
						<td class="text-right"
							>{d.rfi_likelihood.HH.toFixed(1)} / {d.rfi_likelihood.HV.toFixed(1)}</td
						>
					</tr>
				{/each}
			</tbody>
		</table>
		<p class="mt-1 text-[10px] text-slate-300">
			RFI is the product's own radio-frequency-interference likelihood score; higher is worse.
		</p>

		{#if !pol.hv_assessment.hv_usable_for_interpretation}
			<div class="mt-3 rounded border border-rocket-red/70 bg-martian-red/90 p-2.5 text-white">
				<p class="flex items-center gap-1.5 font-bold text-neon-yellow">
					<AlertTriangle class="h-4 w-4 shrink-0" />
					Finding: HH carries the surface signal here; HV is not interpreted
				</p>
				<ul class="mt-1.5 list-disc space-y-1 pl-4">
					{#each pol.hv_assessment.reasons as reason (reason)}
						<li>{reason}</li>
					{/each}
				</ul>
				{#if worstHvRfi}
					<p class="mt-1.5">
						The product rates HV interference likelihood at {worstHvRfi.rfi_likelihood.HV.toFixed(
							1
						)}
						on {dateOf(worstHvRfi.date)}, versus {worstHvRfi.rfi_likelihood.HH.toFixed(1)} for HH{#if unmitigated},
							and reports that neither RFI mitigation nor noise correction was applied to these
							provisional products{/if}. Interference is a plausible cause; we have not confirmed
						it.
					</p>
				{/if}
			</div>
		{/if}

		<p class="mt-3 text-slate-200">
			<strong>Why this matters:</strong> check each channel's quality before reading the surface from
			it. On clean scenes, HV helps tell flooded forest and growing crops apart from open water, which
			HH alone cannot do.
		</p>

		{#if event.processing.threshold_db !== undefined && pol.classes}
			{@const lossBase = pol.classes.apparent_water_loss.HH.baseline}
			{@const lossRep = pol.classes.apparent_water_loss.HH.repeat}
			{@const waterBoth = pol.classes.water_both_dates.HH.repeat}
			{@const landBoth = pol.classes.land_both_dates.HH.repeat}
			{@const noiseFloor = pol.dates[0]?.noise_equivalent_backscatter_db.HH ?? -22.4}
			{@const thresh = event.processing.threshold_db}
			<div class="mt-3 rounded border border-yonder-500/30 bg-deep-blue/90 p-2.5">
				<div class="flex items-center justify-between text-[10px]">
					<span class="font-semibold text-white">
						HH Backscatter Scale (Why "lost" water crossed the threshold)
					</span>
					<span class="font-mono text-neon-yellow">Cutoff: {thresh} dB</span>
				</div>
				<div
					class="relative mt-5 mb-2 h-3 w-full rounded-full bg-gradient-to-r from-deep-blue via-electric-blue to-white"
				>
					<!-- Threshold line -->
					<div
						class="absolute -top-2.5 -bottom-1 w-0.5 bg-neon-yellow"
						style:left={`${dbToPercent(thresh)}%`}
						title={`Water cutoff threshold (${thresh} dB)`}
					>
						<span
							class="absolute -top-3.5 left-1/2 -translate-x-1/2 font-mono text-[8px] font-bold whitespace-nowrap text-neon-yellow"
						>
							{thresh} dB
						</span>
					</div>
					<!-- Noise floor marker -->
					<div
						class="absolute top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border border-slate-300 bg-deep-blue"
						style:left={`${dbToPercent(noiseFloor)}%`}
						title={`HH Noise Floor (${noiseFloor.toFixed(1)} dB)`}
					></div>
					<!-- Water both dates -->
					<div
						class="absolute top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border border-white bg-yonder-500"
						style:left={`${dbToPercent(waterBoth)}%`}
						title={`Water on both dates (${waterBoth?.toFixed(1)} dB)`}
					></div>
					<!-- Apparent water loss shift bar (Aug 27 -> Sep 8) -->
					{#if lossBase !== null && lossRep !== null}
						<div
							class="absolute top-1/2 h-1.5 -translate-y-1/2 rounded bg-neon-yellow"
							style:left={`${dbToPercent(lossBase)}%`}
							style:width={`${Math.max(2, dbToPercent(lossRep) - dbToPercent(lossBase))}%`}
							title={`Apparent water loss pixels shifted from ${lossBase.toFixed(2)} dB to ${lossRep.toFixed(2)} dB`}
						></div>
					{/if}
					<!-- Land both dates -->
					<div
						class="absolute top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border border-deep-blue bg-emerald-400"
						style:left={`${dbToPercent(landBoth)}%`}
						title={`Stable land (${landBoth?.toFixed(1)} dB)`}
					></div>
				</div>
				<div class="flex justify-between font-mono text-[9px] text-slate-300">
					<span>-24 dB (Dark / Mirror)</span>
					<span>-12 dB</span>
					<span>0 dB (Bright / Rough)</span>
				</div>
				<div class="mt-2 grid grid-cols-2 gap-1.5 text-[10px] text-slate-200">
					<div class="flex items-center gap-1.5">
						<span class="inline-block h-2 w-2 shrink-0 rounded-full bg-slate-400"></span>
						<span>Noise floor: <strong class="font-mono">{noiseFloor.toFixed(1)} dB</strong></span>
					</div>
					<div class="flex items-center gap-1.5">
						<span class="inline-block h-2 w-2 shrink-0 rounded-full bg-yonder-500"></span>
						<span>Water both: <strong class="font-mono">{waterBoth?.toFixed(1)} dB</strong></span>
					</div>
					<div class="flex items-center gap-1.5">
						<span class="inline-block h-2 w-2 shrink-0 rounded-full bg-neon-yellow"></span>
						<span
							>Apparent loss: <strong class="font-mono"
								>{lossBase?.toFixed(1)} → {lossRep?.toFixed(1)} dB</strong
							></span
						>
					</div>
					<div class="flex items-center gap-1.5">
						<span class="inline-block h-2 w-2 shrink-0 rounded-full bg-emerald-400"></span>
						<span>Stable land: <strong class="font-mono">{landBoth?.toFixed(1)} dB</strong></span>
					</div>
				</div>
			</div>
		{/if}

		<div class="mt-3 flex flex-wrap items-center gap-3">
			<button
				type="button"
				onclick={() => showOnMap('HH')}
				class="rounded border border-yonder-500/50 bg-electric-blue/50 px-2.5 py-1 text-[10px] font-bold tracking-wide text-white uppercase transition-colors hover:border-neon-yellow hover:text-neon-yellow"
				>Compare dates in HH</button
			>
			<button
				type="button"
				onclick={() => showOnMap('HV')}
				class="rounded border border-neon-yellow/60 bg-deep-blue px-2.5 py-1 text-[10px] font-bold tracking-wide text-neon-yellow uppercase transition-colors hover:bg-electric-blue/50"
				>Compare dates in HV</button
			>
			<a
				href={resolve('/data/[...path]', { path: pol.record_path })}
				download="hlawga-polarization.json"
				class="brand-link-secondary text-[10px]">Download polarization record</a
			>
		</div>
	</section>
{/if}
