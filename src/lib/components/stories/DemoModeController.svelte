<script lang="ts">
	import { appState, DEMO_STEP_COUNT } from '$lib/stores/appState.svelte';
	import {
		ChevronRight,
		ChevronLeft,
		X,
		Satellite,
		MapPin,
		Layers,
		Sparkles,
		Radio,
		ShieldCheck,
		Contrast,
		Sprout
	} from 'lucide-svelte';

	let evt = $derived(appState.selectedEvent);
	let changeArea = $derived(evt?.results.change_area_km2 ?? 0.056);
	let pixelCount = $derived(
		evt?.results.changed_pixels ?? evt?.statistics?.new_inundation_pixels ?? 556
	);
	let thresholdDb = $derived(evt?.processing.threshold_db ?? -9.54);
	let filterName = $derived(evt?.processing.speckle_filter ?? 'the recorded speckle filter');
	let heuristicScore = $derived(
		evt?.results.confidence_type === 'heuristic_detection_score'
			? evt.results.confidence.toFixed(3)
			: (evt?.results.confidence.toFixed(3) ?? '0.639')
	);
	let baselineDateStr = $derived(
		evt
			? new Date(evt.observation_dates.baseline).toLocaleDateString('en-US', {
					month: 'long',
					day: 'numeric',
					year: 'numeric',
					timeZone: 'UTC'
				})
			: 'August 27, 2026'
	);
	let postDateStr = $derived(
		evt
			? new Date(evt.observation_dates.post_event).toLocaleDateString('en-US', {
					month: 'long',
					day: 'numeric',
					year: 'numeric',
					timeZone: 'UTC'
				})
			: 'September 8, 2026'
	);
	let locationName = $derived(evt?.location.name ?? 'Hlawga Reservoir, Yangon Region');
	let trackFrame = $derived(
		evt?.source_products[0]?.track
			? `Track ${evt.source_products[0].track} / Frame 10`
			: 'Track 40 / Frame 10'
	);
	let coordinatesStr = $derived(
		evt
			? `${evt.location.center[0].toFixed(2)}°E, ${evt.location.center[1].toFixed(2)}°N`
			: '96.09°E, 17.06°N'
	);

	let demoSteps = $derived([
		{
			step: 1,
			title: 'The Challenge',
			headline: evt?.timeseries
				? `${evt.timeseries.dates.length} radar passes, one monsoon: Yangon's rice fields through the clouds`
				: 'What can NASA’s newest radar satellite reveal about our changing Earth?',
			description: evt?.timeseries
				? 'The map is playing the season. Every 12 days NISAR imaged the fields around Hlawga Reservoir, through cloud. Flooded fields look dark and brighten as the rice grows. The rest of the tour shows how we tested that, and why a changed radar signal does not automatically mean a flood.'
				: 'Cloud cover can obscure optical images during monsoon weather. Radar provides another view, but a changed radar signal does not automatically prove a flood.',
			actionText: 'Explore Hlawga Reservoir',
			icon: Satellite
		},
		{
			step: 2,
			title: 'Targeting Event',
			headline: `Targeting ${locationName} (NISAR ${trackFrame})`,
			description: `Centering on ${locationName} (${coordinatesStr}). Using genuine NASA NISAR Level-2 GCOV radar products downloaded from the Alaska Satellite Facility (ASF), we compare radar backscatter across two acquisitions. These measurements need interpretation and independent checks.`,
			actionText: 'View Baseline Observation',
			icon: MapPin
		},
		{
			step: 3,
			title: 'Baseline Pass',
			headline: `${baselineDateStr}: Reference Radar Baseline (Pass 29, ${trackFrame})`,
			description: `NISAR acquired its reference pass (a provisional product, before final calibration) over the ${evt?.location.country ?? 'Yangon'} footprint. Baseline backscatter is captured in the co-polarized HH channel, providing a reference for comparison without assuming dry conditions.`,
			actionText: 'View Repeat Observation',
			icon: Layers
		},
		{
			step: 4,
			title: 'Repeat Observation',
			headline: `${postDateStr}: 12-Day Orbital Repeat Pass (Pass 30, ${trackFrame})`,
			description: evt?.timeseries
				? 'Twelve days later our threshold classifies much less water. On a land-cover map, almost all of the "lost" water sits on paddy fields, not the reservoir: flooded fields stopped looking like water as the rice grew. It is not reservoir drawdown.'
				: 'The repeat observation shows a different radar response. Our threshold classifies less water overall; this could reflect surface roughness or other observation conditions. It is not evidence of a confirmed flood or reservoir drawdown.',
			actionText: 'Inspect Change Candidates',
			icon: Layers
		},
		{
			step: 5,
			title: 'Algorithmic Change',
			headline: `New Inundation Candidate: ${changeArea} km² across ${pixelCount} Pixels`,
			description: `Our deterministic remote sensing pipeline applied a ${filterName} and an empirically derived ${thresholdDb} dB threshold to flag possible water-extent changes across the study area with a ${heuristicScore} heuristic detection score across ${pixelCount} pixels. The candidate is sensitive to threshold and filter choices and has no independent ground-truth confirmation.`,
			actionText: 'What Changed, and Why?',
			icon: Sparkles
		},
		{
			step: 6,
			title: 'Drivers',
			headline: 'Orange got brighter, blue got darker: what could cause it?',
			description: evt?.drivers?.length
				? `The HH change map shows where the radar return changed between the dates. The panel on the right weighs ${evt.drivers.length} explanations against the recorded evidence. ${evt.weather?.comparison.all_near_calm ? 'We tested the obvious one, wind rippling the reservoir, against airport weather reports: both mornings were near calm, so wind does not explain it. ' : ''}${evt.timeseries ? 'The full season answers it: the paddy fields brighten as the rice grows, and almost all of the apparent water loss lies on paddy fields, not the reservoir. Field records would confirm it.' : 'Rice growing in the surrounding paddies may explain the widespread brightening. None is confirmed, and each says what would settle it.'}`
				: 'The HH change map shows where the radar return changed between the dates. A change in the signal still needs an explanation before it can be called a change on the ground.',
			actionText: 'Field by Field',
			icon: Contrast
		},
		{
			step: 7,
			title: 'Field by Field',
			headline: evt?.timeseries
				? `${Math.round(evt.timeseries.pixel_season.brightened_over_1db.cropland * 100)}% of paddy brightened. Forest, the control: ${Math.round(evt.timeseries.pixel_season.brightened_over_1db.forest_control * 100)}%.`
				: 'One date pair cannot tell growth from noise',
			description: evt?.timeseries
				? `An average can hide a few loud pixels, so we tested every 70 m patch. Forest should not change much over a few weeks, so it shows how often the test fires by chance. The map colours each paddy field by when it was darkest, most likely flooded around planting, before its radar return rose. The timing forms patches: pixels ${evt.timeseries.pixel_season.timing_neighbour_agreement.lag_m} m apart share a group ${Math.round(evt.timeseries.pixel_season.timing_neighbour_agreement.observed * 100)}% of the time, against ${Math.round(evt.timeseries.pixel_season.timing_neighbour_agreement.if_random * 100)}% if it were random speckle. That fits fields planted at different times, though a local shower on one date could also make patches.`
				: 'With only two dates, a brightening field and a noisy pixel look the same. A longer time series with a control surface is needed.',
			actionText: 'How SAR Works',
			icon: Sprout
		},
		{
			step: 8,
			title: 'SAR Physics',
			headline: 'How Did NISAR See It? The Physics of Specular Reflection',
			description:
				'NISAR sends microwave pulses and measures their return, including at night and through cloud cover. Smooth water often reflects energy away and appears dark. Wind-roughened water may brighten; flooded vegetation can also return a strong signal.',
			actionText: 'Evidence & Next Steps',
			icon: Radio
		},
		{
			step: 9,
			title: 'Scientific Provenance',
			headline: 'Trace the Observations, Then Test the Interpretation',
			description: evt?.independent_validation
				? `Independent Sentinel-2 check: ${evt.independent_validation.summary} The wider-date optical pair is about four days away from each radar date. Open the dated overlays and download the evidence in the scientific panel; this is not field confirmation.${evt.ndvi ? ` Over the whole season, only ${evt.ndvi.scenes.filter((sc) => sc.cropland_ndvi_median !== undefined).length} of ${evt.ndvi.scenes.length} Sentinel-2 scenes were clear enough to measure greenness: in a monsoon, radar is the only regular view.` : ''}`
				: `Level-2 GCOV source identifiers (${trackFrame}), data status ${evt?.data_status ?? 'REAL'}, and processing parameters are available for inspection. Test the water-change hypothesis with independent imagery or reservoir water-level records.`,
			actionText: 'Explore Freely',
			icon: ShieldCheck
		}
	]);

	let currentStepData = $derived(
		demoSteps.find((s) => s.step === appState.demoStep) ?? demoSteps[0]
	);

	function handleKeydown(e: KeyboardEvent) {
		if (!appState.isDemoModeActive) return;
		if (e.key === 'ArrowRight' || e.key === ' ') {
			appState.nextDemoStep();
			e.preventDefault();
		} else if (e.key === 'ArrowLeft') {
			appState.prevDemoStep();
			e.preventDefault();
		} else if (e.key === 'Escape') {
			appState.endJudgeDemo();
			e.preventDefault();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

{#if appState.isDemoModeActive}
	<div
		class="fixed inset-x-0 bottom-6 z-40 mx-auto max-w-3xl px-4 select-none"
		role="region"
		aria-label="Judge Demo Tour Controller"
	>
		<div
			class="brand-pattern-orbits overflow-hidden rounded-xl border-2 border-neon-yellow/80 bg-deep-blue/95 text-slate-200 shadow-[0_0_40px_rgba(0,66,166,0.6)] backdrop-blur-md"
		>
			<!-- Top step progress bar -->
			<div class="flex h-1.5 w-full bg-electric-blue/50">
				<div
					class="bg-neon-yellow transition-all duration-300"
					style="width: {(appState.demoStep / DEMO_STEP_COUNT) * 100}%;"
				></div>
			</div>

			<div class="p-4 sm:p-5">
				<!-- Header Row -->
				<div class="flex items-center justify-between border-b border-yonder-500/30 pb-2.5">
					<div class="flex items-center gap-2">
						<span
							class="rounded border border-neon-yellow px-2 py-0.5 text-[11px] font-extrabold tracking-wide text-neon-yellow uppercase"
						>
							JUDGE TOUR — STEP {appState.demoStep} / {DEMO_STEP_COUNT}
						</span>
						<span class="font-mono-telemetry text-xs font-semibold text-neon-yellow">
							{currentStepData.title}
						</span>
					</div>

					<button
						type="button"
						onclick={() => appState.endJudgeDemo()}
						class="flex items-center gap-1 rounded border border-yonder-500/40 bg-electric-blue/30 px-2 py-1 text-xs text-slate-200 transition-colors hover:border-neon-yellow hover:text-neon-yellow"
					>
						<span>Exit Tour</span>
						<X class="h-4 w-4" />
					</button>
				</div>

				<!-- Content Body -->
				<div class="my-3">
					<h3 class="text-sm leading-snug font-bold text-white sm:text-base">
						{currentStepData.headline}
					</h3>
					<p class="mt-1.5 text-xs leading-relaxed text-slate-200 sm:text-sm">
						{currentStepData.description}
					</p>
				</div>

				<!-- Bottom Controller Row -->
				<div class="flex items-center justify-between border-t border-yonder-500/30 pt-2">
					<div class="flex items-center gap-1">
						<button
							type="button"
							onclick={() => appState.prevDemoStep()}
							disabled={appState.demoStep <= 1}
							class="flex items-center gap-1 rounded-md border border-yonder-500/40 bg-electric-blue/40 px-3 py-1.5 text-xs font-bold tracking-wider text-white uppercase transition-colors hover:border-neon-yellow hover:text-neon-yellow disabled:opacity-40"
						>
							<ChevronLeft class="h-4 w-4" />
							<span>Back</span>
						</button>
					</div>

					<div class="flex items-center gap-2">
						<span class="hidden font-mono text-[11px] text-slate-300 sm:inline">
							[Press Space or Arrow keys]
						</span>
						<button
							type="button"
							onclick={() => appState.nextDemoStep()}
							class="brand-btn-primary rounded-md px-4 py-1.5 text-xs shadow-md"
						>
							<span>{currentStepData.actionText}</span>
							<ChevronRight class="h-4 w-4 stroke-[2.5]" />
						</button>
					</div>
				</div>
			</div>
		</div>
	</div>
{/if}
