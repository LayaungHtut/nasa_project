<script lang="ts">
	import { appState } from '$lib/stores/appState.svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { BookOpen, ArrowRight, MapPin, Radio } from 'lucide-svelte';

	function exploreStory(id: string) {
		appState.selectEvent(id);
		goto(resolve('/'));
	}
</script>

<div class="mx-auto max-w-7xl flex-1 px-4 py-8 sm:px-6 lg:px-8">
	<!-- Hero header -->
	<div
		class="brand-pattern-orbits rounded-2xl border border-yonder-500/40 bg-deep-blue/90 p-6 shadow-xl sm:p-8"
	>
		<div
			class="inline-flex items-center gap-2 rounded-full border border-neon-yellow/60 bg-electric-blue/50 px-3 py-1 text-xs font-bold tracking-wider text-neon-yellow uppercase"
		>
			<BookOpen class="h-4 w-4" />
			<span>Curated Scientific Narratives</span>
		</div>
		<h1 class="mt-3 text-2xl font-black text-white sm:text-4xl">
			Stories from the Radar Looking Glass
		</h1>
		<!-- Brand Guide Pages 12-16: Subheading paragraphs alternating between colors like stripes on the flag -->
		<p class="mt-3 max-w-3xl text-sm leading-relaxed sm:text-base">
			<span class="block font-medium text-neon-yellow">
				Radar sees through clouds and darkness, but its signal still has to be interpreted.
			</span>
			<span class="mt-1 block text-white">
				NISAR’s L-band radar measures how the ground scatters microwaves; these stories show what
				that signal can tell us, and what still needs checking.
			</span>
		</p>
	</div>

	<!-- Stories List -->
	<div class="mt-10 space-y-8">
		{#each appState.events as evt, index (evt.id)}
			<article
				class="brand-pattern-voronoi overflow-hidden rounded-2xl border border-yonder-500/40 bg-deep-blue/95 shadow-2xl transition-all hover:border-yonder-400"
			>
				<div class="grid grid-cols-1 lg:grid-cols-12">
					<!-- Story narrative side -->
					<div class="flex flex-col justify-between p-6 sm:p-8 lg:col-span-7">
						<div>
							<div class="flex flex-wrap items-center gap-2 text-xs">
								{#if evt.data_status === 'REAL'}
									<span
										class="rounded border border-neon-yellow/70 bg-deep-blue px-2 py-0.5 font-mono text-[10px] font-bold text-neon-yellow"
									>
										REAL NISAR DATA
									</span>
								{:else}
									<span
										class="rounded border border-rocket-red bg-martian-red px-2 py-0.5 font-mono text-[10px] font-bold text-white"
									>
										SYNTHETIC DEMO
									</span>
								{/if}
								<span
									class="rounded border border-yonder-500/50 bg-electric-blue/60 px-2.5 py-0.5 font-mono text-[11px] font-bold text-white"
								>
									STORY 0{index + 1}
								</span>
								<span class="text-yonder-500">•</span>
								<span class="font-mono text-slate-200"
									>{evt.source_products[0]?.product} Observation</span
								>
								<span class="text-yonder-500">•</span>
								<div class="flex items-center gap-1 text-slate-200">
									<MapPin class="h-4 w-4 text-neon-yellow" />
									<span>{evt.location.name}</span>
								</div>
							</div>

							<h2 class="mt-3 text-xl font-bold text-white sm:text-2xl">
								{evt.curated_story?.headline ?? evt.title}
							</h2>
							<p class="mt-2 text-xs leading-relaxed text-slate-200 sm:text-sm">
								{evt.curated_story?.context ?? evt.summary}
							</p>

							<!-- Key Radar Scientific Principle -->
							<div class="mt-4 rounded-xl border border-yonder-500/40 bg-electric-blue/35 p-4">
								<div
									class="flex items-center gap-2 text-xs font-bold tracking-wider text-neon-yellow uppercase"
								>
									<Radio class="h-4 w-4" />
									<span>What the Radar Signal Shows</span>
								</div>
								<p class="mt-1.5 text-xs leading-relaxed text-white">
									{evt.curated_story?.radar_insight}
								</p>
							</div>

							{#if evt.curated_story?.quote}
								<blockquote
									class="mt-4 border-l-2 border-neon-yellow pl-3 text-xs text-slate-200 italic"
								>
									"{evt.curated_story.quote}"
								</blockquote>
							{/if}
						</div>

						<!-- Bottom CTA bar -->
						<div
							class="mt-6 flex flex-wrap items-center justify-between gap-4 border-t border-yonder-500/30 pt-4"
						>
							<div class="font-mono-telemetry flex items-center gap-4 text-xs text-slate-300">
								<div>
									<span class="block font-sans text-[10px] text-slate-300 uppercase">
										{evt.phenomenon === 'surface_deformation' ? 'Strain Zone' : 'Candidate Area'}
									</span>
									<span class="text-sm font-extrabold text-yonder-400"
										>{evt.results.change_area_km2} km²</span
									>
								</div>
								<div>
									<span class="block font-sans text-[10px] text-slate-300 uppercase">
										Detection Score
									</span>
									<span class="text-sm font-extrabold text-neon-yellow">
										{evt.results.confidence.toFixed(3)} / 1
									</span>
								</div>
							</div>

							<button
								type="button"
								onclick={() => exploreStory(evt.id)}
								class="brand-btn-primary rounded-lg px-4 py-2 text-xs shadow-lg"
							>
								<span>Launch Interactive Map</span>
								<ArrowRight class="h-4 w-4" />
							</button>
						</div>
					</div>

					<!-- Visual data preview side -->
					<div
						class="brand-pattern-fiduciaries flex flex-col justify-center border-t border-yonder-500/30 bg-deep-blue p-6 lg:col-span-5 lg:border-t-0 lg:border-l"
					>
						<div class="rounded-xl border border-yonder-500/40 bg-electric-blue/25 p-4 text-xs">
							<div class="flex items-center justify-between border-b border-yonder-500/30 pb-2">
								<span class="text-[10px] font-bold tracking-wider text-white uppercase">
									Scientific Provenance
								</span>
								<span class="font-mono text-[10px] font-bold text-neon-yellow"
									>ASF DAAC Archive</span
								>
							</div>

							<div class="font-mono-telemetry mt-3 space-y-2 text-[11px]">
								<div class="flex justify-between">
									<span class="font-sans text-slate-300">Mission:</span>
									<span class="text-white">NASA-ISRO NISAR</span>
								</div>
								<div class="flex justify-between">
									<span class="font-sans text-slate-300">Product Type:</span>
									<span class="font-bold text-yonder-400">{evt.source_products[0]?.product}</span>
								</div>
								<div class="flex justify-between">
									<span class="font-sans text-slate-300">Polarization:</span>
									<span class="text-white">{evt.source_products[0]?.polarization ?? 'HH'}</span>
								</div>
								<div class="flex justify-between">
									<span class="font-sans text-slate-300">Acquisitions:</span>
									<span class="text-white"
										>{evt.observation_dates.all_observations?.length ?? 2} scenes</span
									>
								</div>
							</div>

							<div class="mt-4 rounded border border-yonder-500/30 bg-deep-blue p-2.5">
								<span class="block font-sans text-[10px] text-slate-300"
									>Primary Calibrated Granule:</span
								>
								<span class="font-mono text-[10px] break-all text-yonder-400 select-all">
									{evt.source_products[1]?.granule_id ?? evt.source_products[0]?.granule_id}
								</span>
							</div>
						</div>
					</div>
				</div>
			</article>
		{/each}
	</div>
</div>
