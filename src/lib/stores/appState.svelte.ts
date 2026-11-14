import { SCENARIOS } from '$lib/data/scenarios';

/** Map view: one pass, a before/after swipe, or one of the two InSAR layers. */
export type ScenarioLayer = 'sar' | 'compare' | 'coherence' | 'deformation';

class AppState {
	scenarioId = $state(SCENARIOS[0].id);
	scenario = $derived(SCENARIOS.find((s) => s.id === this.scenarioId) ?? SCENARIOS[0]);
	/** Selected pass; opens on the latest so the outcome is visible first. */
	epochIndex = $state(SCENARIOS[0].epochs.length - 1);
	layer = $state<ScenarioLayer>('sar');
	sliderPosition = $state(50);
	showOverlays = $state(true);
	isSarModalOpen = $state(false);
	mapError = $state<string | null>(null);

	selectScenario(id: string) {
		const s = SCENARIOS.find((x) => x.id === id);
		if (!s) return;
		this.scenarioId = id;
		this.epochIndex = s.epochs.length - 1;
	}
}

export const appState = new AppState();
