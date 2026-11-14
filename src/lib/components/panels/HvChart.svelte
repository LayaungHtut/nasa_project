<script lang="ts">
	import { patchLabel, shortDate } from '$lib/data/scenarios';
	import type { DbStats, Epoch, ObservedHvSeries, ObservedPatch } from '$lib/types/scenario';

	let {
		series,
		epochs,
		selected = null,
		current,
		onpick
	}: {
		series: ObservedHvSeries;
		epochs: Epoch[];
		selected?: ObservedPatch | null;
		current: number;
		onpick: (k: number) => void;
	} = $props();

	// Validated against the deep-blue surface (dataviz validator, dark mode): orange matches the map's
	// "disturbed" overlay, green is stable vegetation; the selected patch is white, as on the map.
	const C = { reference: '#199e70', disturbed: '#d95926', patch: '#ffffff' };
	const W = 400;
	const H = 190;
	const M = { l: 32, r: 104, t: 8, b: 24 };

	let hovered = $state<number | null>(null);
	let focus = $derived(hovered ?? current);

	let days = $derived(epochs.map((e) => e.day));
	/** x scale: passes placed by date, so the 48-day gap shows as a gap. */
	let x = $derived.by(() => {
		const lo = days[0];
		const span = days[days.length - 1] - lo || 1;
		return (k: number) => M.l + ((days[k] - lo) / span) * (W - M.l - M.r);
	});

	type Line = { key: string; name: string; color: string; values: number[]; band?: DbStats[] };
	let lines = $derived.by(() => {
		const out: Line[] = [
			{
				key: 'reference',
				name: 'Stable vegetation',
				color: C.reference,
				values: series.reference.map((s) => s.median),
				band: series.reference
			}
		];
		if (series.disturbed)
			out.push({
				key: 'disturbed',
				name: 'Changed ground',
				color: C.disturbed,
				values: series.disturbed.map((s) => s.median),
				band: series.disturbed
			});
		if (selected)
			out.push({
				key: 'patch',
				name: patchLabel(selected),
				color: C.patch,
				values: selected.hv_db
			});
		return out;
	});

	// Whole-dB axis, padded to even steps around everything drawn.
	let yDomain = $derived.by(() => {
		const all = lines.flatMap((l) => [
			...l.values,
			...(l.band?.flatMap((b) => [b.p25, b.p75]) ?? [])
		]);
		const lo = Math.floor((Math.min(...all) - 0.5) / 2) * 2;
		const hi = Math.ceil((Math.max(...all) + 0.5) / 2) * 2;
		return [lo, hi] as const;
	});
	let y = $derived.by(() => {
		const [lo, hi] = yDomain;
		return (v: number) => M.t + ((hi - v) / (hi - lo)) * (H - M.t - M.b);
	});
	let yTicks = $derived.by(() => {
		const [lo, hi] = yDomain;
		const step = hi - lo > 12 ? 4 : 2;
		const t: number[] = [];
		for (let v = hi; v >= lo; v -= step) t.push(v);
		return t;
	});

	const path = (pts: [number, number][]) =>
		pts.map(([px, py], i) => `${i ? 'L' : 'M'}${px.toFixed(1)},${py.toFixed(1)}`).join('');
	/** Inter-quartile band: along the upper quartile, back along the lower one. */
	let bandPath = $derived.by(() => {
		const sx = x;
		const sy = y;
		return (b: DbStats[]) =>
			path(b.map((s, k) => [sx(k), sy(s.p75)])) +
			path([...b].reverse().map((s, j) => [sx(b.length - 1 - j), sy(s.p25)])).replace('M', 'L') +
			'Z';
	});

	// Direct labels at the right end, nudged apart so they never overlap.
	let endLabels = $derived.by(() => {
		const items = lines
			.map((l) => ({ ...l, ly: y(l.values[l.values.length - 1]) }))
			.sort((a, b) => a.ly - b.ly);
		for (let i = 1; i < items.length; i++)
			items[i].ly = Math.max(items[i].ly, items[i - 1].ly + 12);
		return items;
	});

	// Hit columns: halfway to each neighbouring pass, so the pointer only has to be nearest.
	let columns = $derived(
		epochs.map((_, k) => {
			const left = k === 0 ? M.l - 6 : (x(k - 1) + x(k)) / 2;
			const right = k === epochs.length - 1 ? W - M.r + 6 : (x(k) + x(k + 1)) / 2;
			return { left, width: right - left };
		})
	);
	let tipLeftPct = $derived((x(focus) / W) * 100);
	const fmt = (v: number) => `${v.toFixed(1)} dB`;
