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
			: [
					`Each 12-day GUNW pair: line-of-sight motion = (unwrapped phase − the product's ionosphere phase screen) × wavelength / 4π, positive toward the satellite (ISCE3 sign convention). Pixels kept where coherence ≥ ${s.thresholds.coherence_min} and the unwrapper assigned a connected component.`,
					`Each pair: a planar ramp (leftover ionosphere, orbit) and a linear trend with NASADEM elevation (height-dependent troposphere) are fitted on ground under ${s.thresholds.slope_min_deg}° and removed; then the pair is tied to flat ground (under ${s.thresholds.flat_max_deg}°) that stays coherent, in the same connected component.`,
					`Mean rate per pixel: measured motion divided by measured time, for pixels read on at least ${Math.round(s.thresholds.min_valid_frac * 100)}% of pairs; gaps between pairs do not count.`,
					`Candidate: ground steeper than ${s.thresholds.slope_min_deg}° whose rate exceeds ${s.thresholds.sigma_k}× the scatter on the flat reference, moving the same way on at least ${Math.round(s.thresholds.sign_agreement_min * 100)}% of its pairs, in patches of at least ${ha(s.thresholds.min_cluster_m2)}.`,
					'A candidate is a landslide indicator to check, not a confirmed slide: excavation, dumping and erosion also move ground, and line of sight is not the downslope direction.'
				]
	);
</script>

<section
	class="rounded-lg border border-neon-yellow/60 bg-deep-blue/95 p-3.5 text-[11px] leading-relaxed text-slate-200 shadow-lg"
>
	<h3 class="flex items-center gap-2 text-[11px] font-bold tracking-wider text-white uppercase">
		<ShieldQuestion class="h-4 w-4 text-neon-yellow" />
		<span>Data status: real NISAR observations</span>
	</h3>
	<p class="mt-1.5">
		Every radar image here is a real {s.sensor.backscatter_product} pass and every InSAR layer a real
		{s.sensor.insar_product} pair, read from NASA's ASF DAAC archive{s.module === 'slope'
			? '; terrain slope comes from NASADEM (NASA/JPL, LP DAAC)'
			: ''}. Every area and rate is measured from those files. The NISAR products are provisional,
		so values can change when ASF reprocesses them.
	</p>
</section>

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
		<strong class="text-white">Accuracy: not yet validated.</strong>
		{s.validation.note}
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
