<script lang="ts">
	import { appState } from '$lib/stores/appState.svelte';
	import { resolve } from '$app/paths';
	import { Sprout } from 'lucide-svelte';
	import type { LandcoverClass, TimeSeries } from '$lib/types/api';
	import { ndviFindings, seasonFindings } from '$lib/data/timeseries';

	let event = $derived(appState.selectedEvent);
	let ts = $derived(event.timeseries);
	let f = $derived(ts ? seasonFindings(ts) : undefined);
	let ndvi = $derived(event.ndvi);
	let nd = $derived(ndvi ? ndviFindings(ndvi) : undefined);
	const FOREST = '#93a6cc'; // neutral reference line, not a categorical series
	const NDVI_H = 80;
	// Optical dates fall between radar passes, so place them by time on the radar axis.
	let xt = $derived((iso: string) => {
		const t0 = Date.parse(dates[0].date);
		const t1 = Date.parse(dates[dates.length - 1].date);
		return PAD.l + ((Date.parse(iso) - t0) / (t1 - t0)) * (W - PAD.l - PAD.r);
	});
	const yn = (v: number) => 6 + ((1 - v) * (NDVI_H - 6 - 18)) / 0.6;
	const pct = (v: number) => `${Math.round(v * 100)}%`;

	// Validated with the dataviz palette script on the Deep Blue surface (dark mode, all pairs).
	const SERIES: Array<{ key: LandcoverClass; label: string; color: string }> = [
		{ key: 'cropland', label: 'Paddy fields', color: '#199e70' },
		{ key: 'permanent_water', label: 'Reservoir', color: '#3987e5' },
		{ key: 'built_up', label: 'Built-up (check)', color: '#d95926' }
	];
	const OTHER = '#4d6496';

	const W = 400;
	const H = 170;
	const PAD = { l: 30, r: 74, t: 10, b: 22 };
	const BAR_H = 90;

	type Row = TimeSeries['dates'][number];
	const rel = (d: Row, k: LandcoverClass) => d.relative_to_forest_db[k] ?? NaN;
	const short = (iso: string) =>
		new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });

	let dates = $derived(ts?.dates ?? []);
	let span = $derived((W - PAD.l - PAD.r) / Math.max(1, dates.length - 1));
	let x = $derived((i: number) => PAD.l + i * span);
	let values = $derived(
		dates.flatMap((d) => SERIES.map((s) => rel(d, s.key))).filter(Number.isFinite)
	);
	let yMin = $derived(Math.floor(Math.min(...values) - 0.5));
	let yMax = $derived(Math.ceil(Math.max(...values) + 0.5));
	let y = $derived((v: number) => PAD.t + ((yMax - v) * (H - PAD.t - PAD.b)) / (yMax - yMin));
	let yTicks = $derived(
		Array.from({ length: yMax - yMin + 1 }, (_, i) => yMax - i).filter((v) => v % 2 === 0)
	);
	let line = $derived((k: LandcoverClass) =>
		dates.map((d, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(rel(d, k)).toFixed(1)}`).join(' ')
	);
	let labelStep = $derived(dates.length > 8 ? 2 : 1);
	let versionBreak = $derived(
		dates.findIndex((d, i) => i > 0 && d.processing_crid !== dates[0].processing_crid)
	);
	let comparable = $derived((d: Row) => d.processing_crid === dates[0].processing_crid);

	// Water-like area per date, split by where it lies. Only the first processing version:
	// the newer one is darker overall, so a fixed threshold does not transfer.
	const km2 = (d: Row, k: LandcoverClass) => {
		const c = d.hh_by_landcover[k];
		return c ? (c.radar_water_fraction * c.pixels) / 1e4 : 0;
	};
	let stacks = $derived(
		dates.map((d) => {
			const paddy = km2(d, 'cropland');
			const reservoir = km2(d, 'permanent_water');
			return { paddy, reservoir, other: Math.max(0, d.water_area_km2 - paddy - reservoir) };
		})
	);
	let areaMax = $derived(
		Math.ceil(Math.max(1, ...dates.filter(comparable).map((d) => d.water_area_km2)))
	);
	let ya = $derived((v: number) => 6 + ((areaMax - v) * (BAR_H - 6 - 18)) / areaMax);

	let selected = $derived(appState.activeLayer === 'series' ? appState.seriesIndex : -1);
	let hovered = $state<number | null>(null);
	let focus = $derived(hovered ?? (selected >= 0 ? selected : null));

	function pick(i: number) {
		appState.seriesIndex = i;
		appState.activeLayer = 'series';
	}
</script>

{#if ts && f && dates.length > 1}
	<section
		class="rounded-lg border border-neon-yellow/50 bg-deep-blue/95 p-3.5 text-[11px] leading-relaxed shadow-lg"
		aria-labelledby="timeseries-heading"
	>
		<h2
			id="timeseries-heading"
			class="flex items-center gap-2 text-[11px] font-bold tracking-wider text-white uppercase"
		>
			<Sprout class="h-4 w-4 text-neon-yellow" />
			A rice season, seen by radar
		</h2>
		<p class="mt-2 text-slate-200">
			{dates.length} NISAR passes, every 12 days from {short(dates[0].date)} to
			{short(dates[dates.length - 1].date)}. Each line shows how much brighter or darker a surface
			is than the surrounding forest. Comparing with forest removes a brightness shift that affects
			the whole scene on each date. Click a date to see that pass on the map.
		</p>

		<ul class="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-slate-200" aria-label="Legend">
			{#each SERIES as s (s.key)}
				<li class="flex items-center gap-1.5">
					<span class="h-0.5 w-4 rounded" style:background={s.color}></span>{s.label}
				</li>
			{/each}
		</ul>

		<svg
			viewBox="0 0 {W} {H}"
			class="mt-1 w-full"
			role="img"
			aria-label="HH backscatter relative to forest, in dB, for paddy fields, reservoir and built-up land at each NISAR pass"
			onmouseleave={() => (hovered = null)}
		>
			{#each yTicks as t (t)}
				<line
					x1={PAD.l}
					x2={W - PAD.r}
					y1={y(t)}
					y2={y(t)}
					stroke={t === 0 ? '#4d6496' : '#16306a'}
					stroke-width="1"
				/>
				<text x={PAD.l - 4} y={y(t) + 3} text-anchor="end" class="fill-slate-400 text-[9px]"
					>{t > 0 ? `+${t}` : t}</text
				>
			{/each}
			<text x={PAD.l + 2} y={y(0) - 3} class="fill-slate-400 text-[8px]">forest</text>
			{#if versionBreak > 0}
				{@const bx = x(versionBreak) - span / 2}
				<line
					x1={bx}
					x2={bx}
					y1={PAD.t}
					y2={H - PAD.b}
					stroke="#93a6cc"
					stroke-dasharray="3 3"
					stroke-width="1"
				/>
				<text x={bx - 3} y={H - PAD.b - 4} text-anchor="end" class="fill-slate-400 text-[8px]"
					>newer processing →</text
				>
			{/if}
			{#if focus !== null}
				<line
					x1={x(focus)}
					x2={x(focus)}
					y1={PAD.t}
					y2={H - PAD.b}
					stroke="#eafe07"
					stroke-width="1"
				/>
			{/if}
			{#each SERIES as s (s.key)}
				<path
					d={line(s.key)}
					fill="none"
					stroke={s.color}
					stroke-width="2"
					stroke-linejoin="round"
				/>
				{#each dates as d, i (d.date)}
					<circle
						cx={x(i)}
						cy={y(rel(d, s.key))}
						r={i === focus ? 4 : 2.5}
						fill={s.color}
						stroke="#07173f"
						stroke-width="2"
					/>
				{/each}
				<text
					x={W - PAD.r + 6}
					y={y(rel(dates[dates.length - 1], s.key)) + 3}
					class="fill-slate-200 text-[9px]">{s.label.replace(' (check)', '')}</text
				>
			{/each}
			{#each dates as d, i (d.date)}
				{#if (dates.length - 1 - i) % labelStep === 0}
					<text x={x(i)} y={H - 6} text-anchor="middle" class="fill-slate-400 text-[8px]"
						>{short(d.date)}</text
					>
				{/if}
				<rect
					x={x(i) - span / 2}
					y={PAD.t}
					width={span}
					height={H - PAD.t - PAD.b}
					fill="transparent"
					class="cursor-pointer outline-none"
					role="button"
					tabindex="0"
					aria-label="Show {short(d.date)} on the map"
					onmouseenter={() => (hovered = i)}
					onfocus={() => (hovered = i)}
					onblur={() => (hovered = null)}
					onclick={() => pick(i)}
					onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && pick(i)}
				/>
			{/each}
		</svg>

		{#if focus !== null}
			{@const d = dates[focus]}
			<div
				class="mt-1 rounded border border-yonder-500/30 bg-electric-blue/30 p-2 font-mono text-[10px] text-white"
			>
				<div class="font-sans font-bold text-neon-yellow">
					{short(d.date)} · processing {d.processing_crid}
				</div>
				{#each SERIES as s (s.key)}
					<div class="flex justify-between">
						<span class="flex items-center gap-1.5 font-sans text-slate-200"
							><span class="h-2 w-2 rounded-full" style:background={s.color}></span>{s.label}</span
						>
						<span>{rel(d, s.key) > 0 ? '+' : ''}{rel(d, s.key).toFixed(1)} dB vs forest</span>
					</div>
				{/each}
				<div class="flex justify-between">
					<span class="font-sans text-slate-200">Wind (ERA5 / airport), rain 24 h</span><span
						>{d.weather.era5_wind_ms.toFixed(1)} / {d.weather.airport_max_wind_ms?.toFixed(1) ??
							'n/a'} m/s, {d.weather.era5_rain_24h_mm.toFixed(0)} mm</span
					>
				</div>
			</div>
		{/if}

		<h3 class="mt-3 text-[10px] font-bold tracking-wider text-slate-200 uppercase">
			Where the water-like pixels are (below {ts.inputs.threshold_db} dB)
		</h3>
		<ul class="mt-1 flex flex-wrap gap-x-3 text-[10px] text-slate-200" aria-label="Bar legend">
			<li class="flex items-center gap-1.5">
				<span class="h-2 w-2 rounded-sm" style:background={SERIES[0].color}></span>Paddy fields
			</li>
			<li class="flex items-center gap-1.5">
				<span class="h-2 w-2 rounded-sm" style:background={SERIES[1].color}></span>Reservoir
			</li>
			<li class="flex items-center gap-1.5">
				<span class="h-2 w-2 rounded-sm" style:background={OTHER}></span>Other land
			</li>
		</ul>
		<svg
			viewBox="0 0 {W} {BAR_H}"
			class="w-full"
			role="img"
			aria-label="Area below the water threshold per pass, in km², split into paddy fields, reservoir and other land"
		>
			<line x1={PAD.l} x2={W - PAD.r} y1={ya(0)} y2={ya(0)} stroke="#2a447e" stroke-width="1" />
			<text x={PAD.l - 4} y={ya(areaMax) + 3} text-anchor="end" class="fill-slate-400 text-[9px]"
				>{areaMax} km²</text
			>
			<text x={PAD.l - 4} y={ya(0) + 3} text-anchor="end" class="fill-slate-400 text-[9px]">0</text>
			{#each dates as d, i (d.date)}
				{#if comparable(d)}
					{@const s = stacks[i]}
					{@const parts = [
						{ v: s.paddy, c: SERIES[0].color },
						{ v: s.reservoir, c: SERIES[1].color },
						{ v: s.other, c: OTHER }
					]}
					{#each parts as part, j (j)}
						{@const below = parts.slice(0, j).reduce((sum, p) => sum + p.v, 0)}
						{@const h = ya(below) - ya(below + part.v)}
						{#if h > 2}
							<rect
								x={x(i) - 6}
								y={ya(below + part.v) + 1}
								width="12"
								height={h - 2}
								rx="2"
								fill={part.c}
								opacity={focus === null || focus === i ? 1 : 0.45}
							/>
						{/if}
					{/each}
				{:else}
					<text x={x(i)} y={ya(0) - 4} text-anchor="middle" class="fill-slate-400 text-[8px]"
						>n/c</text
					>
				{/if}
				{#if (dates.length - 1 - i) % labelStep === 0}
					<text x={x(i)} y={BAR_H - 4} text-anchor="middle" class="fill-slate-400 text-[8px]"
						>{short(d.date)}</text
					>
				{/if}
			{/each}
		</svg>
		<p class="text-[10px] text-slate-300">
			n/c: not comparable. The newer processing reads about 2 dB darker everywhere, so the fixed
			threshold does not carry over.
		</p>

		{#if nd && nd.usable.length > 1}
			<h3 class="mt-3 text-[10px] font-bold tracking-wider text-slate-200 uppercase">
				Independent check: Sentinel-2 greenness (NDVI)
			</h3>
			<ul class="mt-1 flex flex-wrap gap-x-3 text-[10px] text-slate-200" aria-label="NDVI legend">
				<li class="flex items-center gap-1.5">
					<span class="h-0.5 w-4 rounded" style:background={SERIES[0].color}></span>Paddy fields
				</li>
				<li class="flex items-center gap-1.5">
					<span class="h-0.5 w-4 rounded" style:background={FOREST}></span>Forest
				</li>
			</ul>
			<svg
				viewBox="0 0 {W} {NDVI_H}"
				class="w-full"
				role="img"
				aria-label="Median Sentinel-2 NDVI of paddy fields and forest on cloud-free dates"
			>
				{#each [0.5, 0.7, 0.9] as t (t)}
					<line x1={PAD.l} x2={W - PAD.r} y1={yn(t)} y2={yn(t)} stroke="#16306a" stroke-width="1" />
					<text x={PAD.l - 4} y={yn(t) + 3} text-anchor="end" class="fill-slate-400 text-[9px]"
						>{t.toFixed(1)}</text
					>
				{/each}
				{#each [{ key: 'cropland_ndvi_median', color: SERIES[0].color }, { key: 'forest_ndvi_median', color: FOREST }] as const as s (s.key)}
					<path
						d={nd.usable
							.map(
								(sc, i) =>
									`${i ? 'L' : 'M'}${xt(sc.datetime).toFixed(1)},${yn(sc[s.key] as number).toFixed(1)}`
							)
							.join(' ')}
						fill="none"
						stroke={s.color}
						stroke-width="2"
					/>
					{#each nd.usable as sc (sc.id)}
						<circle
							cx={xt(sc.datetime)}
							cy={yn(sc[s.key] as number)}
							r="4"
							fill={s.color}
							stroke="#07173f"
							stroke-width="2"
							><title
								>{short(sc.datetime)}: {s.key === 'cropland_ndvi_median' ? 'paddy' : 'forest'} NDVI {(
									sc[s.key] as number
								).toFixed(2)}, {Math.round(sc.cropland_clear_fraction * 100)}% of paddy cloud-free</title
							></circle
						>
					{/each}
				{/each}
				{#each dates as d, i (d.date)}
					{#if (dates.length - 1 - i) % labelStep === 0}
						<text x={x(i)} y={NDVI_H - 4} text-anchor="middle" class="fill-slate-400 text-[8px]"
							>{short(d.date)}</text
						>
					{/if}
				{/each}
			</svg>
			<p class="text-[10px] text-slate-300">
				{nd.usable.length} of {ndvi?.scenes.length} Sentinel-2 scenes had at least
				{Math.round((ndvi?.min_cropland_clear_fraction ?? 0) * 100)}% of the paddy fields
				cloud-free. Monsoon clouds hide the rest, which is why radar matters here.
			</p>
		{/if}

		<div class="mt-3 space-y-2 rounded border border-neon-yellow/40 bg-electric-blue/25 p-2.5">
			<p class="font-bold text-neon-yellow">What the season shows</p>
			<p class="text-slate-100">
				<strong class="text-white">Paddy fields</strong> were darkest relative to forest on
				{short(f.paddyLow.date)} ({f.paddyLow.value.toFixed(1)} dB), when flooded fields looked like water.
				They then brightened by {f.paddyRise.toFixed(1)} dB to {short(f.paddyPeak.date)}, as you
				would expect while rice stems grow above standing water. The {f.laterVersionCount} later passes
				read slightly lower, which could be the start of harvest, but they use newer processing and the
				processing change alone is about that size.
			</p>
			<p class="text-slate-100">
				<strong class="text-white">It is not a statistical fluke:</strong> testing every 70 m patch,
				{pct(ts.pixel_season.brightened_over_1db.cropland)} of paddy brightened by more than 1 dB between
				those dates, against {pct(ts.pixel_season.brightened_over_1db.forest_control)} of forest, the
				control.
				<button
					type="button"
					class="text-yonder-300 underline"
					onclick={() => (appState.activeLayer = 'field_timing')}
					>Map when each field was darkest</button
				>.
			</p>
			{#if nd && nd.usable.length > 1}
				<p class="text-slate-100">
					<strong class="text-white">Optical check, honestly:</strong> on the {nd.usable.length} cloud-free
					Sentinel-2 dates the paddy fields were already green (NDVI {nd.paddyRange[0].toFixed(2)} to
					{nd.paddyRange[1].toFixed(2)}), and their greenness relative to forest barely moved ({nd.relRange[0].toFixed(
						2
					)} to {nd.relRange[1].toFixed(2)}). So the optical data neither confirm nor contradict the
					radar rise: greenness levels off once a rice canopy closes, while L-band radar keeps
					responding to stems and grain. No clear optical scene exists near {short(
						f.paddyLow.date
					)}. Planting dates from local farmers would settle it.
				</p>
			{/if}
			<p class="text-slate-100">
				<strong class="text-white">The "water loss" mystery is solved:</strong> of the
				{f.loss.total.toFixed(3)} km² that stopped looking like water between the two analysed dates,
				{f.loss.paddy.toFixed(2)} km² ({f.loss.paddyPct}%) lies on paddy fields and only
				{f.loss.reservoir.toFixed(3)} km² on the reservoir. The fields changed, not the reservoir.
			</p>
			<p class="text-slate-100">
				<strong class="text-white">The reservoir</strong> reads between {f.reservoirRange[0].toFixed(
					1
				)}
				and {f.reservoirRange[1].toFixed(1)} dB on every comparable pass, while calm open water usually
				reads around -20 dB or darker at L-band. Its brightness does not follow wind (correlation {f.windCorrelation.toFixed(
					2
				)} over
				{f.comparableCount} passes), so something other than wind keeps it bright.
			</p>
			<p class="text-slate-300">
				Check: built-up land stays within {f.builtRange.toFixed(2)} dB of forest across those passes,
				so the forest comparison removes the scene-wide shift. That shift follows recent rain (correlation
				{f.rainCorrelation.toFixed(2)}), consistent with wet surfaces reflecting more radar energy.
			</p>
		</div>

		<details class="mt-2 text-[10px]">
			<summary class="cursor-pointer text-yonder-300">Show as table</summary>
			<table class="mt-1 w-full text-left font-mono">
				<thead class="text-slate-300">
					<tr>
						<th class="font-normal">Date</th>
						<th class="text-right font-normal">Paddy</th>
						<th class="text-right font-normal">Res.</th>
						<th class="text-right font-normal">Built</th>
						<th class="text-right font-normal">Forest</th>
						<th class="text-right font-normal">Wind</th>
					</tr>
				</thead>
				<tbody class="text-white">
					{#each dates as d (d.date)}
						<tr class="border-t border-yonder-500/20">
							<td class="font-sans text-slate-300">{short(d.date)}</td>
							{#each SERIES as s (s.key)}
								<td class="text-right">{rel(d, s.key).toFixed(1)}</td>
							{/each}
							<td class="text-right">{d.hh_by_landcover.tree_cover?.median_db.toFixed(1)}</td>
							<td class="text-right">{d.weather.era5_wind_ms.toFixed(1)}</td>
						</tr>
					{/each}
				</tbody>
			</table>
			<p class="mt-1 text-slate-300">
				Paddy, reservoir and built-up are dB relative to forest; forest is its median HH in dB.
				Medians of 3 × 3 Lee-filtered HH. Wind is ERA5 at 10 m (m/s). Land cover: {ts.landcover_source}.
				<a
					class="text-yonder-300 underline"
					href={resolve('/data/[...path]', { path: ts.record_path })}
					download>Download the record</a
				>
			</p>
			{#if ndvi && nd && nd.usable.length}
				<table class="mt-3 w-full text-left font-mono">
					<caption class="text-left font-sans text-slate-300"
						>Sentinel-2 NDVI, usable scenes</caption
					>
					<thead class="text-slate-300">
						<tr>
							<th class="font-normal">Date</th>
							<th class="text-right font-normal">Paddy</th>
							<th class="text-right font-normal">Forest</th>
							<th class="text-right font-normal">Clear</th>
						</tr>
					</thead>
					<tbody class="text-white">
						{#each nd.usable as sc (sc.id)}
							<tr class="border-t border-yonder-500/20">
								<td class="font-sans text-slate-300">{short(sc.datetime)}</td>
								<td class="text-right">{sc.cropland_ndvi_median?.toFixed(2)}</td>
								<td class="text-right">{sc.forest_ndvi_median?.toFixed(2)}</td>
								<td class="text-right">{Math.round(sc.cropland_clear_fraction * 100)}%</td>
							</tr>
						{/each}
					</tbody>
				</table>
				<p class="mt-1 text-slate-300">
					Medians over the same WorldCover cores as the radar; "Clear" is the cloud-free share of
					paddy.
					<a
						class="text-yonder-300 underline"
						href={resolve('/data/[...path]', { path: ndvi.record_path })}
						download>Download the NDVI record</a
					>
				</p>
			{/if}
		</details>
	</section>
{/if}
