<script lang="ts">
	import { appState } from '$lib/stores/appState.svelte';
	import { compliance, forensics, shortDate } from '$lib/data/scenarios';
	import { Calendar, Play, Pause, TriangleAlert } from 'lucide-svelte';

	let scenario = $derived(appState.scenario);
	let observations = $derived(scenario.epochs);
	/** Playback belongs to one module, so switching module stops it without an effect. */
	let playingId = $state<string | null>(null);
	let isPlaying = $derived(playingId === appState.scenarioId);
	/** Passes where an alert first fires get a marker on the track. */
	let flagged = $derived.by(() => {
		const s = scenario;
		if (s.module === 'mining') return new Set([compliance(s, 0).firstBreach]);
		const f = forensics(s, 0);
		return new Set([f.slideEpoch, f.diversionEpoch]);
	});

	$effect(() => {
		if (!isPlaying) return;
		const timer = setInterval(() => {
			appState.epochIndex = (appState.epochIndex + 1) % observations.length;
		}, 1600);
		return () => clearInterval(timer);
	});

	function togglePlay() {
		if (!isPlaying && appState.epochIndex === observations.length - 1) appState.epochIndex = 0;
		playingId = isPlaying ? null : appState.scenarioId;
	}
</script>

<div
	class="rounded-lg border border-yonder-500/40 bg-deep-blue/95 p-3 text-xs text-slate-200 shadow-xl backdrop-blur-md"
>
	<div class="mb-2.5 flex items-center justify-between border-b border-yonder-500/30 pb-2">
		<div class="flex items-center gap-2">
			<Calendar class="h-4 w-4 text-yonder-400" />
			<span class="text-[11px] font-bold tracking-wider text-white uppercase">
				{observations.length} NISAR passes · {scenario.sensor.repeat_days}-day repeat · simulated
			</span>
		</div>
		<div class="flex items-center gap-1.5">
			<button
				type="button"
				onclick={togglePlay}
				disabled={observations.length < 2}
				class="brand-btn-primary rounded px-2 py-0.5 text-[10px]"
			>
				{#if isPlaying}
					<Pause class="h-3 w-3" />
					<span>Pause</span>
				{:else}
					<Play class="h-3 w-3 fill-current" />
					<span>Play observations</span>
				{/if}
			</button>
		</div>
	</div>

	<!-- Horizontal Timeline Track -->
	<div class="relative flex items-center justify-between px-3 pt-2 pb-1">
		<!-- Track line -->
		<div class="absolute top-5 right-6 left-6 h-0.5 bg-electric-blue"></div>

		{#each observations as obs, idx (obs.date)}
			{@const selected = appState.epochIndex === idx}
			{@const dateStr = `Day ${obs.day} · ${shortDate(obs.date)}`}
			<div class="relative z-10 flex flex-col items-center">
				<button
					type="button"
					onclick={() => {
						playingId = null;
						appState.epochIndex = idx;
					}}
					aria-label={`${obs.label}: ${dateStr}`}
					aria-pressed={selected}
					class="flex h-6 w-6 items-center justify-center rounded-full border-2 transition-all {selected
						? 'scale-110 border-neon-yellow bg-electric-blue text-neon-yellow shadow-[0_0_12px_rgba(234,254,7,0.7)]'
						: 'border-yonder-500/50 bg-deep-blue text-slate-300 hover:border-neon-yellow hover:text-white'}"
					title={`${obs.label} (${dateStr})`}
				>
					{#if selected}
						<span class="h-2 w-2 rounded-full bg-neon-yellow"></span>
					{:else if flagged.has(idx)}
						<TriangleAlert class="h-3 w-3 text-[#ff7f5c]" />
					{:else}
						<span class="font-mono text-[9px]">{idx + 1}</span>
					{/if}
				</button>

				<!-- Date and label below node -->
				<div class="mt-1 text-center">
					<span
						class="font-mono-telemetry block text-[10px] {selected
							? 'font-bold text-neon-yellow'
							: 'text-slate-300'}"
					>
						{dateStr}
					</span>
					<span
						class="hidden max-w-[110px] truncate text-[9px] sm:block {selected
							? 'font-medium text-white'
							: 'text-slate-400'}"
					>
						{obs.label}
					</span>
				</div>
			</div>
		{/each}
	</div>
</div>
