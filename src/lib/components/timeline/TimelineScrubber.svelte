<script lang="ts">
	import { appState } from '$lib/stores/appState.svelte';
	import { observationTimeline } from '$lib/data/presentation';
	import { Calendar, Play, Pause } from 'lucide-svelte';

	let event = $derived(appState.selectedEvent);
	let observations = $derived(observationTimeline(event));
	let isPlaying = $state(false);

	$effect(() => {
		// Stop playback when the dataset changes.
		void appState.selectedEvent.id;
		isPlaying = false;
	});

	$effect(() => {
		if (!isPlaying || observations.length < 2) return;
		const timer = setInterval(() => {
			selectObservation((appState.selectedObservationIndex + 1) % observations.length);
		}, 1800);
		return () => clearInterval(timer);
	});

	function isSelected(idx: number): boolean {
		return appState.activeLayer === (idx === 0 ? 'baseline' : 'post');
	}

	function selectObservation(index: number) {
		appState.selectedObservationIndex = index;
		// Update active layer accordingly
		if (index === 0) {
			appState.activeLayer = 'baseline';
		} else {
			appState.activeLayer = 'post';
		}
	}

	function togglePlay() {
		isPlaying = !isPlaying;
	}
</script>

{#if observations.length > 0}
	<div
		class="rounded-lg border border-yonder-500/40 bg-deep-blue/95 p-3 text-xs text-slate-200 shadow-xl backdrop-blur-md"
	>
		<div class="mb-2.5 flex items-center justify-between border-b border-yonder-500/30 pb-2">
			<div class="flex items-center gap-2">
				<Calendar class="h-4 w-4 text-yonder-400" />
				<span class="text-[11px] font-bold tracking-wider text-white uppercase">
					Acquisition Timeline (UTC)
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

			{#each observations as obs, idx (obs.granule_id)}
				{@const selected = isSelected(idx)}
				{@const dateStr = new Date(obs.date).toLocaleDateString('en-US', {
					month: 'short',
					day: 'numeric',
					timeZone: 'UTC'
				})}
				<div class="relative z-10 flex flex-col items-center">
					<button
						type="button"
						onclick={() => {
							isPlaying = false;
							selectObservation(idx);
						}}
						aria-label={`${obs.label}: ${dateStr} UTC`}
						aria-pressed={selected}
						class="flex h-6 w-6 items-center justify-center rounded-full border-2 transition-all {selected
							? 'scale-110 border-neon-yellow bg-electric-blue text-neon-yellow shadow-[0_0_12px_rgba(234,254,7,0.7)]'
							: 'border-yonder-500/50 bg-deep-blue text-slate-300 hover:border-neon-yellow hover:text-white'}"
						title={`${obs.label} (${dateStr})`}
					>
						{#if selected}
							<span class="h-2 w-2 rounded-full bg-neon-yellow"></span>
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
							class="hidden max-w-[70px] truncate text-[9px] sm:block {selected
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
{/if}
