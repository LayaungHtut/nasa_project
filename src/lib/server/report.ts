import fs from 'node:fs';
import path from 'node:path';
import type { ChangeEvent, TimeSeries } from '$lib/types/api';
import { seasonFindings, ndviFindings } from '$lib/data/timeseries';
import { formatAcquisitionDate } from '$lib/data/presentation';
import { localAcquisitionTime } from '$lib/data/drivers';
// Official logo, black colourway for the white report page; bundled so it ships with the build.
import logoSvg from '$lib/assets/space-apps-logo-black.svg?raw';

/**
 * A self-contained, printable HTML report for one real event, built from the same records
 * and helpers as the app, so the report and the app always quote the same numbers.
 */

const DATA_DIR = path.resolve(process.cwd(), 'data');
// Light-surface steps of the app's series hues (paddy, reservoir, built-up).
const INK = { cropland: '#1baf7a', permanent_water: '#2a78d6', built_up: '#eb6834' } as const;
const LABEL = { cropland: 'Paddy fields', permanent_water: 'Reservoir', built_up: 'Built-up' };

const esc = (v: unknown) =>
	String(v).replace(
		/[&<>"']/g,
		(c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!
	);
const day = (iso: string) => esc(formatAcquisitionDate(iso));
const short = (iso: string) =>
	esc(
		new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' })
	);
const signed = (v: number, d = 1) => `${v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v).toFixed(d)}`;
const pct = (v: number) => `${Math.round(v * 100)}%`;

/** A data/ file as a data URI; only files inside data/ are read. */
function embed(url: string): string | undefined {
	const file = path.resolve(DATA_DIR, url.replace(/^\/data\//, ''));
	if (!file.startsWith(DATA_DIR + path.sep) || !fs.existsSync(file)) return undefined;
	return `data:image/png;base64,${fs.readFileSync(file).toString('base64')}`;
}

/** Season chart: one axis (dB relative to forest), direct labels, newer-processing passes apart. */
function seasonChart(ts: TimeSeries): string {
	const [W, H, L, R, T, B] = [720, 300, 48, 110, 16, 34];
	const keys = ['cropland', 'permanent_water', 'built_up'] as const;
	const crid = ts.dates[0].processing_crid;
	const t = ts.dates.map((d) => Date.parse(d.date));
	const vals = ts.dates.flatMap((d) => keys.map((k) => d.relative_to_forest_db[k] ?? 0));
	const lo = Math.floor(Math.min(0, ...vals) / 2) * 2;
	const hi = Math.ceil(Math.max(0, ...vals) / 2) * 2;
	const x = (ms: number) => L + ((ms - t[0]) / (t.at(-1)! - t[0])) * (W - L - R);
	const y = (v: number) => T + ((hi - v) / (hi - lo)) * (H - T - B);
	const out: string[] = [];
	for (let v = lo; v <= hi; v += 2)
		out.push(
			`<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="${v === 0 ? '#8a94a8' : '#e3e7ef'}" />`,
			`<text x="${L - 6}" y="${y(v) + 4}" text-anchor="end" class="tick">${signed(v, 0)}</text>`
		);
	out.push(
		`<text x="${L + 4}" y="${y(0) - 5}" class="tick">forest (reference)</text>`,
		...ts.dates
			.filter((_, i) => i % 2 === 0 || i === ts.dates.length - 1)
			.map(
				(d) =>
					`<text x="${x(Date.parse(d.date))}" y="${H - 12}" text-anchor="middle" class="tick">${short(d.date)}</text>`
			)
	);
	const firstNew = ts.dates.findIndex((d) => d.processing_crid !== crid);
	if (firstNew > 0) {
		const xm = (x(t[firstNew - 1]) + x(t[firstNew])) / 2;
		out.push(
			`<line x1="${xm}" x2="${xm}" y1="${T}" y2="${H - B}" stroke="#8a94a8" stroke-dasharray="4 4" />`,
			`<text x="${xm + 4}" y="${H - B - 6}" class="tick">newer processing →</text>`
		);
	}
	const ends: Array<{ k: (typeof keys)[number]; y: number }> = [];
	for (const k of keys) {
		const pts = ts.dates.map((d, i) => ({
			x: x(t[i]),
			y: y(d.relative_to_forest_db[k] ?? 0),
			same: d.processing_crid === crid,
			label: `${LABEL[k]}, ${short(d.date)}: ${signed(d.relative_to_forest_db[k] ?? 0, 2)} dB`
		}));
		const same = pts.filter((p) => p.same);
		out.push(
			`<polyline fill="none" stroke="${INK[k]}" stroke-width="2" points="${same.map((p) => `${p.x},${p.y}`).join(' ')}" />`,
			...pts.map(
				(p) =>
					`<circle cx="${p.x}" cy="${p.y}" r="4" fill="${p.same ? INK[k] : '#fff'}" stroke="${INK[k]}" stroke-width="2"><title>${p.label}</title></circle>`
			)
		);
		ends.push({ k, y: same.at(-1)!.y });
	}
	// Direct labels in the right margin, pushed apart so close lines stay readable.
	ends.sort((a, b) => a.y - b.y);
	ends.forEach((e, i) => {
		if (i > 0) e.y = Math.max(e.y, ends[i - 1].y + 15);
		out.push(`<text x="${W - R + 12}" y="${e.y + 4}" class="series">${LABEL[e.k]}</text>`);
	});
	return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Paddy, reservoir and built-up radar brightness relative to forest at each pass">${out.join('')}</svg>`;
}

export function buildReport(event: ChangeEvent): string | undefined {
	const ts = event.timeseries;
	const st = event.statistics;
	if (event.data_status !== 'REAL' || !ts || !st) return undefined;
	const f = seasonFindings(ts);
	const ps = ts.pixel_season;
	const lc = ts.landcover_map;
	const ndvi = event.ndvi ? ndviFindings(event.ndvi) : undefined;
	const pv = event.processing_versions;
	const { baseline, post_event } = event.observation_dates;
	const landcover = embed(lc.map_url);
	const loss = embed(lc.water_loss_url);
	const timing = embed(ps.map_url);
	const logo = `data:image/svg+xml;base64,${Buffer.from(logoSvg).toString('base64')}`;
	const crid = ts.dates[0].processing_crid;

	const passRows = ts.dates
		.map(
			(d) => `<tr${d.processing_crid !== crid ? ' class="newer"' : ''}>
				<td>${day(d.date)}</td><td>${esc(d.processing_crid)}</td>
				<td>${signed(d.relative_to_forest_db.cropland ?? NaN, 2)}</td>
				<td>${signed(d.relative_to_forest_db.permanent_water ?? NaN, 2)}</td>
				<td>${signed(d.relative_to_forest_db.built_up ?? NaN, 2)}</td>
				<td>${d.processing_crid === crid ? d.water_area_km2.toFixed(2) : 'n/c'}</td>
				<td>${d.weather.era5_rain_24h_mm.toFixed(0)}</td><td>${d.weather.era5_wind_ms.toFixed(1)}</td></tr>`
		)
		.join('');

	const drivers = (event.drivers ?? [])
		.map(
			(
				h
			) => `<div class="driver"><h3>${esc(h.title)} <span class="tag">${esc(h.support)}</span></h3>
			${h.evidence_for.length ? `<p class="k">For</p><ul>${h.evidence_for.map((e) => `<li>${esc(e)}</li>`).join('')}</ul>` : ''}
			${h.evidence_against.length ? `<p class="k">Against</p><ul>${h.evidence_against.map((e) => `<li>${esc(e)}</li>`).join('')}</ul>` : ''}
			<p><strong>What would settle it:</strong> ${esc(h.how_to_test)}</p></div>`
		)
		.join('');

	const granules = event.source_products
		.map((p) => `<li><code>${esc(p.granule_id)}</code> (${day(p.acquisition_date)})</li>`)
		.join('');

	return `<!doctype html>
<html lang="en"><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>${esc(event.title)}: analysis report</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fira+Code&family=Fira+Sans:wght@700;900&family=Overpass:wght@400;600;700&display=swap" />
<style>
:root { --deep: #07173f; --electric: #0042a6; --muted: #4a5670; --line: #d5dbe7; }
* { box-sizing: border-box; }
body { margin: 0; background: #fff; color: var(--deep); font: 15px/1.55 Overpass, system-ui, sans-serif; }
main { max-width: 880px; margin: 0 auto; padding: 32px 24px 48px; }
header { border-bottom: 3px solid var(--electric); padding-bottom: 16px; }
header img { height: 44px; }
h1 { font: 900 28px/1.2 'Fira Sans', sans-serif; text-transform: uppercase; letter-spacing: .04em; margin: 14px 0 4px; }
h2 { font: 700 19px/1.3 'Fira Sans', sans-serif; text-transform: uppercase; letter-spacing: .03em; margin: 34px 0 10px; color: var(--electric); }
h3 { font-size: 15px; margin: 0 0 6px; }
.sub, .note, figcaption, .k { color: var(--muted); }
.note, figcaption { font-size: 13px; }
.k { font-size: 12px; font-weight: 700; text-transform: uppercase; margin: 8px 0 2px; }
.key { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; margin: 16px 0; }
.key div { border: 1px solid var(--line); border-radius: 8px; padding: 10px 12px; }
.key b { display: block; font: 700 22px 'Fira Code', monospace; }
.callout { background: #eef3fb; border-left: 4px solid var(--electric); padding: 12px 16px; border-radius: 4px; }
figure { margin: 16px 0; }
svg { width: 100%; height: auto; font-family: Overpass, sans-serif; }
svg .tick { font-size: 11px; fill: var(--muted); } svg .series { font-size: 12px; font-weight: 700; fill: var(--deep); }
.map { position: relative; width: 100%; max-width: 520px; aspect-ratio: 1; background: var(--deep); border-radius: 6px; overflow: hidden; }
.map img { position: absolute; inset: 0; width: 100%; height: 100%; image-rendering: pixelated; }
.swatches { display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: 13px; margin-top: 8px; }
.swatches span::before { content: ''; display: inline-block; width: 12px; height: 12px; border-radius: 2px; margin-right: 6px; vertical-align: -1px; background: var(--c); border: 1px solid #0002; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { border-bottom: 1px solid var(--line); padding: 5px 6px; text-align: right; }
th:first-child, td:first-child, .passes td:nth-child(2), .passes th:nth-child(2) { text-align: left; }
.scroll { overflow-x: auto; }
th { font-weight: 700; color: var(--muted); }
tr.newer td { color: var(--muted); font-style: italic; }
.driver { border: 1px solid var(--line); border-radius: 8px; padding: 12px 14px; margin: 10px 0; }
.driver ul { margin: 2px 0 6px; padding-left: 18px; }
.tag { font-size: 11px; font-weight: 700; text-transform: uppercase; border: 1px solid var(--electric); color: var(--electric); border-radius: 4px; padding: 1px 6px; margin-left: 6px; }
code, pre { font-family: 'Fira Code', monospace; font-size: 12px; word-break: break-all; }
pre { background: #f3f5f9; padding: 10px 12px; border-radius: 6px; white-space: pre-wrap; }
footer { margin-top: 40px; border-top: 1px solid var(--line); padding-top: 12px; font-size: 12px; color: var(--muted); }
@media print { main { padding: 0; } h2 { break-after: avoid; } figure, .driver, tr { break-inside: avoid; } * { print-color-adjust: exact; -webkit-print-color-adjust: exact; } }
</style></head>
<body><main>
<header>
	<img src="${logo}" alt="NASA Space Apps Challenge" />
	<h1>${esc(event.title)}</h1>
	<p class="sub">Analysis report · Team YOUTHs, Yangon · 2026 NASA Space Apps Challenge, “Dancing with the SARs” ·
	NISAR L2 GCOV, Track ${ts.track} / Frame ${ts.frame}, HH · ${day(ts.dates[0].date)} to ${day(ts.dates.at(-1)!.date)}</p>
	<p class="note">A team project, not a NASA product. Every number below is read from the project's processed records; nothing is generated by an AI model.</p>
</header>

<h2>Summary</h2>
<p class="callout">A two-date comparison (${day(baseline)} vs ${day(post_event)}) flagged <strong>${f.loss.total.toFixed(2)} km² of apparent water loss</strong> near Hlawga Reservoir.
Checked against the independent ESA WorldCover map, <strong>${f.loss.paddyPct}% of it lies on paddy fields</strong> and only ${f.loss.reservoir} km² on the reservoir.
Across ${ts.dates.length} NISAR passes, the paddy fields are darkest on ${day(f.paddyLow.date)} (flooded fields look like water) and then brighten by
<strong>${f.paddyRise.toFixed(1)} dB relative to forest</strong> by ${day(f.paddyPeak.date)}, as rice grows above the standing water. The fields changed, not the reservoir.</p>
<div class="key">
	<div><b>${f.loss.paddyPct}%</b>of the apparent water loss is on paddy fields</div>
	<div><b>${signed(f.paddyRise)} dB</b>paddy rise against forest, ${short(f.paddyLow.date)} → ${short(f.paddyPeak.date)}</div>
	<div><b>${pct(ps.brightened_over_1db.cropland)} vs ${pct(ps.brightened_over_1db.forest_control)}</b>of paddy vs forest patches brightened by more than 1 dB</div>
	<div><b>${ts.dates.length}</b>NISAR passes, every 12 days, through monsoon cloud</div>
</div>

<h2>1 · The season, pass by pass</h2>
<figure><div class="swatches">${(['cropland', 'permanent_water', 'built_up'] as const).map((k) => `<span style="--c:${INK[k]}">${LABEL[k]}</span>`).join('')}<span style="--c:#fff">Newer processing (hollow)</span></div>${seasonChart(ts)}
<figcaption>Median HH of each surface minus median HH of forest, in dB. Comparing with forest removes the shift that brightens the whole scene after rain
(forest brightness follows the previous day's rain, correlation ${f.rainCorrelation.toFixed(2)}). Built-up land is a check: it stays within ${f.builtRange} dB.
Hollow points use a newer processing version that reads about 2 dB darker everywhere, so they are not joined to the line.</figcaption></figure>
<div class="scroll"><table class="passes"><thead><tr><th>Pass (UTC)</th><th>Processing</th><th>Paddy</th><th>Reservoir</th><th>Built-up</th><th>Water-like km²</th><th>Rain 24 h, mm</th><th>Wind, m/s</th></tr></thead>
<tbody>${passRows}</tbody></table></div>
<p class="note">dB relative to forest. Water-like area uses the fixed ${esc(st.threshold_db)} dB threshold, which does not carry over to the newer processing (n/c: not comparable).</p>

<h2>2 · Where the “water loss” fell</h2>
<figure>
	<div class="map">${landcover ? `<img src="${landcover}" alt="Land cover: paddy, reservoir and built-up land" />` : ''}${loss ? `<img src="${loss}" alt="Apparent water loss pixels" />` : ''}</div>
	<div class="swatches">${lc.classes.map((c) => `<span style="--c:${esc(c.color)}">${esc(c.label)}, ${c.area_km2} km²</span>`).join('')}<span style="--c:#fff">Apparent water loss, ${short(baseline)} → ${short(post_event)}</span></div>
	<figcaption>ESA WorldCover 2021 classes on the radar grid; ${esc(lc.uncoloured.toLowerCase())} are not coloured. White pixels are the ${f.loss.total.toFixed(2)} km² the two-date threshold called water loss:
	${f.loss.paddy} km² on paddy fields, ${f.loss.reservoir} km² on the reservoir. Of the ${esc(st.new_inundation_area_km2)} km² new-inundation candidate, ${f.candidatePaddy} km² is also paddy.</figcaption>
</figure>

<h2>3 · Field by field</h2>
<p>Every 70 m patch was tested on the ${f.comparableCount} passes that share one processing version, with forest as the control: forest should change little over weeks, so its pass rate is the false-positive rate.</p>
<table><thead><tr><th>Test</th><th>Paddy</th><th>Forest (control)</th></tr></thead><tbody>
<tr><td>Brightened by more than 1 dB, ${short(ps.compared_dates.darkest_paddy)} → ${short(ps.compared_dates.brightest_paddy_after)}</td><td>${pct(ps.brightened_over_1db.cropland)}</td><td>${pct(ps.brightened_over_1db.forest_control)}</td></tr>
<tr><td>Darkened by more than 1 dB</td><td>${pct(ps.darkened_over_1db.cropland)}</td><td>${pct(ps.darkened_over_1db.forest_control)}</td></tr>
<tr><td>Darkest pass, then a rise of at least ${ps.rice_rise_threshold_db} dB</td><td>${pct(ps.dark_then_rise.cropland)}</td><td>${pct(ps.dark_then_rise.forest_control)}</td></tr>
</tbody></table>
<figure>
	<div class="map">${timing ? `<img src="${timing}" alt="When each paddy field was darkest" />` : ''}</div>
	<div class="swatches">${ps.darkest_pass_periods.map((p) => `<span style="--c:${esc(p.color)}">${short(p.from)} to ${short(p.to)}, ${p.cropland_km2} km²</span>`).join('')}</div>
	<figcaption>When each paddy field was darkest (most water-like, likely flooded around planting) before its return rose. Fields ${ps.timing_neighbour_agreement.lag_m} m apart share a timing group
	${pct(ps.timing_neighbour_agreement.observed)} of the time, against ${pct(ps.timing_neighbour_agreement.if_random)} for random labels: patches, as fields planted at different times would make, though a local shower could too.</figcaption>
</figure>

<h2>4 · Competing explanations</h2>
${drivers || '<p class="note">No explanations recorded for this event.</p>'}

<h2>5 · Independent checks</h2>
<ul>
	${event.weather ? `<li><strong>Weather:</strong> the detailed passes were at ${esc(localAcquisitionTime(baseline))} and ${esc(localAcquisitionTime(post_event))} Myanmar time, and ${event.weather.comparison.all_near_calm ? 'both mornings were near calm' : 'wind was recorded at both'} (ERA5 and Yangon airport reports). Across the season, reservoir brightness is uncorrelated with wind (${f.windCorrelation.toFixed(2)}).</li>` : ''}
	${ndvi && event.ndvi ? `<li><strong>Sentinel-2 greenness:</strong> only ${ndvi.usable.length} of ${event.ndvi.scenes.length} scenes were clear enough over the paddy fields. Paddy NDVI is ${ndvi.paddyRange[0].toFixed(2)} to ${ndvi.paddyRange[1].toFixed(2)} on those dates: consistent with the radar, but not independent confirmation of growth.</li>` : ''}
	${pv ? `<li><strong>Processing versions:</strong> the last ${f.laterVersionCount} passes use newer processing. Their metadata show ${Object.keys(pv.flags_that_differ).length === 0 ? 'identical processing flags' : 'different processing flags'}${pv.software_release_changed ? ' and a new software release' : ''}. Relative to forest, the reservoir drops ${signed(pv.forest_relative_db_change.permanent_water)} dB across the change while paddy moves ${signed(pv.forest_relative_db_change.cropland, 2)} dB, so part of the reservoir's brightness is likely processing.</li>` : ''}
</ul>

<h2>6 · Method</h2>
<ul>
	<li>NISAR L2 GCOV, frequency A, HH; ${esc(st.aoi_area_km2)} km² study area at ${Math.sqrt(st.pixel_area_m2).toFixed(0)} m pixel spacing. The two detailed passes were downloaded in full; the other passes were read remotely, fetching only the study window.</li>
	<li>${esc(st.lee_filter_size)} × ${esc(st.lee_filter_size)} Lee speckle filter, conversion to dB, water-like below ${esc(st.threshold_db)} dB, change clusters of at least ${esc(st.min_cluster_pixels)} pixels.
	Two-date result: ${esc(st.baseline_water_area_km2)} km² water-like before, ${esc(st.post_event_water_area_km2)} km² after; heuristic score ${esc(st.detection_score)} (not a probability).</li>
	<li>${esc(ts.landcover_source)}; class statistics use core pixels eroded by ${ts.landcover_mask_erosion_px} px so field edges do not blur the classes.</li>
</ul>

<h2>7 · Limits</h2>
<ul>${event.processing.limitations.map((l) => `<li>${esc(l)}</li>`).join('')}
	<li>No crop calendar, field survey or reservoir level record has been checked. Planting dates from farmers around Hlawga would test the field-timing map directly.</li></ul>

<h2>8 · Data and sources</h2>
<ul>
	<li>Radar: NASA/ISRO NISAR, distributed by ASF DAAC / NASA Earthdata. Detailed passes:<ul>${granules}</ul></li>
	<li>Land cover: ESA WorldCover 10 m 2021 v200 (© ESA WorldCover project, CC BY 4.0).</li>
	<li>Optical: modified Copernicus Sentinel data (2026), via Element 84 Earth Search.</li>
	<li>Weather: ERA5 via Open-Meteo (CC BY 4.0); Yangon airport (VYYY) METAR via the Iowa Environmental Mesonet.</li>
	<li>Analysis and interpretation: Team YOUTHs. Records: <code>data/processed/${esc(event.id)}/timeseries.json</code>, <code>statistics.json</code>, <code>metadata.json</code>.</li>
</ul>
<pre>python -m services.processing.timeseries --event-id ${esc(event.id)}
python -m services.processing.ndvi --event-id ${esc(event.id)}
python scripts/compare_processing_versions.py --event-id ${esc(event.id)}</pre>

<footer>Generated ${esc(new Date().toISOString().slice(0, 16).replace('T', ' '))} UTC from the season record dated ${esc((ts as TimeSeries & { generated_at?: string }).generated_at?.slice(0, 10) ?? 'n/a')}. Print this page or save it as PDF from your browser.</footer>
</main></body></html>`;
}
