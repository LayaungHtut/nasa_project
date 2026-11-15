<script lang="ts">
	import { appState } from '$lib/stores/appState.svelte';
	import { TOUR_STEPS } from '$lib/data/tour';
	import { X, ChevronLeft, ChevronRight } from 'lucide-svelte';

	let step = $derived(TOUR_STEPS[appState.demoStep - 1]);

	function handleKeydown(e: KeyboardEvent) {
		if (!appState.isDemoModeActive) return;
		if (e.key === 'ArrowRight' || e.key === ' ') appState.goToDemoStep(appState.demoStep + 1);
		else if (e.key === 'ArrowLeft') appState.goToDemoStep(Math.max(1, appState.demoStep - 1));
		else if (e.key === 'Escape') appState.goToDemoStep(0);
		else return;
		e.preventDefault();
	}
</script>

<svelte:window onkeydown={handleKeydown} />

{#if step}
	<div
		class="fixed inset-x-0 bottom-3 z-40 mx-auto max-w-3xl px-3 select-none sm:bottom-6 sm:px-4"
		role="region"
		aria-label="Judge tour"
	>
		<div
			class="brand-pattern-orbits overflow-hidden rounded-xl border-2 border-neon-yellow/80 bg-deep-blue/95 text-slate-200 shadow-[0_0_40px_rgba(0,66,166,0.6)] backdrop-blur-md"
		>
			<div class="flex h-1.5 w-full bg-electric-blue/50">
				<div
					class="bg-neon-yellow transition-all duration-300"
					style:width="{(appState.demoStep / TOUR_STEPS.length) * 100}%"
				></div>
			</div>

			<div class="p-3 sm:p-5">
				<div class="flex items-center justify-between gap-2 border-b border-yonder-500/30 pb-2">
					<div class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
						<span
							class="rounded border border-neon-yellow px-2 py-0.5 text-[11px] font-extrabold tracking-wide whitespace-nowrap text-neon-yellow uppercase"
						>
							Judge tour · {appState.demoStep} / {TOUR_STEPS.length}
						</span>
						<span class="font-mono-telemetry text-xs font-semibold text-slate-200">
							{step.title}
						</span>
						{#if step.dataStatus === 'REAL'}
							<span
								class="rounded border border-neon-yellow/60 px-1.5 py-0.5 text-[10px] font-bold tracking-wider text-neon-yellow uppercase"
							>
								Real NISAR data
							</span>
						{:else}
							<span
								class="rounded border border-rocket-red bg-martian-red px-1.5 py-0.5 text-[10px] font-bold tracking-wider text-white uppercase"
							>
								Simulated demo
							</span>
						{/if}
					</div>
					<button
						type="button"
						onclick={() => appState.goToDemoStep(0)}
						class="flex shrink-0 items-center gap-1 rounded border border-yonder-500/40 bg-electric-blue/30 px-2 py-1 text-xs text-slate-200 transition-colors hover:border-neon-yellow hover:text-neon-yellow"
					>
						<span>Exit tour</span>
						<X class="h-4 w-4" />
					</button>
				</div>

				<div class="my-2.5 sm:my-3" aria-live="polite">
					<h3 class="text-sm leading-snug font-bold text-white sm:text-base">{step.headline}</h3>
					<p class="mt-1.5 text-xs leading-relaxed text-slate-200 sm:text-sm">
						{step.description}
					</p>
				</div>

				<div class="flex items-center justify-between border-t border-yonder-500/30 pt-2">
					<button
						type="button"
						onclick={() => appState.goToDemoStep(appState.demoStep - 1)}
						disabled={appState.demoStep <= 1}
						class="flex items-center gap-1 rounded-md border border-yonder-500/40 bg-electric-blue/40 px-3 py-1.5 text-xs font-bold tracking-wider text-white uppercase transition-colors hover:border-neon-yellow hover:text-neon-yellow disabled:opacity-40"
					>
						<ChevronLeft class="h-4 w-4" />
						<span>Back</span>
					</button>
					<div class="flex items-center gap-2">
						<span class="hidden font-mono text-[11px] text-slate-300 sm:inline">
							[Space or arrow keys · Esc to exit]
						</span>
						<button
							type="button"
							onclick={() => appState.goToDemoStep(appState.demoStep + 1)}
							class="brand-btn-primary flex items-center gap-1 rounded-md px-4 py-1.5 text-xs shadow-md"
						>
							<span>{step.actionText}</span>
							<ChevronRight class="h-4 w-4 stroke-[2.5]" />
						</button>
					</div>
				</div>
			</div>
		</div>
	</div>
{/if}
