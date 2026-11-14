<script lang="ts">
	import { appState } from '$lib/stores/appState.svelte';
	import { X, Radio, Sun, Waves, Trees, ShieldAlert } from 'lucide-svelte';

	type SimulationMode =
		'optical_cloud' | 'sar_clouds' | 'specular_water' | 'diffuse_land' | 'double_bounce';

	let activeMode = $state<SimulationMode>('sar_clouds');

	const modes: Array<{ id: SimulationMode; label: string; icon: typeof Radio }> = [
		{ id: 'optical_cloud', label: '1. Optical Satellites vs Clouds', icon: Sun },
		{ id: 'sar_clouds', label: '2. NISAR Microwaves (24cm)', icon: Radio },
		{ id: 'specular_water', label: '3. Why Smooth Water Looks Dark', icon: Waves },
		{ id: 'diffuse_land', label: '4. Why Land Looks Bright', icon: Trees },
		{ id: 'double_bounce', label: '5. The "Double Bounce" Edge Case', icon: ShieldAlert }
	];
</script>

{#if appState.isSarModalOpen}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-md"
		role="dialog"
		aria-modal="true"
		aria-labelledby="sar-explainer-title"
	>
		<div
			class="relative flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-xl border border-yonder-500/40 bg-deep-blue shadow-[0_0_50px_rgba(46,150,245,0.25)]"
		>
			<!-- Header -->
			<div
				class="brand-pattern-waves flex items-center justify-between border-b border-yonder-500/30 bg-deep-blue px-5 py-3.5"
			>
				<div class="flex items-center gap-2.5">
					<div
						class="flex h-8 w-8 items-center justify-center rounded-lg border border-yonder-500/50 bg-electric-blue/50 text-neon-yellow"
					>
						<Radio class="h-4 w-4 animate-pulse" />
					</div>
					<div>
						<h2 id="sar-explainer-title" class="text-sm font-bold text-white sm:text-base">
							How NISAR Sees It: Synthetic Aperture Radar Physics
						</h2>
						<p class="text-xs text-slate-300">
							Active microwave remote sensing through weather, clouds, and darkness
						</p>
					</div>
				</div>

				<button
					type="button"
					onclick={() => {
						appState.isSarModalOpen = false;
					}}
					class="rounded-lg border border-yonder-500/40 bg-electric-blue/30 p-1.5 text-slate-200 transition-colors hover:border-neon-yellow hover:text-neon-yellow"
					aria-label="Close explainer"
				>
					<X class="h-4 w-4" />
				</button>
			</div>

			<!-- Interactive Tab Navigation -->
			<div
				class="flex flex-wrap gap-1 border-b border-yonder-500/30 bg-deep-blue/90 p-2 text-xs font-medium"
			>
				{#each modes as m (m.id)}
					{@const Icon = m.icon}
					<button
						type="button"
						onclick={() => {
							activeMode = m.id;
						}}
						class="flex items-center gap-1.5 rounded-md px-3 py-1.5 transition-all {activeMode ===
						m.id
							? 'border border-neon-yellow/70 bg-electric-blue/60 font-bold text-neon-yellow shadow-sm'
							: 'text-slate-300 hover:bg-electric-blue/30 hover:text-white'}"
					>
						<Icon class="h-4 w-4" />
						<span>{m.label}</span>
					</button>
				{/each}
			</div>

			<!-- Interactive Visual Simulation Stage -->
			<div
				class="relative flex h-64 w-full items-center justify-center overflow-hidden border-b border-slate-800 bg-slate-950 p-4"
			>
				<svg
					viewBox="0 0 700 240"
					class="h-full w-full max-w-2xl select-none"
					xmlns="http://www.w3.org/2000/svg"
				>
					<!-- Starfield / Space background -->
					<rect width="700" height="240" fill="#0c2259" />

					<!-- Orbiting Satellite (top left) -->
					<g transform="translate(100, 35)">
						<rect
							x="-18"
							y="-10"
							width="36"
							height="20"
							rx="3"
							fill="#16306a"
							stroke="#2e96f5"
							stroke-width="1.5"
						/>
						<!-- Solar panels -->
						<rect x="-42" y="-7" width="20" height="14" rx="1" fill="#0042a6" stroke="#82bdf9" />
						<rect x="22" y="-7" width="20" height="14" rx="1" fill="#0042a6" stroke="#82bdf9" />
						<!-- Antenna dish -->
						<path d="M-8,12 Q0,20 8,12" fill="none" stroke="#eafe07" stroke-width="2.5" />
						<text
							x="0"
							y="-16"
							fill="#93a6cc"
							font-size="10"
							text-anchor="middle"
							font-family="monospace"
						>
							{activeMode === 'optical_cloud' ? 'Optical Satellite' : 'NISAR (L-band)'}
						</text>
					</g>

					<!-- Atmospheric Cloud Layer (mid altitude) -->
					<g transform="translate(260, 90)">
						<ellipse cx="60" cy="10" rx="90" ry="24" fill="#2a447e" opacity="0.85" />
						<ellipse cx="150" cy="18" rx="80" ry="20" fill="#4d6496" opacity="0.8" />
						<ellipse cx="100" cy="0" rx="70" ry="22" fill="#8094bf" opacity="0.7" />
						<text
							x="110"
							y="14"
							fill="#d3dcee"
							font-size="11"
							text-anchor="middle"
							font-weight="600"
						>
							Dense Monsoon Clouds & Rain
						</text>
					</g>

					<!-- Ground Surface (bottom) -->
					<line x1="0" y1="210" x2="700" y2="210" stroke="#2a447e" stroke-width="2" />

					<!-- MODE 1: OPTICAL SAT BLOCKED BY CLOUDS -->
					{#if activeMode === 'optical_cloud'}
						<!-- Sunlight rays bouncing off top of cloud -->
						<line
							x1="100"
							y1="45"
							x2="310"
							y2="85"
							stroke="#eafe07"
							stroke-width="2"
							stroke-dasharray="4,4"
						/>
						<!-- Cloud scattering reflection back to sat -->
						<line x1="310" y1="85" x2="110" y2="45" stroke="#eafe07" stroke-width="2" />
						<circle cx="310" cy="85" r="5" fill="#eafe07" opacity="0.8" />
						<text x="440" y="80" fill="#ff7f5c" font-size="11" font-weight="bold">
							✕ Visible Light Blocked (0% Surface View)
						</text>
						<!-- Blocked path beneath clouds -->
						<text
							x="350"
							y="160"
							fill="#8094bf"
							font-size="12"
							font-style="italic"
							text-anchor="middle"
						>
							Ground invisible to optical sensors during monsoon season
						</text>
					{/if}

					<!-- MODE 2: SAR PENETRATING CLOUDS -->
					{#if activeMode === 'sar_clouds'}
						<!-- Transmitted 24cm Microwave Pulse penetrating right through -->
						<line
							x1="100"
							y1="48"
							x2="400"
							y2="210"
							stroke="#2e96f5"
							stroke-width="3"
							stroke-dasharray="6,4"
						>
							<animate
								attributeName="stroke-dashoffset"
								values="40;0"
								dur="1s"
								repeatCount="indefinite"
							/>
						</line>
						<!-- Wave ripples -->
						<circle
							cx="280"
							cy="140"
							r="14"
							fill="none"
							stroke="#2e96f5"
							stroke-width="1.5"
							opacity="0.6"
						/>
						<circle
							cx="340"
							cy="175"
							r="14"
							fill="none"
							stroke="#2e96f5"
							stroke-width="1.5"
							opacity="0.6"
						/>
						<!-- Returned microwave backscatter -->
						<line
							x1="400"
							y1="210"
							x2="100"
							y2="48"
							stroke="#82bdf9"
							stroke-width="2"
							stroke-dasharray="4,4"
							opacity="0.8"
						/>
						<text x="690" y="145" fill="#34d399" font-size="11" font-weight="bold" text-anchor="end">
							✓ L-band radar can observe through cloud cover
						</text>
					{/if}

					<!-- MODE 3: SPECULAR REFLECTION (WATER = BLACK) -->
					{#if activeMode === 'specular_water'}
						<!-- Calm water surface -->
						<rect x="250" y="206" width="300" height="20" fill="#0960e1" opacity="0.8" />
						<text
							x="400"
							y="222"
							fill="#eef6ff"
							font-size="10"
							text-anchor="middle"
							font-weight="bold"
						>
							Smooth Inundated Water Surface
						</text>

						<!-- Incident microwave beam -->
						<line x1="100" y1="48" x2="380" y2="206" stroke="#2e96f5" stroke-width="3" />
						<!-- Specular reflection: bounces away like a mirror -->
						<line
							x1="380"
							y1="206"
							x2="660"
							y2="50"
							stroke="#2e96f5"
							stroke-width="3"
							stroke-dasharray="5,3"
						/>

						<!-- Angle indicator -->
						<path
							d="M 350,206 A 30 30 0 0 1 410,206"
							fill="none"
							stroke="#eafe07"
							stroke-width="1.5"
						/>
						<text x="380" y="195" fill="#eafe07" font-size="10" text-anchor="middle"
							>θ incident = θ reflect</text
						>

						<!-- Result on satellite -->
						<text x="130" y="80" fill="#ff7f5c" font-size="11" font-weight="bold">
							LOW RETURN: SMOOTH WATER OFTEN APPEARS DARK
						</text>
						<text x="130" y="96" fill="#93a6cc" font-size="10">
							Water acts as a specular mirror → Often appears dark in SAR
						</text>
					{/if}

					<!-- MODE 4: DIFFUSE SCATTERING (LAND = BRIGHT) -->
					{#if activeMode === 'diffuse_land'}
						<!-- Rough trees & terrain -->
						<g transform="translate(320, 185)">
							<polygon points="10,25 20,0 30,25" fill="#15803d" />
							<polygon points="35,25 45,5 55,25" fill="#16a34a" />
							<polygon points="60,25 70,0 80,25" fill="#15803d" />
							<polygon points="85,25 95,8 105,25" fill="#166534" />
						</g>
						<text x="380" y="224" fill="#86efac" font-size="10" text-anchor="middle">
							Rough Forest & Agricultural Vegetation
						</text>

						<!-- Incident beam -->
						<line x1="100" y1="48" x2="380" y2="195" stroke="#2e96f5" stroke-width="3" />
						<!-- Diffuse rays bouncing in all directions -->
						<line x1="380" y1="195" x2="100" y2="48" stroke="#34d399" stroke-width="2.5" />
						<line
							x1="380"
							y1="195"
							x2="260"
							y2="100"
							stroke="#34d399"
							stroke-width="1.5"
							stroke-dasharray="3,3"
							opacity="0.6"
						/>
						<line
							x1="380"
							y1="195"
							x2="520"
							y2="110"
							stroke="#34d399"
							stroke-width="1.5"
							stroke-dasharray="3,3"
							opacity="0.6"
						/>

						<text x="130" y="80" fill="#34d399" font-size="11" font-weight="bold">
							STRONG RETURN TO SENSOR (-8 to 0 dB)
						</text>
						<text x="130" y="96" fill="#93a6cc" font-size="10">
							Rough surfaces scatter energy back to satellite → Appears Bright
						</text>
					{/if}

					<!-- MODE 5: DOUBLE BOUNCE (FLOODED VEGETATION LIMITATION) -->
					{#if activeMode === 'double_bounce'}
						<!-- Tree trunk standing in floodwater -->
						<rect x="360" y="206" width="120" height="15" fill="#0960e1" />
						<rect x="400" y="160" width="12" height="46" fill="#78350f" />
						<circle cx="406" cy="155" r="18" fill="#15803d" />

						<!-- Incident beam to water surface -->
						<line x1="100" y1="48" x2="390" y2="206" stroke="#2e96f5" stroke-width="3" />
						<!-- Bounce 1: Water to tree trunk -->
						<line x1="390" y1="206" x2="400" y2="185" stroke="#eafe07" stroke-width="3" />
						<!-- Bounce 2: Tree trunk straight back to satellite! -->
						<line x1="400" y1="185" x2="100" y2="48" stroke="#e43700" stroke-width="3" />

						<text x="130" y="80" fill="#ff7f5c" font-size="11" font-weight="bold">
							DOUBLE BOUNCE: FLOODED FOREST CAN LOOK BRIGHT!
						</text>
						<text x="130" y="96" fill="#d3dcee" font-size="10">
							Water + vertical trunk acts as a 90° corner reflector. This is why our pipeline notes
							this known limitation.
						</text>
					{/if}
				</svg>
			</div>

			<!-- Scientific Explanation Details -->
			<div class="space-y-3 overflow-y-auto p-5 text-xs leading-relaxed text-slate-200">
				{#if activeMode === 'optical_cloud'}
					<div class="rounded-lg border border-rocket-red/70 bg-martian-red/90 p-3 text-white">
						<h3 class="mb-1 text-sm font-bold text-white">
							The Optical Satellite Limitation
						</h3>
						<p>
							Optical instruments can measure reflected sunlight in visible and infrared bands.
							Thick cloud cover can obscure the surface, limiting observations during some storms.
							Radar provides a complementary view and does not require sunlight.
						</p>
					</div>
				{:else if activeMode === 'sar_clouds'}
					<div class="rounded-lg border border-yonder-500/50 bg-electric-blue/35 p-3 text-white">
						<h3 class="mb-1 text-sm font-bold text-white">NISAR Active L-Band Microwaves</h3>
						<p>
							NISAR does not rely on sunlight. It transmits its own high-power radar pulses at a <strong
								>24 cm wavelength (L-band, 1.25 GHz)</strong
							>. Because this microwave wavelength is thousands of times larger than typical cloud
							droplets and atmospheric moisture particles, the waves pass through dense storm
							systems and rain with much less cloud interference than visible light. Furthermore, it
							operates equally well at midnight as it does at noon.
						</p>
					</div>
				{:else if activeMode === 'specular_water'}
					<div class="rounded-lg border border-yonder-500/50 bg-electric-blue/35 p-3 text-white">
						<h3 class="mb-1 text-sm font-bold text-yonder-400">
							Specular Reflection: The Key to Flood Mapping
						</h3>
						<p>
							Smooth water often reflects radar energy away from the sensor and appears dark. The
							return also depends on wind, surface roughness, viewing geometry and polarization.
							There is no universal water threshold; our Hlawga comparison uses a scene-specific
							threshold and remains unconfirmed.
						</p>
					</div>
				{:else if activeMode === 'diffuse_land'}
					<div class="rounded-lg border border-yonder-500/50 bg-electric-blue/35 p-3 text-white">
						<h3 class="mb-1 text-sm font-bold text-white">
							Diffuse Scattering: Surrounding Land & Vegetation
						</h3>
						<p>
							Rough surfaces and vegetation can scatter more energy back toward the satellite and
							appear bright. Moisture, structure and viewing geometry also affect the return, so
							brightness alone cannot identify a land-cover class.
						</p>
					</div>
				{:else}
					<div class="rounded-lg border border-rocket-red/70 bg-martian-red/90 p-3 text-white">
						<h3 class="mb-1 text-sm font-bold text-white">
							The Double-Bounce Caveat (Scientific Honesty)
						</h3>
						<p>
							When water floods into a forest or tall agricultural crop (like maize or sugarcane),
							an interesting physical interaction occurs: the radar wave bounces off the smooth
							water surface, strikes the vertical tree trunk at a 90° angle, and reflects straight
							back into space toward the satellite. This "corner reflector" effect causes flooded
							forests to appear <em>brighter</em> rather than darker. This is why our team explicitly
							documents this limitation in our methodology.
						</p>
					</div>
				{/if}

				<!-- Summary pill footer -->
				<div
					class="flex items-center justify-between border-t border-yonder-500/30 pt-2 text-[11px] text-slate-300"
				>
					<span>Mission: NASA-ISRO Synthetic Aperture Radar (NISAR)</span>
					<span class="font-mono-telemetry text-neon-yellow"
						>Pixel spacing: 10m in this case study</span
					>
				</div>
				{#if appState.isDemoModeActive}
					<!-- This modal covers the tour bar, so the tour continues from here. -->
					<div class="mt-3 flex justify-end">
						<button
							type="button"
							class="brand-btn-primary rounded-md px-4 py-1.5 text-xs shadow-md"
							onclick={() => appState.nextDemoStep()}
						>
							Continue tour →
						</button>
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}
