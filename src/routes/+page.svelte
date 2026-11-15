<script lang="ts">
	import { appState } from '$lib/stores/appState.svelte';
	import MapContainer from '$lib/components/map/MapContainer.svelte';
	import ScientificTierPanel from '$lib/components/panels/ScientificTierPanel.svelte';
	import TimelineScrubber from '$lib/components/timeline/TimelineScrubber.svelte';
	import ProvenanceBadge from '$lib/components/nav/ProvenanceBadge.svelte';
	import SpaceAppsLogo from '$lib/components/brand/SpaceAppsLogo.svelte';
	import { Radio, MapPin, BookOpen, ChevronDown } from 'lucide-svelte';

	let event = $derived(appState.selectedEvent);
	let isEventDropdownOpen = $state(false);
	// Real observations first; synthetic scenarios stay available but are grouped apart from them.
	let eventGroups = $derived(
		[
			{
				label: 'NASA NISAR observations',
				items: appState.events.filter((e) => e.data_status === 'REAL')
			},
			{
				label: 'Teaching scenarios (synthetic, not observations)',
				items: appState.events.filter((e) => e.data_status !== 'REAL')
			}
		].filter((g) => g.items.length)
	);
</script>

<div class="flex flex-1 flex-col overflow-hidden">
	<!-- Sub-header / Event Telemetry Bar -->
	<section
		class="brand-pattern-fiduciaries border-b border-slate-800 bg-deep-blue/90 px-4 py-2 text-xs text-slate-200 backdrop-blur-sm"
		aria-label="Mission Telemetry Bar"
	>
		<div class="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3">
			<!-- Event Selector Pill -->
			<div class="flex items-center gap-2">
				<div class="relative">
					<button
						type="button"
						onclick={() => {
							isEventDropdownOpen = !isEventDropdownOpen;
						}}
						class="flex items-center gap-2 rounded-lg border border-yonder-500/50 bg-electric-blue/35 px-3 py-1.5 text-xs font-bold text-white shadow-sm transition-colors hover:border-neon-yellow"
					>
						<MapPin class="h-4 w-4 text-neon-yellow" />
						<span>{event.title}</span>
						<ChevronDown class="h-4 w-4 text-yonder-300" />
					</button>

					{#if isEventDropdownOpen}
						<div
							class="absolute top-full left-0 z-50 mt-1 w-72 rounded-lg border border-slate-700 bg-deep-blue p-1.5 shadow-2xl backdrop-blur-md"
						>
							{#each eventGroups as group (group.label)}
								<div
									class="mt-1 px-2 py-1 text-[10px] font-bold tracking-wider text-yonder-300 uppercase first:mt-0"
								>
									{group.label}
								</div>
								{#each group.items as item (item.id)}
									<button
										type="button"
										onclick={() => {
											appState.selectEvent(item.id);
											isEventDropdownOpen = false;
										}}
										class="flex w-full flex-col rounded-md px-2.5 py-1.5 text-left text-xs transition-colors {appState.selectedEventId ===
										item.id
											? 'border border-neon-yellow/50 bg-electric-blue/50 font-semibold text-white'
											: 'text-slate-300 hover:bg-slate-800 hover:text-white'}"
									>
										<div class="flex items-center justify-between gap-1.5">
											<span class="truncate font-medium">{item.title}</span>
											{#if item.data_status === 'REAL'}
												<span
													class="shrink-0 rounded border border-neon-yellow/60 bg-deep-blue px-1.5 py-0.5 font-mono text-[9px] font-bold text-neon-yellow"
												>
													REAL
												</span>
											{:else}
												<span
													class="shrink-0 rounded border border-rocket-red/60 bg-martian-red px-1.5 py-0.5 font-mono text-[9px] font-bold text-white"
												>
													SYNTHETIC
												</span>
											{/if}
										</div>
										<span class="font-mono-telemetry text-[10px] text-slate-300">
											{item.location.name} • {item.results.change_area_km2} km²
										</span>
									</button>
								{/each}
							{/each}
						</div>
					{/if}
				</div>

				<span class="hidden text-slate-600 md:inline">|</span>

				<div class="hidden items-center gap-1.5 text-slate-300 md:flex">
					<span class="font-mono-telemetry text-[11px] font-bold text-yonder-400">
						[{event.location.center[0].toFixed(2)}°E, {event.location.center[1].toFixed(2)}°N]
					</span>
				</div>
			</div>

			<!-- Provenance & Source Badge -->
			<div class="flex items-center gap-2">
				<ProvenanceBadge
					provenance={event.source_products[1] ?? event.source_products[0]}
					processingMethod={event.processing.method}
				/>
			</div>
		</div>
	</section>

	<!-- Main Exploration Stage -->
	<div
		class="relative flex flex-1 flex-col overflow-hidden lg:h-[calc(100dvh-7.25rem)] lg:flex-none lg:flex-row"
	>
		<!-- Left / Main: The Geospatial Map -->
		<section
			class="relative flex h-[60vh] min-h-[420px] shrink-0 flex-col lg:h-auto lg:min-h-0 lg:flex-1"
			aria-label="Interactive Radar Map"
		>
			<div class="relative min-h-0 flex-1">
				<MapContainer />
			</div>

			<!-- Floating bottom timeline inside map container -->
			<div class="shrink-0 border-t border-slate-800 bg-deep-blue/95 p-3">
				<TimelineScrubber />
			</div>
		</section>

		<!-- Right: Scientific Details & Grounded Analysis Panel -->
		<aside
			class="flex w-full flex-col overflow-y-auto border-t border-slate-800 bg-deep-blue/95 lg:w-[420px] lg:border-t-0 lg:border-l xl:w-[460px]"
			aria-label="Observation Science and Analysis"
		>
			<!-- Story & Context Card (Brand Guide p. 12: Electric Blue section contrasting against Deep Blue) -->
			<div
				class="brand-pattern-orbits border-b border-slate-700/80 bg-gradient-to-br from-electric-blue/75 to-deep-blue p-4"
			>
				<div
					class="flex items-center gap-1.5 text-xs font-bold tracking-wider text-neon-yellow uppercase"
				>
					<BookOpen class="h-4 w-4" />
					<span>Why It Matters</span>
				</div>
				<h2 class="mt-1.5 text-base font-black text-white">
					{event.curated_story?.headline ?? event.title}
				</h2>
				<p class="mt-2 text-xs leading-relaxed text-slate-100">
					{event.curated_story?.context ?? event.summary}
				</p>

				{#if event.curated_story?.radar_insight}
					<div
						class="mt-3 rounded-lg border border-yonder-400/40 bg-deep-blue/85 p-2.5 text-xs text-slate-100"
					>
						<div
							class="mb-1 flex items-center gap-1.5 text-[11px] font-bold text-yonder-300 uppercase"
						>
							<Radio class="h-3 w-3 text-neon-yellow" />
							<span>Radar Remote Sensing Insight</span>
						</div>
						<p class="text-[11px] leading-relaxed text-slate-200">
							{event.curated_story.radar_insight}
						</p>
					</div>
				{/if}

				{#if event.curated_story?.quote}
					<blockquote
						class="mt-3 border-l-2 border-neon-yellow pl-3 text-[11px] text-slate-200 italic"
					>
						"{event.curated_story.quote}"
					</blockquote>
				{/if}
			</div>

			<!-- Three-Tier Scientific Provenance Panel -->
			<div class="flex-1 space-y-4 p-4">
				<ScientificTierPanel />
			</div>

			<!-- Footer Attribution -->
			<div
				class="flex items-center justify-center gap-2 border-t border-slate-800/80 bg-deep-blue p-3 text-center font-mono text-[10px] text-slate-400"
			>
				<SpaceAppsLogo variant="small" class="h-4 w-4" />
				<span>NASA-ISRO NISAR • ASF DAAC • SPACE APPS 2026 YANGON</span>
			</div>
		</aside>
	</div>
</div>
