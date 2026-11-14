<script lang="ts">
	import type { Scenario } from '$lib/types/scenario';
	import { ha } from '$lib/data/scenarios';
	import { FlaskConical, ExternalLink, ShieldQuestion } from 'lucide-svelte';

	let { scenario }: { scenario: Scenario } = $props();
	let s = $derived(scenario);

	let steps = $derived(
		s.module === 'observed'
			? [
					`Pass selection: one acquisition mode and processing version only, and only passes whose scene median HV is within ${s.thresholds.calibration_tolerance_db} dB of the latest pass (earlier 2026 passes have non-physical offsets).`,
					`Lee speckle filter (${s.thresholds.lee_window_px} × ${s.thresholds.lee_window_px}) on HV and HH; each pass is offset so persistently vegetated reference ground matches the latest pass.`,
					`Baseline: the mean of the first two passes. Vegetation loss: ground within ${s.thresholds.vegetated_below_reference_db} dB of the vegetated reference whose HV drops by more than ${s.thresholds.drop_db} dB. New water: HH below ${s.thresholds.water_db} dB.`,
					`A change counts only on two consecutive passes, in patches of at least ${ha(s.thresholds.min_cluster_m2)}.`,
					'Uncertainty: the same rule between the two baseline passes gives the false-alarm rate. GUNW coherence over the changed ground is supporting evidence.'
				]
			: s.module === 'mining'
				? [
						`Lee speckle filter (5 × 5) on each ${s.sensor.polarization} backscatter pass.`,
						`Log-ratio against the baseline pass; a drop of more than ${s.thresholds.clearing_drop_db} dB on ground that was vegetated marks new clearing (forest volume scattering lost).`,
						`Clusters smaller than ${ha(s.thresholds.min_cluster_m2)} are dropped as speckle.`,
						`New clearing is split by the permit polygon, with a ${s.thresholds.tolerance_m} m tolerance band for geolocation error.`,
						`InSAR: coherence below ${s.thresholds.coherence_min} flags ground disturbed between passes; line-of-sight phase gives centimetre ground motion where coherence holds.`
					]
				: [
						`Lee speckle filter on each ${s.sensor.polarization} pass; water where filtered backscatter is below ${s.thresholds.water_db} dB (specular reflection).`,
						`Landslide: off-channel return drops by more than ${s.thresholds.landslide_drop_db} dB together with InSAR coherence below ${s.thresholds.coherence_min}.`,
						'Impoundment: new water upstream of the slide. Diversion: new and abandoned water downstream, and the shift of the channel centre row by row.',
						`Control reach above the lake: if its water area also changed, a basin-wide flood is the simpler explanation.`,
						`Root cause: a slide upstream on the same river, within ${s.thresholds.link_max_km} km and ${s.thresholds.link_max_days} days before the shift.`
					]
	);
</script>

