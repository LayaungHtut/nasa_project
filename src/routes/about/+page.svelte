<script lang="ts">
	import { Satellite, Radio, Cpu, Database, Award, ExternalLink, Rocket } from 'lucide-svelte';
	import SpaceAppsLogo from '$lib/components/brand/SpaceAppsLogo.svelte';

	const futureApplications = [
		{
			title: 'Validate the Hpakant result',
			body: 'Compare the detected change with cloud-free NASA HLS (Landsat and Sentinel-2) imagery from the dry season and with field reports, to measure precision and recall on real ground instead of the null test alone.'
		},
		{
			title: 'Permit checks with official boundaries',
			body: 'With concession polygons from the licensing authority, the change map could be split into inside and outside each permit. Those boundaries are not public, so the app makes no legality claim.'
		},
		{
			title: 'More frames across Kachin and Shan State',
			body: 'The slope-motion method runs on any NISAR frame with GUNW pairs. Extending it to the landslide-prone valleys of northern Shan State and the rest of Kachin needs only more downloads, then field checks of what it flags.'
		},
		{
			title: 'On-demand processing with ASF HyP3',
			body: 'HyP3 already produces terrain-corrected backscatter and InSAR products on request in the cloud. Using it would let the app follow new passes without downloading granule windows by hand.'
		},
		{
			title: 'Ground truth before any real alert',
			body: 'A compliance alert has legal weight. Before use, thresholds must be calibrated against field inspections and known excavation dates, and every alert should go to a person to verify, not straight to enforcement.'
		}
	];
</script>

<div
	class="mx-auto max-w-5xl flex-1 px-4 py-10 text-sm leading-relaxed text-slate-200 sm:px-6 lg:px-8"
