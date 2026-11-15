<script lang="ts">
	import { appState } from '$lib/stores/appState.svelte';
	import { SCENARIOS } from '$lib/data/scenarios';
	import ScenarioMap from '$lib/components/map/ScenarioMap.svelte';
	import TimelineScrubber from '$lib/components/timeline/TimelineScrubber.svelte';
	import CompliancePanel from '$lib/components/panels/CompliancePanel.svelte';
	import ForensicsPanel from '$lib/components/panels/ForensicsPanel.svelte';
	import ObservedChangePanel from '$lib/components/panels/ObservedChangePanel.svelte';
	import MethodPanel from '$lib/components/panels/MethodPanel.svelte';
	import SpaceAppsLogo from '$lib/components/brand/SpaceAppsLogo.svelte';
	import { Radio, BookOpen, Pickaxe, Mountain, Satellite } from 'lucide-svelte';

	let scenario = $derived(appState.scenario);
	const icons = { observed: Satellite, mining: Pickaxe, landslide: Mountain };
	const labels = {
		observed: 'Hpakant mining · real data',
		mining: 'Permit check · demo',
		landslide: 'Landslide & river · demo'
	};
	const modules = SCENARIOS.map((s) => ({
		id: s.id,
		label: labels[s.module],
		icon: icons[s.module]
	}));
</script>

<div class="flex flex-1 flex-col overflow-hidden">
	<!-- Module selector and telemetry bar -->
	<section
		class="brand-pattern-fiduciaries border-b border-slate-800 bg-deep-blue/90 px-4 py-2 text-xs text-slate-200 backdrop-blur-sm"
		aria-label="Module selector"
	>
		<div class="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3">
			<div class="flex flex-wrap items-center gap-2" role="group" aria-label="Monitoring module">
				{#each modules as mod (mod.id)}
					{@const active = appState.scenarioId === mod.id}
					<button
						type="button"
						aria-pressed={active}
						onclick={() => appState.selectScenario(mod.id)}
						class="flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs font-bold transition-colors {active
							? 'border-neon-yellow/70 bg-electric-blue/50 text-neon-yellow'
							: 'border-yonder-500/50 bg-electric-blue/20 text-white hover:border-neon-yellow'}"
					>
						<mod.icon class="h-4 w-4" />
						<span>{mod.label}</span>
					</button>
				{/each}
				<span class="hidden text-slate-600 md:inline">|</span>
				<span class="hidden text-slate-300 md:inline"
					>{scenario.location.name}, {scenario.location.region}</span
				>
			</div>
			<div class="flex items-center gap-2">
				<span
					class="rounded border border-yonder-500/50 bg-electric-blue/50 px-2 py-0.5 font-mono text-[11px] font-semibold text-white"
				>
					NISAR {scenario.sensor.band} · {scenario.sensor.polarization}
				</span>
				{#if scenario.data_status === 'REAL'}
					<span
						class="rounded border border-neon-yellow/70 bg-electric-blue/60 px-1.5 py-0.5 font-mono text-[10px] font-bold text-neon-yellow"
					>
						REAL NISAR · ASF DAAC
					</span>
				{:else}
					<span
						class="rounded border border-rocket-red bg-martian-red px-1.5 py-0.5 font-mono text-[10px] font-bold text-white"
					>
						SIMULATED
					</span>
				{/if}
			</div>
		</div>
	</section>

	<div
		class="relative flex flex-1 flex-col overflow-hidden lg:h-[calc(100dvh-7.25rem)] lg:flex-none lg:flex-row"
	>
		<section
			class="relative flex h-[62vh] min-h-[440px] shrink-0 flex-col lg:h-auto lg:min-h-0 lg:flex-1"
			aria-label="Interactive radar map"
		>
			<div class="relative min-h-0 flex-1">
				<ScenarioMap />
			</div>
			<div class="shrink-0 border-t border-slate-800 bg-deep-blue/95 p-3">
				<TimelineScrubber />
			</div>
		</section>

		<aside
			class="flex w-full flex-col overflow-y-auto border-t border-slate-800 bg-deep-blue/95 lg:w-[420px] lg:border-t-0 lg:border-l xl:w-[460px]"
			aria-label="Analysis"
		>
			<div
				class="brand-pattern-orbits border-b border-slate-700/80 bg-gradient-to-br from-electric-blue/75 to-deep-blue p-4"
			>
				<div
					class="flex items-center gap-1.5 text-xs font-bold tracking-wider text-neon-yellow uppercase"
				>
					<BookOpen class="h-4 w-4" />
					<span>Why It Matters</span>
				</div>
				<h2 class="mt-1.5 text-base font-black text-white">{scenario.story.headline}</h2>
				<p class="mt-2 text-xs leading-relaxed text-slate-100">{scenario.story.context}</p>
				<div
					class="mt-3 rounded-lg border border-yonder-400/40 bg-deep-blue/85 p-2.5 text-xs text-slate-100"
				>
					<div
						class="mb-1 flex items-center gap-1.5 text-[11px] font-bold text-yonder-300 uppercase"
					>
						<Radio class="h-3 w-3 text-neon-yellow" />
						<span>Radar Remote Sensing Insight</span>
					</div>
					<p class="text-[11px] leading-relaxed text-slate-200">{scenario.story.radar_insight}</p>
				</div>
			</div>

			<div class="flex-1 space-y-4 p-4">
				{#if scenario.module === 'observed'}
					<ObservedChangePanel {scenario} />
				{:else if scenario.module === 'mining'}
					<CompliancePanel {scenario} />
				{:else}
					<ForensicsPanel {scenario} />
				{/if}
				<MethodPanel {scenario} />
			</div>

			<div
				class="flex items-center justify-center gap-2 border-t border-slate-800/80 bg-deep-blue p-3 text-center font-mono text-[10px] text-slate-400"
			>
				<SpaceAppsLogo variant="small" class="h-4 w-4" />
				<span>NASA-ISRO NISAR • ASF DAAC • SPACE APPS 2026 YANGON</span>
			</div>
		</aside>
	</div>
</div>
