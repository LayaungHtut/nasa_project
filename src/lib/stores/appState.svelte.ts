import { SCENARIOS } from '$lib/data/scenarios';
import { TOUR_STEPS } from '$lib/data/tour';

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
	/** Judge tour step, 1-based; 0 when the tour is off. */
	demoStep = $state(0);
	isDemoModeActive = $derived(this.demoStep > 0);

	selectScenario(id: string) {
		const s = SCENARIOS.find((x) => x.id === id);
		if (!s) return;
		this.scenarioId = id;
		this.epochIndex = s.epochs.length - 1;
	}

	/** Moves the tour to step n and sets the map to show it; any n outside the tour ends it. */
	goToDemoStep(n: number) {
		const step = TOUR_STEPS[n - 1];
		if (!step) {
			this.demoStep = 0;
			return;
		}
		this.demoStep = n;
		this.isSarModalOpen = false;
		this.showOverlays = true;
		this.scenarioId = step.scenarioId;
		this.epochIndex = step.epochIndex;
		this.layer = step.layer;
		this.sliderPosition = 50;
	}
}

export const appState = new AppState();
