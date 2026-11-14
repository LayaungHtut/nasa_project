<script lang="ts">
	import { formatAcquisitionDate } from '$lib/data/presentation';
	import type { Provenance } from '$lib/types/api';
	import { Database, ExternalLink, ShieldCheck } from 'lucide-svelte';

	let { provenance, processingMethod }: { provenance?: Provenance; processingMethod?: string } =
		$props();
</script>

{#if provenance}
	<div
		title={processingMethod ? `Processing: ${processingMethod}` : undefined}
		class="inline-flex flex-wrap items-center gap-2 rounded-md border border-slate-700/90 bg-deep-blue/95 px-3 py-1.5 text-xs text-slate-200 shadow-md backdrop-blur-sm"
	>
		<div class="flex items-center gap-1.5 font-bold text-neon-yellow">
			<ShieldCheck class="h-4 w-4" />
			<span>NASA / ISRO {provenance.mission}</span>
		</div>

		<span class="text-slate-600">|</span>

		<span
			class="rounded border border-yonder-500/30 bg-electric-blue/40 px-1.5 py-0.5 font-mono text-[11px] font-bold text-white"
		>
			{provenance.product} ({provenance.polarization ?? 'HH'})
		</span>

		<span class="text-slate-600">|</span>

		<span class="font-mono-telemetry text-slate-300">
			{formatAcquisitionDate(provenance.acquisition_date)}
		</span>

		<span class="text-slate-600">|</span>

		<a
			href="https://asf.alaska.edu"
			target="_blank"
			rel="noreferrer"
			class="brand-link-secondary flex items-center gap-1 text-[11px]"
			title={`Granule: ${provenance.granule_id}`}
		>
			<Database class="h-3 w-3" />
			<span>ASF DAAC</span>
			<ExternalLink class="h-3 w-3" />
		</a>
	</div>
{/if}
