<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import TopNav from '$lib/components/nav/TopNav.svelte';
	import SarExplainerModal from '$lib/components/panels/SarExplainerModal.svelte';
	import LimitationsModal from '$lib/components/panels/LimitationsModal.svelte';
	import DemoModeController from '$lib/components/stories/DemoModeController.svelte';
	import { appState } from '$lib/stores/appState.svelte';

	let { data, children } = $props();

	$effect(() => {
		if (data?.events) {
			appState.setEvents(data.events);
		}
	});
</script>

<svelte:head>
	<title>Dancing with the SARs — NASA NISAR Earth Explorer | Team YOUTHs</title>
	<meta
		name="description"
		content="Interactive geospatial application using NASA-ISRO NISAR radar data to visualize and explain Earth surface changes, flood inundation, and SAR remote sensing."
	/>
	<link rel="icon" href={favicon} />
	<link rel="preconnect" href="https://tiles.openfreemap.org" />
</svelte:head>

<div class="flex min-h-screen flex-col text-slate-100">
	<!-- Mission Top Navigation -->
	<TopNav />

	<!-- Main App Content -->
	<main class="flex flex-1 flex-col">
		{@render children()}
	</main>

	<!-- Global Modals & Controllers -->
	<SarExplainerModal />
	<LimitationsModal />
	<DemoModeController />
</div>