{#if s.data_status === 'REAL'}
	<section
		class="rounded-lg border border-neon-yellow/60 bg-deep-blue/95 p-3.5 text-[11px] leading-relaxed text-slate-200 shadow-lg"
	>
		<h3 class="flex items-center gap-2 text-[11px] font-bold tracking-wider text-white uppercase">
			<ShieldQuestion class="h-4 w-4 text-neon-yellow" />
			<span>Data status: real NISAR observations</span>
		</h3>
		<p class="mt-1.5">
			Every image here is a real {s.sensor.backscatter_product} pass and every coherence layer a real
			{s.sensor.insar_product} pair, read from NASA's ASF DAAC archive. The detected areas are measured
			from those images. The products are provisional, so values can change when ASF reprocesses them.
		</p>
	</section>
{:else}
	<section
		class="rounded-lg border border-rocket-red/70 bg-deep-blue/95 p-3.5 text-[11px] leading-relaxed text-slate-200 shadow-lg"
	>
		<h3 class="flex items-center gap-2 text-[11px] font-bold tracking-wider text-white uppercase">
			<ShieldQuestion class="h-4 w-4 text-[#ff7f5c]" />
			<span>Data status: simulated</span>
		</h3>
		<p class="mt-1.5">
			These radar images are <strong>synthetic</strong>, generated from NISAR mission parameters to
			demonstrate the method. They are not satellite observations. The site, operator and permit are
			fictional and the location is illustrative. Every number shown is measured from the simulated
			images by the detection steps below, not typed in.
		</p>
		<p class="mt-1.5">
			With real data, backscatter would come from {s.sensor.backscatter_product}, and coherence and
			displacement from {s.sensor.insar_product}, searched via NASA Earthdata and ASF.
		</p>
	</section>
{/if}

<section
	class="brand-pattern-fiduciaries rounded-lg border border-yonder-500/40 bg-deep-blue/95 p-3.5 text-[11px] leading-relaxed text-slate-200 shadow-lg"
>
	<h3 class="flex items-center gap-2 text-[11px] font-bold tracking-wider text-white uppercase">
		<FlaskConical class="h-4 w-4 text-neon-yellow" />
		<span>How it is measured</span>
	</h3>
	<dl class="font-mono-telemetry mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-[10px]">
		<dt class="text-slate-400">Sensor</dt>
		<dd>{s.sensor.mission}</dd>
		<dt class="text-slate-400">Band</dt>
		<dd>{s.sensor.band}, {s.sensor.wavelength_cm} cm</dd>
		<dt class="text-slate-400">Repeat</dt>
		<dd>{s.sensor.repeat_days} days, any weather</dd>
		<dt class="text-slate-400">Pixel</dt>
		<dd>{s.sensor.pixel_m} m, {s.sensor.polarization}</dd>
	</dl>
	<ol class="mt-2 list-decimal space-y-1 pl-4">
		{#each steps as step (step)}<li>{step}</li>{/each}
	</ol>
	<p class="mt-2 rounded border border-yonder-500/30 bg-deep-blue/90 p-2">
		{#if s.validation.precision !== null && s.validation.recall !== null}
			<strong class="text-white">Detector accuracy on this simulation:</strong>
			precision {Math.round(s.validation.precision * 100)}%, recall {Math.round(
				s.validation.recall * 100
			)}%.
			{s.validation.note} Real scenes are harder: slope, moisture and crop changes also shift backscatter.
		{:else}
			<strong class="text-white">Accuracy: not yet validated.</strong>
			{s.validation.note}
		{/if}
	</p>
	<h4 class="mt-3 font-bold text-white">NASA resources this method follows</h4>
	<ul class="mt-1 space-y-1">
		<li>
			<a
				href="https://nisar.jpl.nasa.gov/"
				target="_blank"
				rel="noopener noreferrer"
				class="brand-link-secondary inline-flex items-center gap-1"
			>
				NISAR mission (NASA JPL)<ExternalLink class="h-3 w-3" />
			</a>
		</li>
		<li>
			<a
				href="https://nisar-docs.asf.alaska.edu/"
				target="_blank"
				rel="noopener noreferrer"
				class="brand-link-secondary inline-flex items-center gap-1"
			>
				NISAR data products: GCOV, GUNW (ASF DAAC)<ExternalLink class="h-3 w-3" />
			</a>
		</li>
		<li>
			<a
				href="https://search.earthdata.nasa.gov/"
				target="_blank"
				rel="noopener noreferrer"
				class="brand-link-secondary inline-flex items-center gap-1"
			>
				NASA Earthdata Search<ExternalLink class="h-3 w-3" />
			</a>
		</li>
		<li>
			<a
				href="https://hyp3-docs.asf.alaska.edu/"
				target="_blank"
				rel="noopener noreferrer"
				class="brand-link-secondary inline-flex items-center gap-1"
			>
				ASF HyP3 on-demand InSAR and RTC processing<ExternalLink class="h-3 w-3" />
			</a>
		</li>
		<li>
			<a
				href="https://ntrs.nasa.gov/citations/20190002563"
				target="_blank"
				rel="noopener noreferrer"
				class="brand-link-secondary inline-flex items-center gap-1"
			>
				The SAR Handbook (NASA SERVIR, 2019)<ExternalLink class="h-3 w-3" />
			</a>
		</li>
	</ul>
</section>
