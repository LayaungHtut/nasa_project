<script lang="ts">
	import { appState } from '$lib/stores/appState.svelte';
	import { periodChange } from '$lib/data/timeseries';
	import { TriangleAlert } from 'lucide-svelte';

	let ts = $derived(appState.selectedEvent.timeseries);
	let range = $derived(appState.periodRange);
	let change = $derived(ts && range ? periodChange(ts, range.from, range.to) : undefined);

	const day = (iso: string) =>
		new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });
	const db = (v: number) => `${v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v).toFixed(1)} dB`;
	const word = (v: number) =>
		Math.abs(v) < 0.5 ? 'about the same' : v > 0 ? 'brighter' : 'darker';

	/** Phones: the map is short, so details fold away until asked for. */
	let open = $state(false);

	function pick(from: number, to: number) {
		appState.periodChoice = { from, to };
	}
</script>

{#if ts && range && change}
	<section
		class="pointer-events-auto max-h-full overflow-y-auto rounded-lg border border-yonder-500/40 bg-deep-blue/95 p-3 text-xs text-white shadow-xl backdrop-blur-md"
		aria-label="Compare two radar passes"
	>
		<div class="flex items-center justify-between gap-2">
			<h3 class="text-[11px] font-semibold text-white">Compare any two passes</h3>
			<button
				type="button"
				class="rounded border border-yonder-500/50 px-1.5 py-0.5 text-[10px] font-bold text-slate-200 sm:hidden"
				aria-expanded={open}
				aria-controls="period-details"
				onclick={() => (open = !open)}>{open ? 'Hide' : 'Changes'}</button
			>
		</div>

		<div class="mt-2 grid grid-cols-2 gap-2">
			<label class="block">
				<span class="text-[10px] text-slate-300 uppercase">From (left)</span>
				<select
					class="mt-0.5 w-full rounded border border-yonder-500/50 bg-deep-blue py-1 pr-7 pl-2 font-mono text-xs text-white"
					value={range.from}
					onchange={(e) => pick(Number(e.currentTarget.value), range.to)}
				>
					{#each ts.dates as d, i (d.date)}
						<option value={i} disabled={i >= range.to}>{day(d.date)}</option>
					{/each}
				</select>
			</label>
			<label class="block">
				<span class="text-[10px] text-slate-300 uppercase">To (right)</span>
				<select
					class="mt-0.5 w-full rounded border border-yonder-500/50 bg-deep-blue py-1 pr-7 pl-2 font-mono text-xs text-white"
					value={range.to}
					onchange={(e) => pick(range.from, Number(e.currentTarget.value))}
				>
					{#each ts.dates as d, i (d.date)}
						<option value={i} disabled={i <= range.from}>{day(d.date)}</option>
					{/each}
				</select>
			</label>
		</div>

		<div id="period-details" class={open ? '' : 'hidden sm:block'}>
			<div class="mt-2 flex flex-wrap gap-1" role="group" aria-label="Suggested periods">
				{#each appState.periodPresets as p (p.label)}
					{@const active = p.from === range.from && p.to === range.to}
					<button
						type="button"
						onclick={() => pick(p.from, p.to)}
						aria-pressed={active}
						class="rounded border px-1.5 py-0.5 text-[10px] font-bold {active
							? 'border-neon-yellow text-neon-yellow'
							: 'border-yonder-500/50 text-slate-200 hover:border-white hover:text-white'}"
					>
						{p.label}
					</button>
				{/each}
			</div>

			<p class="mt-2.5 text-[11px] text-slate-200">
				{change.days} days apart. Change relative to forest:
			</p>
			<table class="mt-1 w-full font-mono text-[11px]">
				<tbody>
					{#each [['Paddy fields', change.paddy], ['Reservoir', change.reservoir], ['Built-up (check)', change.builtUp]] as const as [label, v] (label)}
						<tr>
							<td class="py-0.5 font-sans text-slate-200">{label}</td>
							<td class="py-0.5 text-right font-bold text-white">{db(v)}</td>
							<td class="py-0.5 pl-2 font-sans text-[10px] text-slate-300">{word(v)}</td>
						</tr>
					{/each}
				</tbody>
			</table>

			{#if !change.sameProcessing}
				<p
					class="mt-2 flex gap-1.5 rounded border border-rocket-red/70 bg-martian-red/90 p-1.5 text-[10px] leading-relaxed"
				>
					<TriangleAlert class="mt-0.5 h-3 w-3 shrink-0 text-neon-yellow" aria-hidden="true" />
					<span
						>These passes use different processing versions. The newer one reads about 2 dB darker
						everywhere, so read the map and these numbers with caution.</span
					>
				</p>
			{/if}
			<p class="mt-2 text-[10px] leading-relaxed text-slate-300">
				The map shows each pass on the same grayscale, so rain can brighten the whole scene. The
				numbers compare each surface with forest, which removes that shift.
			</p>
		</div>
	</section>
{/if}
