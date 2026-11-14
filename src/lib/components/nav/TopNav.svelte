<script lang="ts">
	import { appState } from '$lib/stores/appState.svelte';
	import SpaceAppsLogo from '$lib/components/brand/SpaceAppsLogo.svelte';
	import { Radio, Info, Globe2, Play } from 'lucide-svelte';
	import { page } from '$app/state';
	import { resolve } from '$app/paths';
	import { goto } from '$app/navigation';

	async function startTour() {
		if (page.url.pathname !== '/') await goto(resolve('/'));
		appState.goToDemoStep(1);
	}
</script>

<header
	class="brand-pattern-orbits sticky top-0 z-40 w-full border-b border-slate-800/90 bg-deep-blue/95 px-4 py-2.5 backdrop-blur-md"
>
	<div class="mx-auto flex max-w-7xl items-center justify-between gap-3">
		<!-- Left: Official NASA Space Apps Default / Small responsive logo + Mission title -->
		<div class="flex items-center gap-3">
			<a href={resolve('/')} class="group flex items-center gap-3">
				<div class="flex shrink-0 items-center">
					<SpaceAppsLogo variant="default" class="hidden h-9 w-auto sm:block" />
					<SpaceAppsLogo variant="small" class="h-9 w-9 sm:hidden" />
				</div>
				<div class="h-7 w-[1px] bg-slate-700/80"></div>
				<div>
					<div class="flex items-center gap-2">
						<span class="font-mono text-[10px] font-bold tracking-widest text-yonder-300 uppercase">
							2026 Earth Science
						</span>
						<span
							class="hidden rounded border border-neon-yellow/40 bg-electric-blue/50 px-1.5 py-0.5 text-[10px] font-bold tracking-wider text-neon-yellow uppercase sm:inline-block"
						>
							Yangon
						</span>
					</div>
					<h1 class="text-sm font-black text-white sm:text-base">
						Dancing with the SARs
						<span
							class="font-sans text-xs font-normal tracking-normal whitespace-nowrap text-slate-300 normal-case"
						>
							Team YOUTHs
						</span>
					</h1>
				</div>
			</a>

			<!-- Orbit status indicator -->
			<div
				class="hidden items-center gap-1.5 rounded-full border border-yonder-500/40 bg-electric-blue/30 px-2.5 py-1 text-[11px] text-white xl:flex"
			>
				<span class="relative flex h-2 w-2">
					<span
						class="absolute inline-flex h-full w-full animate-ping rounded-full bg-neon-yellow opacity-75"
					></span>
					<span class="relative inline-flex h-2 w-2 rounded-full bg-neon-yellow"></span>
				</span>
				<span class="font-mono-telemetry font-medium">NISAR L-band Active (24cm)</span>
			</div>
		</div>

		<!-- Center: Navigation -->
		<nav
			class="hidden items-center gap-1.5 text-xs font-bold tracking-wider text-slate-200 uppercase md:flex"
		>
			<a
				href={resolve('/')}
				class="flex items-center gap-1.5 rounded-md px-3 py-1.5 transition-colors {page.url
					.pathname === '/'
					? 'border border-neon-yellow/60 bg-electric-blue/50 text-neon-yellow'
					: 'hover:bg-electric-blue/30 hover:text-white'}"
			>
				<Globe2 class="h-4 w-4 text-yonder-400" />
				<span>Surface Watch</span>
			</a>
			<a
				href={resolve('/about')}
				class="flex items-center gap-1.5 rounded-md px-3 py-1.5 transition-colors {page.url
					.pathname === '/about'
					? 'border border-neon-yellow/60 bg-electric-blue/50 text-neon-yellow'
					: 'hover:bg-electric-blue/30 hover:text-white'}"
			>
				<Info class="h-4 w-4 text-yonder-400" />
				<span>Science & Team</span>
			</a>
		</nav>

		<!-- Right: judge tour + SAR explainer -->
		<div class="flex items-center gap-2">
			<button
				type="button"
				onclick={startTour}
				class="brand-btn-primary flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs shadow-md active:scale-[0.98]"
			>
				<Play class="h-4 w-4 fill-deep-blue" />
				<span>Judge Tour</span>
				<span
					class="hidden rounded bg-deep-blue/15 px-1 font-mono text-[10px] tracking-tight text-deep-blue sm:inline"
				>
					2 min
				</span>
			</button>
			<!-- SAR Physics Explainer button -->
			<button
				type="button"
				onclick={() => {
					appState.isSarModalOpen = true;
				}}
				class="flex items-center gap-1.5 rounded-md border border-yonder-400/50 bg-electric-blue/40 px-3 py-1.5 text-xs font-bold tracking-wider text-white uppercase transition-colors hover:border-neon-yellow hover:text-neon-yellow"
			>
				<Radio class="h-4 w-4 animate-pulse text-neon-yellow" />
				<span class="hidden sm:inline">How NISAR Sees It</span>
				<span class="sm:hidden">SAR 101</span>
			</button>
		</div>
	</div>
</header>