</script>

<div class="relative">
	<!-- Legend: line keys, names in text colours. -->
	<ul class="mb-1 flex flex-wrap gap-x-3 gap-y-0.5 text-[10px] text-slate-200">
		{#each lines as l (l.key)}
			<li class="flex items-center gap-1.5">
				<svg width="14" height="6" aria-hidden="true"
					><line x1="0" y1="3" x2="14" y2="3" stroke={l.color} stroke-width="2" /></svg
				>
				{l.name}
			</li>
		{/each}
		<li class="flex items-center gap-1.5 text-slate-300">
			<svg width="10" height="8" aria-hidden="true"
				><rect width="10" height="8" fill="#d3dcee" fill-opacity="0.25" /></svg
			>
			middle 50% of pixels
		</li>
	</ul>

	<svg
		viewBox="0 0 {W} {H}"
		class="w-full overflow-visible"
		role="img"
		aria-label="Median HV backscatter on each of the {epochs.length} passes for stable vegetation{series.disturbed
			? ' and the ground changed on the latest pass'
			: ''}{selected ? ` and ${patchLabel(selected)}` : ''}. Values are in the table below."
	>
		<!-- Baseline passes -->
		<rect
			x={x(0) - 6}
			y={M.t}
			width={x(1) - x(0) + 12}
			height={H - M.t - M.b}
			fill="#d3dcee"
			fill-opacity="0.06"
		/>
		<text x={(x(0) + x(1)) / 2} y={M.t + 11} text-anchor="middle" class="fill-slate-400 text-[10px]"
			>baseline</text
		>

		<!-- Recessive grid and y axis -->
		{#each yTicks as t (t)}
			<line x1={M.l} x2={W - M.r} y1={y(t)} y2={y(t)} stroke="#2a447e" stroke-width="0.5" />
			<text x={M.l - 4} y={y(t) + 3} text-anchor="end" class="fill-slate-400 text-[10px]">{t}</text>
		{/each}
		<text
			x={4}
			y={M.t + (H - M.t - M.b) / 2}
			transform="rotate(-90 4 {M.t + (H - M.t - M.b) / 2})"
			text-anchor="middle"
			dominant-baseline="hanging"
			class="fill-slate-400 text-[10px]">HV dB</text
		>

		<!-- Pass ticks -->
		{#each epochs as e, k (e.date)}
			<text
				x={x(k)}
				y={H - 8}
				text-anchor="middle"
				class="text-[10px] {k === current ? 'fill-slate-50 font-bold' : 'fill-slate-400'}"
				>{shortDate(e.date)}</text
			>
		{/each}

		<!-- Selected pass, then the crosshair while hovering another -->
		<line
			x1={x(current)}
			x2={x(current)}
			y1={M.t}
			y2={H - M.b}
			stroke="#b6c4e0"
			stroke-width="1"
			stroke-dasharray="2 2"
		/>
		{#if hovered !== null && hovered !== current}
			<line
				x1={x(hovered)}
				x2={x(hovered)}
				y1={M.t}
				y2={H - M.b}
				stroke="#e8eef8"
				stroke-width="1"
			/>
		{/if}

		{#each lines as l (l.key)}
			{#if l.band}
				<path d={bandPath(l.band)} fill={l.color} fill-opacity="0.16" />
			{/if}
		{/each}
		{#each lines as l (l.key)}
			<path
				d={path(l.values.map((v, k) => [x(k), y(v)]))}
				fill="none"
				stroke={l.color}
				stroke-width="2"
				stroke-linejoin="round"
				stroke-linecap="round"
			/>
			{#each l.values as v, k (k)}
				<!-- Surface ring keeps overlapping markers apart. -->
				<circle
					cx={x(k)}
					cy={y(v)}
					r={k === focus ? 4.5 : 3}
					fill={l.color}
					stroke="#07173f"
					stroke-width="1.5"
				/>
			{/each}
		{/each}

		{#each endLabels as l (l.key)}
			<line
				x1={W - M.r + 6}
				x2={W - M.r + 14}
				y1={l.ly}
				y2={l.ly}
				stroke={l.color}
				stroke-width="2"
			/>
			<text x={W - M.r + 18} y={l.ly + 3} class="fill-slate-100 text-[10px]">{l.name}</text>
		{/each}

		<!-- Hit columns: hover or focus shows every value at that pass; click or Enter selects the pass. -->
		{#each columns as c, k (k)}
			<rect
				x={c.left}
				y={M.t}
				width={c.width}
				height={H - M.t}
				fill="transparent"
				role="button"
				tabindex="0"
				aria-label="Show pass {shortDate(epochs[k].date)}"
				class="cursor-pointer outline-none focus-visible:fill-white/10"
				onpointerenter={() => (hovered = k)}
				onpointerleave={() => (hovered = null)}
				onfocus={() => (hovered = k)}
				onblur={() => (hovered = null)}
				onclick={() => onpick(k)}
				onkeydown={(ev) => {
					if (ev.key === 'Enter' || ev.key === ' ') {
						ev.preventDefault();
						onpick(k);
					}
				}}
			/>
		{/each}
	</svg>

	{#if hovered !== null}
		<div
			class="pointer-events-none absolute top-6 z-10 rounded-md border border-yonder-400/60 bg-deep-blue/95 px-2 py-1 text-[10px] whitespace-nowrap text-slate-300 shadow-lg"
			style:left="{tipLeftPct}%"
			style:transform={tipLeftPct > 50 ? 'translateX(calc(-100% - 8px))' : 'translateX(8px)'}
		>
			<div class="mb-0.5 text-slate-100">
				{shortDate(epochs[hovered].date)} · {epochs[hovered].label}
			</div>
			{#each lines as l (l.key)}
				<div class="flex items-center gap-1.5">
					<svg width="10" height="4" aria-hidden="true"
						><line x1="0" y1="2" x2="10" y2="2" stroke={l.color} stroke-width="2" /></svg
					>
					<strong class="font-mono text-white">{fmt(l.values[hovered])}</strong>
					<span>{l.name}</span>
				</div>
			{/each}
		</div>
	{/if}

	<details class="mt-1 text-[10px]">
		<summary class="cursor-pointer text-slate-300">Table of values</summary>
		<table class="font-mono-telemetry mt-1 w-full text-left">
			<thead class="text-slate-400">
				<tr>
					<th class="py-0.5 font-normal">Pass</th>
					{#each lines as l (l.key)}<th class="py-0.5 text-right font-normal">{l.name}</th>{/each}
				</tr>
			</thead>
			<tbody class="text-slate-100">
				{#each epochs as e, k (e.date)}
					<tr class={k === current ? 'text-neon-yellow' : ''}>
						<td class="py-0.5">{shortDate(e.date)}</td>
						{#each lines as l (l.key)}
							<td class="py-0.5 text-right">
								{l.values[k].toFixed(1)}{#if l.band}<span class="text-slate-400">
										({l.band[k].p25.toFixed(1)}…{l.band[k].p75.toFixed(1)})</span
									>{/if}
							</td>
						{/each}
					</tr>
				{/each}
			</tbody>
		</table>
	</details>
</div>
