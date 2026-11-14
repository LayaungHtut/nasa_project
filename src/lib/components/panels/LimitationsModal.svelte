<script lang="ts">
	import { appState } from '$lib/stores/appState.svelte';
	import { X, ShieldAlert, AlertTriangle, CheckCircle2, XCircle } from 'lucide-svelte';

	let event = $derived(appState.selectedEvent);
</script>

{#if appState.isLimitationsModalOpen}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-md"
		role="dialog"
		aria-modal="true"
		aria-labelledby="limitations-title"
	>
		<div
			class="relative flex max-h-[85vh] w-full max-w-3xl flex-col overflow-hidden rounded-xl border border-yonder-500/60 bg-deep-blue shadow-[0_0_50px_rgba(0,66,166,0.5)]"
		>
			<!-- Header -->
			<div
				class="brand-pattern-fiduciaries flex items-center justify-between border-b border-yonder-500/30 bg-deep-blue px-5 py-3.5"
			>
				<div class="flex items-center gap-2.5">
					<div
						class="flex h-8 w-8 items-center justify-center rounded-lg border border-rocket-red/70 bg-martian-red text-neon-yellow"
					>
						<ShieldAlert class="h-4 w-4" />
					</div>
					<div>
						<h2 id="limitations-title" class="text-sm font-bold text-white sm:text-base">
							Scientific Limitations & Responsible-Use Statement
						</h2>
						<p class="text-xs text-slate-300">
							Honest remote sensing boundaries per docs/science/limitations.md
						</p>
					</div>
				</div>

				<button
					type="button"
					onclick={() => {
						appState.isLimitationsModalOpen = false;
					}}
					class="rounded-lg border border-yonder-500/40 bg-electric-blue/30 p-1.5 text-slate-200 transition-colors hover:border-neon-yellow hover:text-neon-yellow"
					aria-label="Close modal"
				>
					<X class="h-4 w-4" />
				</button>
			</div>

			<!-- Body Content -->
			<div class="space-y-4 overflow-y-auto p-5 text-xs text-slate-200">
				<!-- What We Can Claim vs What We Must Not Claim -->
				<div class="grid grid-cols-1 gap-3 md:grid-cols-2">
					<div class="rounded-lg border border-yonder-500/50 bg-electric-blue/35 p-3">
						<div class="mb-1.5 flex items-center gap-1.5 text-xs font-bold text-neon-yellow">
							<CheckCircle2 class="h-4 w-4" />
							<span>What We Can Honestly Claim</span>
						</div>
						<ul class="list-inside list-disc space-y-1 text-[11px] leading-relaxed text-white">
							<li>NISAR acquired real, calibrated backscatter over this AOI.</li>
							<li>Our pipeline applied published Lee speckle filtering and dB thresholding.</li>
							<li>L-band microwaves penetrated monsoon clouds that blind optical cameras.</li>
							<li>Measurements report detected standing water area and confidence score.</li>
						</ul>
					</div>

					<div class="rounded-lg border border-rocket-red/70 bg-martian-red/90 p-3">
						<div class="mb-1.5 flex items-center gap-1.5 text-xs font-bold text-neon-yellow">
							<XCircle class="h-4 w-4" />
							<span>What We Must NOT Claim</span>
						</div>
						<ul class="list-inside list-disc space-y-1 text-[11px] leading-relaxed text-white">
							<li>
								"NASA detected this flood" (NASA provided raw data; YOUTHs ran the detection).
							</li>
							<li>
								"AI independently discovered an event" (AI only explains our computed numbers).
							</li>
							<li>Casualties or human displacement without validated external census data.</li>
							<li>That this threshold generalizes globally without regional calibration.</li>
						</ul>
					</div>
				</div>

				<!-- Event Specific Documented Limitations -->
				<div>
					<h3
						class="mb-2 flex items-center gap-1.5 text-[11px] font-bold tracking-wider text-white uppercase"
					>
						<AlertTriangle class="h-4 w-4 text-neon-yellow" />
						<span>Documented Methodological Failure Modes ({event.processing.method})</span>
					</h3>
					<div class="space-y-2">
						{#each event.processing.limitations as limitation, i (i)}
							<div
								class="flex items-start gap-2.5 rounded-md border border-yonder-500/30 bg-electric-blue/25 p-2.5 text-xs text-slate-100"
							>
								<span
									class="flex h-5 w-5 shrink-0 items-center justify-center rounded border border-rocket-red/60 bg-martian-red font-mono text-[10px] font-bold text-neon-yellow"
								>
									{i + 1}
								</span>
								<p class="leading-relaxed">{limitation}</p>
							</div>
						{/each}
					</div>
				</div>

				{#if event.statistics?.water_loss_area_km2}
					<div class="rounded-lg border border-rocket-red/70 bg-martian-red/90 p-3.5 text-white">
						<div class="flex items-center gap-2 text-xs font-bold text-neon-yellow">
							<AlertTriangle class="h-4 w-4 text-neon-yellow" />
							<span
								>Scientific Investigation Finding: Apparent Water Loss ({event.statistics
									.water_loss_area_km2} km²)</span
							>
						</div>
						<p class="mt-1.5 text-[11px] leading-relaxed text-white">
							The automated two-pass comparison detected {event.statistics.water_loss_area_km2} km² ({event.statistics.water_loss_pixels?.toLocaleString()}
							cells) of apparent water loss in the baseline water body. Surface roughness is a plausible
							explanation for the changed backscatter, but its cause has not been independently confirmed.
							These classifications alone do not establish reservoir drawdown.
						</p>
					</div>
				{/if}

				<!-- Disclaimer Banner -->
				<div
					class="rounded-lg border border-yonder-500/30 bg-electric-blue/25 p-3 text-[11px] text-slate-200"
				>
					<strong class="text-neon-yellow">Official Attribution Notice:</strong> Observations labeled
					REAL originate from NASA-ISRO NISAR via ASF DAAC. Synthetic demonstrations are labeled separately.
					Algorithmic processing and interpretation is conducted by Team YOUTHs for the NASA Space Apps
					Challenge 2026. This demonstration is not certified for emergency dispatch or life-critical
					rescue operations.
				</div>
			</div>
		</div>
	</div>
{/if}
