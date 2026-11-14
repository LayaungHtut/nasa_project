<script lang="ts">
	import { appState } from '$lib/stores/appState.svelte';
	import { formatAcquisitionDate } from '$lib/data/presentation';
	import { timeGap } from '$lib/data/evidence';
	import { resolve } from '$app/paths';
	let evidence = $derived(appState.opticalEvidence);
	let scene = $derived(appState.opticalScene);
	let candidate = $derived(appState.selectedCandidate);
</script>

{#if evidence && scene}
	<section
		id="candidate-evidence"
		aria-labelledby="evidence-explorer-title"
		class="brand-pattern-fiduciaries rounded-xl border border-yonder-700/80 bg-deep-blue/95 p-4 text-xs leading-relaxed text-slate-200 shadow-lg"
	>
		<h2 id="evidence-explorer-title" class="text-sm font-bold text-white">
			Explore candidate evidence
		</h2>
		<p class="mt-1">
			Compare radar with dated optical imagery. Select a marker on the map or choose a candidate
			below.
		</p>
		<div class="mt-3 space-y-3">
			<label class="block font-semibold text-slate-200"
				>Radar observation (HH)
				<select
					aria-label="Radar reference for optical comparison"
					bind:value={appState.radarReference}
					onchange={() => (appState.activeLayer = 'optical_compare')}
					class="mt-1 block w-full rounded border border-slate-600 bg-slate-900 p-2 text-xs font-normal text-white"
				>
					<option value="baseline"
						>Baseline · {formatAcquisitionDate(evidence.nisar_dates.baseline)}</option
					>
					<option value="repeat"
						>Repeat · {formatAcquisitionDate(evidence.nisar_dates.post_event)}</option
					>
				</select>
			</label>
			<label class="block font-semibold text-slate-200"
				>Sentinel-2 optical observation
				<select
					aria-label="Optical observation"
					value={scene.id}
					onchange={(e) => {
						appState.opticalSceneId = e.currentTarget.value;
						appState.activeLayer = 'optical_compare';
					}}
					class="mt-1 block w-full rounded border border-slate-600 bg-slate-900 p-2 text-xs font-normal text-white"
				>
					{#each evidence.scenes as option (option.id)}
						<option value={option.id}
							>{formatAcquisitionDate(option.datetime)} · {timeGap(
								option,
								appState.radarReference
							)}</option
						>
					{/each}
				</select>
			</label>
			<p class="font-semibold text-neon-yellow">
				Optical acquired {timeGap(scene, appState.radarReference)}. Different times and sensors;
				water change remains unconfirmed.
			</p>
			<button
				type="button"
				onclick={() => (appState.activeLayer = 'optical_compare')}
				aria-pressed={appState.activeLayer === 'optical_compare'}
				class="brand-btn-primary w-full rounded px-3 py-2 text-xs shadow-md"
				>Compare radar and optical</button
			>
			<label class="block font-semibold text-slate-200"
				>Candidate ({evidence.candidates.length} total)
				<select
					aria-label="Candidate to inspect"
					value={appState.selectedCandidateId ?? ''}
					onchange={(e) =>
						appState.selectCandidate(
							e.currentTarget.value ? Number(e.currentTarget.value) : null,
							true
						)}
					class="mt-1 block w-full rounded border border-slate-600 bg-slate-900 p-2 text-xs font-normal text-white"
				>
					<option value="">Choose a candidate…</option>
					{#each evidence.candidates as item (item.component)}
						<option value={item.component}
							>Candidate {item.component} · {item.area_m2.toLocaleString()} m²</option
						>
					{/each}
				</select>
			</label>
		</div>
		{#if candidate}
			<div class="mt-4 border-t border-slate-700 pt-3" aria-live="polite">
				<h3 class="font-semibold text-white">
					Candidate {candidate.component} · {candidate.area_m2.toLocaleString()} m²
				</h3>
				<p class="mt-1 font-mono text-slate-300">
					{candidate.candidate_pixels} radar-grid cells · {candidate.centroid_lon_lat[1].toFixed(
						6
					)}° N, {candidate.centroid_lon_lat[0].toFixed(6)}° E
				</p>
				<p class="mt-2 font-mono text-[11px] text-slate-200">
					Radar: {evidence.nisar_dates.baseline.replace('T', ' ')} → {evidence.nisar_dates.post_event.replace(
						'T',
						' '
					)} (UTC).
				</p>
				<div class="mt-3 overflow-x-auto">
					<table class="w-full text-left text-[11px]">
						<caption class="mb-2 text-left font-semibold text-white"
							>Optical classification by date (cell counts)</caption
						>
						<thead
							><tr class="text-slate-300"
								><th class="py-1">Optical date (UTC)</th><th class="px-1">Water</th><th class="px-1"
									>Land</th
								><th class="px-1">Unknown</th></tr
							></thead
						>
						<tbody
							>{#each evidence.scenes as reference (reference.id)}
								{@const counts = candidate.references.find(
									(item) => item.scene_id === reference.id
								)!}
								<tr
									class:bg-electric-blue={reference.id === scene.id}
									class="border-t border-slate-800"
								>
									<th class="py-2 font-normal text-white"
										>{reference.datetime.slice(0, 10)}<span class="block text-[10px] text-slate-300"
											>{reference.datetime.slice(11, 19)} · {timeGap(
												reference,
												appState.radarReference
											)}</span
										></th
									>
									<td class="px-1 font-mono font-bold text-yonder-300">{counts.water_pixels}</td><td
										class="px-1 font-mono font-bold text-white">{counts.land_pixels}</td
									><td class="px-1 font-mono font-bold text-neon-yellow">{counts.unknown_pixels}</td
									>
								</tr>
							{/each}</tbody
						>
					</table>
				</div>
				<p class="mt-3 font-semibold text-white">Wider-date check: Aug 24 → Sep 13</p>
				<p class="mt-1">
					{candidate.land_to_water_pixels} land → water; {candidate.land_to_land_pixels} land → land;
					{candidate.water_to_water_pixels} water → water; {candidate.water_to_land_pixels} water → land;
					{candidate.unknown_pixels} unassessable.
				</p>
				<p class="mt-2 font-semibold text-neon-yellow">
					{candidate.joint_clear_pixels === 0
						? 'No usable paired optical coverage for this candidate.'
						: 'The optical transitions describe different dates and do not confirm the radar-date change.'}
				</p>
				<button
					type="button"
					onclick={() => appState.selectCandidate(candidate!.component, true)}
					class="brand-link-secondary mt-2 text-[11px]">Center selected candidate on map</button
				>
			</div>
		{/if}
		<p class="mt-3 text-[11px] text-slate-300">
			Unknown includes clouds, shadows, unclassified cells and the exclusion buffer. The 20 m
			optical classification is sampled on the 10 m radar grid; these counts are not independent
			optical measurements. All candidates remain unconfirmed.
		</p>
		<a
			class="brand-link-secondary mt-2 inline-block text-[11px]"
			href={resolve('/data/[...path]', {
				path: `validation/${evidence.event_id}/map-evidence.json`
			})}
			download>Download map evidence</a
		>
	</section>
{/if}
