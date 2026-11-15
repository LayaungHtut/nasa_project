<script lang="ts">
	import { formatAcquisitionDate } from '$lib/data/presentation';
	import { appState } from '$lib/stores/appState.svelte';
	import { ChevronsLeftRight, ArrowLeft, ArrowRight } from 'lucide-svelte';

	let containerEl = $state<HTMLDivElement | null>(null);
	let isDragging = $state(false);

	function handlePointerDown(e: PointerEvent) {
		isDragging = true;
		(e.target as HTMLElement).setPointerCapture(e.pointerId);
		updatePosition(e.clientX);
	}

	function handlePointerMove(e: PointerEvent) {
		if (!isDragging) return;
		updatePosition(e.clientX);
	}

	function handlePointerUp(e: PointerEvent) {
		isDragging = false;
		try {
			(e.target as HTMLElement).releasePointerCapture(e.pointerId);
		} catch {
			// ignore
		}
	}

	function updatePosition(clientX: number) {
		if (!containerEl) return;
		const rect = containerEl.getBoundingClientRect();
		const relativeX = clientX - rect.left;
		const pct = Math.max(0, Math.min(100, (relativeX / rect.width) * 100));
		appState.sliderPosition = Math.round(pct);
	}

	function handleKeyDown(e: KeyboardEvent) {
		if (e.key === 'ArrowLeft') {
			appState.sliderPosition = Math.max(0, appState.sliderPosition - 5);
			e.preventDefault();
		} else if (e.key === 'ArrowRight') {
			appState.sliderPosition = Math.min(100, appState.sliderPosition + 5);
			e.preventDefault();
		} else if (e.key === 'Home') {
			appState.sliderPosition = 0;
			e.preventDefault();
		} else if (e.key === 'End') {
			appState.sliderPosition = 100;
			e.preventDefault();
		}
	}

	let baselineDate = $derived(
		formatAcquisitionDate(appState.selectedEvent.observation_dates.baseline)
	);
	let postDate = $derived(
		formatAcquisitionDate(appState.selectedEvent.observation_dates.post_event)
	);
</script>

<div
	bind:this={containerEl}
	class="pointer-events-none absolute inset-0 z-20 overflow-hidden select-none"
	role="region"
	aria-label="Before and After Radar Comparison Slider"
>
	<!-- Left Side Label (Baseline) -->
	<div
		class="pointer-events-auto absolute top-24 left-3 z-30 flex max-w-[45%] items-center gap-2 rounded-md border border-yonder-500/50 bg-deep-blue/90 px-2.5 py-1.5 text-xs text-white shadow-lg backdrop-blur-sm"
	>
		<ArrowLeft class="h-3 w-3 text-yonder-400" />
		<div>
			<div class="text-[10px] font-semibold tracking-wider text-slate-300 uppercase">
				Baseline Observation
			</div>
			<div class="font-mono-telemetry font-bold text-yonder-400">{baselineDate}</div>
		</div>
	</div>

	<!-- Right Side Label (Post-Event) -->
	<div
		class="pointer-events-auto absolute top-24 right-3 z-30 flex max-w-[45%] items-center gap-2 rounded-md border border-neon-yellow/60 bg-deep-blue/90 px-2.5 py-1.5 text-right text-xs text-white shadow-lg backdrop-blur-sm"
	>
		<div>
			<div class="text-[10px] font-semibold tracking-wider text-slate-300 uppercase">
				Repeat Observation
			</div>
			<div class="font-mono-telemetry font-bold text-neon-yellow">{postDate}</div>
		</div>
		<ArrowRight class="h-3 w-3 text-neon-yellow" />
	</div>

	<!-- Vertical Divider Line -->
	<div
		class="absolute top-0 bottom-0 z-20 w-[2px] bg-neon-yellow shadow-[0_0_12px_rgba(234,254,7,0.85)]"
		style="left: {appState.sliderPosition}%;"
	></div>

	<!-- Draggable Slider Handle -->
	<div
		role="slider"
		tabindex="0"
		aria-valuenow={appState.sliderPosition}
		aria-valuemin="0"
		aria-valuemax="100"
		aria-label="Radar Comparison Divider"
		onpointerdown={handlePointerDown}
		onpointermove={handlePointerMove}
		onpointerup={handlePointerUp}
		onkeydown={handleKeyDown}
		class="pointer-events-auto absolute top-1/2 z-30 flex h-11 w-11 -translate-x-1/2 -translate-y-1/2 cursor-ew-resize touch-none items-center justify-center rounded-full border-2 border-neon-yellow bg-deep-blue text-neon-yellow shadow-[0_0_20px_rgba(0,66,166,0.8)] transition-transform hover:scale-110 focus:ring-2 focus:ring-neon-yellow focus:outline-none active:scale-95"
		style="left: {appState.sliderPosition}%;"
	>
		<ChevronsLeftRight class="h-5 w-5" />
	</div>
</div>
