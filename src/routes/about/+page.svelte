<script lang="ts">
	import { Satellite, Radio, Cpu, Database, Award, ExternalLink, Rocket } from 'lucide-svelte';
	import SpaceAppsLogo from '$lib/components/brand/SpaceAppsLogo.svelte';

	const futureApplications = [
		{
			title: 'Monsoon flood maps every 12 days',
			body: 'NISAR images the same ground on a 12-day repeat, through cloud. With calibrated thresholds and river-gauge checks, the Ayeyarwady delta and Bago river plains could get flood-extent maps during the season when optical satellites see least.'
		},
		{
			title: 'Rice-season monitoring (shown here for one season)',
			body: 'Twelve NISAR passes already show the paddies around Hlawga flooding in late August and brightening as the rice grows into October. Rice is Myanmar’s staple crop and most of it is grown in the monsoon, when clouds hide fields from optical satellites. The same method, scaled to the Ayeyarwady and Bago plains and checked against township crop calendars, could tell agricultural extension officers when fields were planted and which are lagging, without a field visit.'
		},
		{
			title: 'Reservoir and wetland watch',
			body: 'Hlawga supplies drinking water to Yangon. Across 12 passes its surface stays radar-bright whatever the wind, which is unusual for open water and worth checking for floating plants such as water hyacinth. Repeat NISAR passes, paired with operator level records, could flag such changes for the water utility every 12 days.'
		},
		{
			title: 'Ground motion from InSAR',
			body: 'NISAR interferometric products (GUNW) measure centimetre-scale ground movement. They could map deformation along the Sagaing Fault after earthquakes such as the March 2025 Mandalay earthquake, or test whether parts of Yangon are slowly sinking.'
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
				scientifically transparent. Team YOUTHs built this product around one monsoon season of
				surface change near our home city of Yangon: 12 NISAR passes over the paddy fields and
				reservoir at Hlawga, from flooded fields in August to growing rice in October.
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
				We strictly distinguish between <strong>NASA observations</strong> (raw calibrated
				backscatter from ASF DAAC), <strong>our deterministic processing</strong> (speckle filtering
				and decibel thresholding), and <strong>record-based explanations</strong>. The current
				summary uses a deterministic template; no live AI model is called.
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
			<span>Our Scientific Methodology</span>
		</h2>

		<div class="mt-4 space-y-3 text-xs leading-relaxed">
			<p>
				Our demonstration compares two L-band GCOV observations of Hlawga Reservoir (August 27 and
				September 8, 2026) using deterministic thresholding. It flags possible water changes for
				investigation:
			</p>

			<ol class="list-inside list-decimal space-y-2 pl-2 text-slate-200">
				<li>
					<strong>Radiometric Terrain-Corrected Backscatter:</strong> We ingest geocoded
					gamma-naught (&gamma;<sup>0</sup>) radar backscatter in the co-polarized (HH) channel.
				</li>
				<li>
					<strong>Lee Speckle Filtering:</strong> Granular speckle noise inherent to coherent radar systems
					is smoothed using a 3&times;3 Lee filter for this case study. Residual speckle can remain.
				</li>
				<li>
					<strong>Specular Reflection Cutoff:</strong> Smooth open water surfaces reflect microwave beams
					away from the sensor. We isolate pixels dropping below an empirical threshold (-9.54 dB for
					this study area).
				</li>
				<li>
					<strong>Connected Component Clustering:</strong> Pockets of detected change smaller than 8 contiguous
					pixels are rejected to reduce small isolated detections. This can also discard small real changes.
				</li>
				<li>
					<strong>Polarization Quality Check:</strong> We compare the HH and cross-polarized HV channels
					on both dates, with the product's own interference and noise metadata. In these provisional
					scenes HV fails our consistency checks, so classification uses HH only.
				</li>
				<li>
					<strong>HH Change Map:</strong> A per-pixel dB difference between the dates shows where the
					radar return brightened or darkened, beyond the water/land threshold. We then weigh competing
					physical explanations against the recorded evidence.
				</li>
				<li>
					<strong>Surface Extent Calculation:</strong> Vectorized boundaries are transformed into GeoJSON
					polygons and area statistics (km²) for high-performance MapLibre WebGL rendering.
				</li>
			</ol>
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
			Our case study uses two dates and one channel. These are directions a longer NISAR record
			could support; they are proposals, not results of this project.
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
				The real observation products originate from the <strong
					>NASA-ISRO SAR (NISAR) Mission</strong
				>, archived and distributed publicly by the
				<strong>Alaska Satellite Facility (ASF) Distributed Active Archive Center (DAAC)</strong>.
				Synthetic demonstrations are labeled separately and do not represent observed events.
			</p>
			<p>
				Basemap tiles are provided by <strong>OpenFreeMap</strong>, using OpenMapTiles and
				OpenStreetMap contributors' data. The independent optical check uses modified Copernicus
				Sentinel-2 data (2026) via Element 84 Earth Search. Weather records come from ERA5
				reanalysis via Open-Meteo (CC BY 4.0) and Yangon International Airport METAR reports via the
				Iowa Environmental Mesonet. Client application engineered with SvelteKit, TypeScript,
				MapLibre GL JS, and TailwindCSS.
			</p>
		</div>

		<div class="mt-4 flex flex-wrap gap-4 pt-2">
			<a
				href="https://nisar-docs.asf.alaska.edu/gcov/"
				target="_blank"
				rel="noreferrer"
				class="brand-link-secondary inline-flex items-center gap-1.5 text-xs"
			>
				<span>ASF NISAR GCOV Product Guide</span>
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
