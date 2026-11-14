<script lang="ts">
	import { appState } from '$lib/stores/appState.svelte';
	import { seasonFindings } from '$lib/data/timeseries';
	import { formatAcquisitionDate } from '$lib/data/presentation';
	let event = $derived(appState.selectedEvent);
	let threshold = $derived(event.processing.threshold_db);
	let polarimetry = $derived(event.polarimetry);
	let mode = $derived(appState.activeLayer);
	let showsHv = $derived(
		appState.polarization === 'HV' &&
			!!polarimetry &&
			['compare', 'baseline', 'post'].includes(mode)
	);
	let range = $derived(
		showsHv && polarimetry
			? polarimetry.display.hv_range_db
			: (event.tiles.display_range_db ?? [-25, -5])
	);
</script>

<div
	class="rounded-lg border border-yonder-500/40 bg-deep-blue/95 p-3 text-xs text-slate-200 shadow-xl backdrop-blur-md"
>
	{#if mode === 'optical_compare'}
		<p class="font-semibold text-white">Radar ↔ true-color optical</p>
		<p class="mt-1 max-w-60 text-[11px]">
			Drag the divider. Images show different dates and different kinds of surface information.
		</p>
		<p class="mt-2 font-semibold text-neon-yellow">○ Candidate markers · click to inspect</p>
		<p class="mt-1 text-[10px] text-slate-300">
			Outlines follow candidate pixels. Markers locate small shapes; their size does not represent
			area.
		</p>
	{:else if mode === 'landcover' && event.timeseries?.landcover_map}
		{@const lc = event.timeseries.landcover_map}
		{@const loss = seasonFindings(event.timeseries).loss}
		<p class="font-semibold text-white">Land cover (ESA WorldCover)</p>
		<ul class="mt-2 space-y-1 text-[11px]">
			{#each lc.classes as c (c.key)}
				<li class="flex items-center justify-between gap-4">
					<span class="flex items-center gap-1.5"
						><span class="h-3 w-3 rounded-sm" style:background={c.color}></span>{c.label}</span
					>
					<span class="font-mono text-slate-300">{c.area_km2} km²</span>
				</li>
			{/each}
			<li class="flex items-center gap-1.5 text-slate-300">
				<span class="h-3 w-3 rounded-sm border border-slate-400"></span>{lc.uncoloured}: no colour
			</li>
		</ul>
		<label class="mt-2.5 flex cursor-pointer items-start gap-2 text-[11px] text-white">
			<input
				type="checkbox"
				class="mt-0.5 h-3.5 w-3.5 rounded border-slate-400 bg-deep-blue text-electric-blue focus:ring-neon-yellow"
				bind:checked={appState.showWaterLoss}
			/>
			<span
				><span class="mr-1 inline-block h-2.5 w-2.5 rounded-sm bg-white align-middle"
				></span>Apparent water loss, {formatAcquisitionDate(
					event.observation_dates.baseline
				).replace(/, \d{4}$/, '')}
				→ {formatAcquisitionDate(event.observation_dates.post_event).replace(/, \d{4}$/, '')}</span
			>
		</label>
		<p class="mt-1.5 max-w-60 text-[10px] leading-relaxed text-slate-300">
			The two-date comparison flagged {loss.total.toFixed(2)} km² as water loss. {loss.paddyPct}% of
			it lies on paddy fields and {loss.reservoir} km² on the reservoir: the fields changed, not the reservoir.
			The map is from 2021, so a few fields may have changed use since.
		</p>
	{:else if mode === 'field_timing' && event.timeseries}
		{@const ps = event.timeseries.pixel_season}
		{@const day = (iso: string) =>
			new Date(iso).toLocaleDateString('en-US', {
				month: 'short',
				day: 'numeric',
				timeZone: 'UTC'
			})}
		<p class="font-semibold text-white">When each paddy field was darkest</p>
		<ul class="mt-2 space-y-1 text-[11px]">
			{#each ps.darkest_pass_periods as period (period.from)}
				<li class="flex items-center justify-between gap-4">
					<span class="flex items-center gap-1.5"
						><span class="h-3 w-3 rounded-sm" style:background={period.color}></span>{day(
							period.from
						)} to {day(period.to)}</span
					>
					<span class="font-mono text-slate-300">{period.cropland_km2} km²</span>
				</li>
			{/each}
		</ul>
		<p class="mt-2 max-w-60 text-[10px] leading-relaxed text-slate-300">
			Paddy pixels (ESA WorldCover) whose radar return later rose by at least
			{ps.rice_rise_threshold_db} dB against forest. The darkest pass is the most water-like: likely flooded,
			around planting. {Math.round(ps.dark_then_rise.forest_control * 100)}% of forest pixels pass
			the same test by chance, so read patterns, not single pixels. Pixels
			{ps.timing_neighbour_agreement.lag_m} m apart share a colour
			{Math.round(ps.timing_neighbour_agreement.observed * 100)}% of the time ({Math.round(
				ps.timing_neighbour_agreement.if_random * 100
			)}% if random).
		</p>
	{:else if mode === 'difference' && polarimetry}
		{@const [lo, hi] = polarimetry.display.difference_range_db}
		<p class="font-semibold text-white">HH change, second date minus first</p>
		<div class="mt-2 flex justify-between gap-6 text-[10px] text-slate-300">
			<span>{lo} dB darker</span><span>{hi} dB brighter</span>
		</div>
		<div
			class="mt-1 h-2 rounded bg-gradient-to-r from-yonder-500 via-transparent to-rocket-red"
		></div>
		<p class="mt-2 max-w-60 text-[10px] leading-relaxed text-slate-300">
			Changes smaller than ±{polarimetry.display.difference_transparent_below_db} dB are left clear; that
			much varies by chance between passes. Smoothed with a
			{polarimetry.display.difference_display_smoothing} for display. Brighter does not mean wetter or
			drier on its own.
		</p>
	{:else}
		<p class="font-semibold text-white">
			Radar backscatter preview{#if polarimetry}
				<span class="font-mono {showsHv ? 'text-neon-yellow' : 'text-yonder-400'}"
					>· {showsHv ? 'HV' : 'HH'}</span
				>{/if}
		</p>
		<div class="mt-2 flex justify-between gap-6 text-[10px] text-slate-300">
			<span>{range[0]} dB or lower</span><span>{range[1]} dB or higher</span>
		</div>
		<div class="mt-1 h-2 rounded bg-gradient-to-r from-black to-white"></div>
		<p class="mt-2 max-w-60 text-[10px] leading-relaxed text-slate-300">
			{appState.activeLayer === 'series'
				? 'Every pass uses the same grayscale range.'
				: 'Both dates use the same grayscale range.'} Dark pixels have lower radar return; darkness alone
			does not identify water.
		</p>
		{#if showsHv && polarimetry && !polarimetry.hv_assessment.hv_usable_for_interpretation}
			<p
				class="mt-2 max-w-60 rounded border border-rocket-red/70 bg-martian-red/90 p-1.5 text-[10px] leading-relaxed text-white"
			>
				<strong class="text-neon-yellow">Quality warning:</strong> HV in these scenes fails our consistency
				checks and is shown for comparison only. See “Which polarization shows the change?”
			</p>
		{/if}
		{#if threshold !== undefined && !showsHv}<p class="mt-2 font-mono text-neon-yellow">
				Scene threshold: {threshold} dB
			</p>{/if}
	{/if}
	{#if mode === 'change_mask'}
		<p class="mt-2 flex items-center gap-2 text-white">
			<span class="h-3 w-3 rounded-sm bg-yonder-400"></span>New-inundation candidates
		</p>
	{/if}
</div>
