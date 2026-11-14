<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import TopNav from '$lib/components/nav/TopNav.svelte';
	import SarExplainerModal from '$lib/components/panels/SarExplainerModal.svelte';
	import JudgeTour from '$lib/components/tour/JudgeTour.svelte';

	let { children } = $props();
</script>

<svelte:head>
	<title>Dancing with the SARs — NISAR Myanmar Surface Watch | Team YOUTHs</title>
	<meta
		name="description"
		content="SAR monitoring and early-warning demo for remote Myanmar: permit-compliance checks for mining and forensic linking of landslides to downstream river diversion, using NISAR-style radar and InSAR (simulated scenarios)."
	/>
	<link rel="icon" href={favicon} />
	<link rel="preconnect" href="https://tiles.openfreemap.org" />
</svelte:head>

<div class="flex min-h-screen flex-col text-slate-100">
	<TopNav />
	<main class="flex flex-1 flex-col">
		{@render children()}
	</main>
	<SarExplainerModal />
	<JudgeTour />
</div>