>
	<!-- Hero header with official Space Apps Motif Logo & Rosette pattern -->
	<div
		class="brand-pattern-rosette flex flex-col items-start justify-between gap-6 rounded-2xl border border-yonder-500/40 bg-deep-blue/90 p-6 shadow-xl sm:flex-row sm:items-center sm:p-8"
	>
		<div>
			<div
				class="inline-flex items-center gap-2 rounded-full border border-neon-yellow/60 bg-electric-blue/50 px-3 py-1 text-xs font-bold tracking-wider text-neon-yellow uppercase"
			>
				<Award class="h-4 w-4 text-neon-yellow" />
				<span>NASA Space Apps Challenge 2026 • Yangon</span>
			</div>
			<h1 class="mt-3 text-3xl font-black text-white sm:text-4xl">Dancing with the SARs</h1>
			<!-- Brand Guide Pages 12-16: Alternating two-color subheading lines -->
			<p class="mt-2 text-base font-light sm:text-lg">
				<span class="block font-medium text-neon-yellow">
					Built with passion by Team <strong>YOUTHs</strong> in Yangon, Myanmar
				</span>
				<span class="block text-white">
					to reveal Earth surface processes through synthetic aperture radar.
				</span>
			</p>
		</div>
		<SpaceAppsLogo variant="motif" class="h-28 w-28 shrink-0" />
	</div>

	<!-- Team & Challenge Details -->
	<section class="mt-8 grid grid-cols-1 gap-6 md:grid-cols-2" aria-labelledby="challenge-title">
		<div
			class="brand-pattern-orbits rounded-xl border border-yonder-500/40 bg-deep-blue/95 p-5 shadow-lg"
		>
			<h2 id="challenge-title" class="flex items-center gap-2 text-base font-bold text-white">
				<Satellite class="h-4 w-4 text-yonder-400" />
				<span>The NASA Challenge</span>
			</h2>
			<p class="mt-2 text-xs leading-relaxed text-slate-200">
				NASA's "Dancing with the SARs" challenge calls for teams to leverage Synthetic Aperture
				Radar (SAR) data to make complex Earth surface changes accessible, intuitive, and
				scientifically transparent. Team YOUTHs built a monitoring tool for Hpakant, Kachin State,
				where inspectors cannot go and monsoon cloud blinds optical satellites. Both modules run on
				real NISAR data: one maps surface change in the jade-mining belt, the other measures how its
				landslide-prone slopes move.
			</p>
		</div>

		<div
			class="brand-pattern-fiduciaries rounded-xl border border-yonder-500/40 bg-deep-blue/95 p-5 shadow-lg"
		>
			<h2 class="flex items-center gap-2 text-base font-bold text-white">
				<Cpu class="h-4 w-4 text-neon-yellow" />
				<span>Our Philosophy: Scientific Integrity</span>
			</h2>
			<p class="mt-2 text-xs leading-relaxed text-slate-200">
				The Hpakant module runs on <strong>real NISAR L2 GCOV and GUNW granules</strong> from NASA's ASF
				DAAC, and lists every granule it used and every pass it excluded, with the reason. It reports
				surface change consistent with excavation, with a false-alarm estimate, and never calls it mining
				or illegal. The slope module measures line-of-sight ground motion from real GUNW interferograms
				and NASADEM slope, and calls what it finds places to check, not confirmed landslides. There is
				no simulated data in the app, and no AI model generates any text.
			</p>
		</div>
	</section>

	<!-- NISAR Mission Specifications -->
	<section class="mt-10" aria-labelledby="satellite-specs">
		<h2
			id="satellite-specs"
			class="flex items-center gap-2 border-b border-yonder-500/30 pb-2 text-xl font-bold text-white"
		>
			<Radio class="h-5 w-5 text-yonder-400" />
			<span>NASA-ISRO SAR (NISAR) Mission Overview</span>
		</h2>
		<p class="mt-3 text-xs leading-relaxed text-slate-200 sm:text-sm">
			Launched on July 30, 2025, NISAR is the first satellite radar mission to feature
			dual-frequency Synthetic Aperture Radar: an <strong>L-band</strong> radar (24 cm wavelength)
			built by NASA/JPL and an <strong>S-band</strong> radar (9 cm wavelength) built by ISRO.
		</p>

		<div
			class="font-mono-telemetry mt-5 grid grid-cols-1 gap-4 text-xs sm:grid-cols-2 lg:grid-cols-4"
		>
			<div
				class="brand-pattern-fiduciaries rounded-lg border border-yonder-500/40 bg-deep-blue/95 p-3.5"
			>
				<span class="block font-sans text-[10px] text-slate-300 uppercase">Orbit Repeat</span>
				<span class="text-base font-bold text-yonder-400">12 Days</span>
				<span class="mt-0.5 block font-sans text-[11px] text-slate-200">Exact repeat pass</span>
			</div>
			<div
				class="brand-pattern-fiduciaries rounded-lg border border-yonder-500/40 bg-deep-blue/95 p-3.5"
			>
				<span class="block font-sans text-[10px] text-slate-300 uppercase">Wavelength</span>
				<span class="text-base font-bold text-neon-yellow">24 cm (L-band)</span>
				<span class="mt-0.5 block font-sans text-[11px] text-slate-200"
					>Observes through cloud cover</span
				>
			</div>
			<div
				class="brand-pattern-fiduciaries rounded-lg border border-yonder-500/40 bg-deep-blue/95 p-3.5"
			>
				<span class="block font-sans text-[10px] text-slate-300 uppercase">GCOV Pixel Spacing</span>
				<span class="text-base font-bold text-neon-yellow">10m / 20m</span>
				<span class="mt-0.5 block font-sans text-[11px] text-slate-200"
					>Depends on acquisition mode</span
				>
			</div>
			<div
				class="brand-pattern-fiduciaries rounded-lg border border-yonder-500/40 bg-deep-blue/95 p-3.5"
			>
				<span class="block font-sans text-[10px] text-slate-300 uppercase">Antenna Reflector</span>
				<span class="text-base font-bold text-white">12 Meter</span>
				<span class="mt-0.5 block font-sans text-[11px] text-slate-200">Deployable mesh boom</span>
			</div>
		</div>
	</section>

	<!-- Methodology Pipeline -->
	<section class="mt-10" aria-labelledby="methodology-title">
		<h2
			id="methodology-title"
			class="flex items-center gap-2 border-b border-yonder-500/30 pb-2 text-xl font-bold text-white"
		>
			<Cpu class="h-5 w-5 text-yonder-400" />
			<span>How Each Module Works</span>
		</h2>

		<div class="mt-4 grid grid-cols-1 gap-4 text-xs leading-relaxed md:grid-cols-2">
			<div class="brand-pattern-waves rounded-lg border border-neon-yellow/50 bg-deep-blue/95 p-4">
				<h3 class="text-sm font-semibold text-white">Hpakant surface change (real NISAR data)</h3>
				<ol class="mt-2 list-inside list-decimal space-y-1.5 text-slate-200">
					<li>
						<strong>Real passes</strong>: NISAR Track 062 (descending), Frame 075, read from ASF
						DAAC for a 16 km window over the Hpakant jade-mining district.
					</li>
					<li>
						<strong>Pass selection</strong>: one acquisition mode and processing version only.
						Early-2026 passes with non-physical calibration offsets are excluded and listed.
					</li>
					<li>
						<strong>Lee filter</strong>, then a per-pass offset so stable vegetated ground matches
						the latest pass.
					</li>
					<li>
						HV down more than <strong>3 dB</strong> on formerly vegetated ground: vegetation loss or new
						bare ground. HH below −18 dB: new open water.
					</li>
					<li>
						Counted only when <strong>two consecutive passes</strong> agree, in patches of 1 ha or more.
					</li>
					<li>
						<strong>Uncertainty</strong>: the same rule between the two baseline passes gives the
						false-alarm rate; GUNW coherence is supporting evidence.
					</li>
				</ol>
			</div>
			<div class="brand-pattern-waves rounded-lg border border-neon-yellow/50 bg-deep-blue/95 p-4">
				<h3 class="text-sm font-semibold text-white">Hpakant slope motion (real NISAR InSAR)</h3>
				<ol class="mt-2 list-inside list-decimal space-y-1.5 text-slate-200">
					<li>
						<strong>Real interferograms</strong>: every 12-day NISAR L2 GUNW pair for the same Track
						062 Frame 075 window, read from ASF DAAC.
					</li>
					<li>
						<strong>Line-of-sight motion</strong> from the unwrapped phase, minus the product's own ionosphere
						screen; positive is toward the satellite (ISCE3 convention).
					</li>
					<li>
						Only <strong>coherent</strong> pixels (≥ 0.3) inside an unwrapping connected component are
						read; each pair is tied to flat, coherent reference ground.
					</li>
					<li>
						<strong>Mean rate</strong> per pixel over the measured pairs; gaps between pairs are not filled
						in.
					</li>
					<li>
						<strong>Candidate</strong>: ground steeper than 20° in NASA's NASADEM moving faster than
						3× the reference scatter, the same way on most pairs.
					</li>
					<li>
						A candidate is a <strong>landslide indicator to check</strong>, not a confirmed slide;
						only the height-dependent part of the troposphere is removed, so patchy water vapour
						stays in the noise.
					</li>
				</ol>
			</div>
		</div>
	</section>

	<!-- Future applications -->
	<section class="mt-10" aria-labelledby="future-title">
		<h2
			id="future-title"
			class="flex items-center gap-2 border-b border-yonder-500/30 pb-2 text-xl font-bold text-white"
		>
			<Rocket class="h-5 w-5 text-neon-yellow" />
			<span>What NISAR Could Do Next for Myanmar</span>
		</h2>
		<p class="mt-3 text-xs leading-relaxed text-slate-200">
			Next steps from research to operation. These are proposals, not results of this project.
		</p>
		<div class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
			{#each futureApplications as item (item.title)}
				<div class="brand-pattern-waves rounded-lg border border-yonder-500/40 bg-deep-blue/95 p-4">
					<h3 class="text-sm font-semibold text-white">{item.title}</h3>
					<p class="mt-1.5 text-xs leading-relaxed text-slate-200">{item.body}</p>
				</div>
			{/each}
		</div>
	</section>

	<!-- Data Citations & DAAC Attribution -->
	<section
		class="brand-pattern-orbits mt-10 rounded-xl border border-yonder-500/40 bg-deep-blue/95 p-6 shadow-xl"
		aria-labelledby="citations-title"
	>
		<h2 id="citations-title" class="flex items-center gap-2 text-base font-bold text-white">
			<Database class="h-4 w-4 text-yonder-400" />
			<span>Data Sources & Open Science Provenance</span>
		</h2>
		<div class="mt-3 space-y-2 text-xs leading-relaxed text-slate-200">
			<p>
				The app uses real products of the
				<strong>NASA-ISRO SAR (NISAR) Mission</strong> (L2 GCOV backscatter and L2 GUNW
				interferograms, provisional release) for both modules, and terrain slope from
				<strong>NASADEM</strong> (NASA/JPL, distributed by the LP DAAC). NISAR products are archived
				and distributed by the
				<strong>Alaska Satellite Facility (ASF) Distributed Active Archive Center (DAAC)</strong> and
				searchable in NASA Earthdata Search. Methods follow the NASA SAR Handbook (SERVIR, 2019) and ASF
				HyP3 processing documentation.
			</p>
			<p>
				Basemap tiles are provided by <strong>OpenFreeMap</strong>, using OpenMapTiles and
				OpenStreetMap contributors' data. Client application engineered with SvelteKit, TypeScript,
				MapLibre GL JS, and TailwindCSS. Detection in Python (NumPy, SciPy, scikit-image).
			</p>
		</div>

		<div class="mt-4 flex flex-wrap gap-4 pt-2">
			<a
				href="https://nisar-docs.asf.alaska.edu/"
				target="_blank"
				rel="noreferrer"
				class="brand-link-secondary inline-flex items-center gap-1.5 text-xs"
			>
				<span>ASF NISAR Product Guides (GCOV, GUNW)</span>
				<ExternalLink class="h-3 w-3" />
			</a>
			<a
				href="https://nisar.jpl.nasa.gov"
				target="_blank"
				rel="noreferrer"
				class="brand-link-secondary inline-flex items-center gap-1.5 text-xs"
			>
				<span>NASA JPL NISAR Mission Portal</span>
				<ExternalLink class="h-3 w-3" />
			</a>
			<a
				href="https://www.spaceappschallenge.org"
				target="_blank"
				rel="noreferrer"
				class="brand-link-secondary inline-flex items-center gap-1.5 text-xs"
			>
				<span>NASA Space Apps Challenge</span>
				<ExternalLink class="h-3 w-3" />
			</a>
		</div>
	</section>
</div>
