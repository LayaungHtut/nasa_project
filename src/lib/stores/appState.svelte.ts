import type { ChangeEvent } from '$lib/types/api';
import { CURATED_EVENTS } from '$lib/data/fixtures';

export type LayerViewMode = 'compare' | 'baseline' | 'post' | 'change_mask';
export const DEMO_STEP_COUNT = 7;

class AppState {
	events = $state<ChangeEvent[]>(CURATED_EVENTS);
	selectedEventId = $state<string>(CURATED_EVENTS[0].id);
	selectedEvent = $state<ChangeEvent>(CURATED_EVENTS[0]);
	activeLayer = $state<LayerViewMode>('compare');
	sliderPosition = $state<number>(50); // 0 to 100%
	opacity = $state<number>(0.85);

	// Modals & Panels
	isSarModalOpen = $state<boolean>(false);
	isLimitationsModalOpen = $state<boolean>(false);
	isAiPanelExpanded = $state<boolean>(true);
	isProvenanceExpanded = $state<boolean>(false);

	// Timeline
	selectedObservationIndex = $state<number>(1); // Default to repeat pass (index 1)

	// Demo Mode for Space Apps judges
	isDemoModeActive = $state<boolean>(false);
	demoStep = $state<number>(0);

	// Loading and status
	isLoadingData = $state<boolean>(false);
	mapError = $state<string | null>(null);

	/**
	 * Populates the application state with authoritative events loaded from the API / SSR
	 */
	setEvents(events: ChangeEvent[]) {
		if (!events || events.length === 0) return;
		this.events = events;
		const found = events.find((e) => e.id === this.selectedEventId);
		if (found) {
			this.selectedEvent = found;
		} else {
			this.selectedEvent = events[0];
			this.selectedEventId = events[0].id;
		}
	}

	selectEvent(id: string) {
		const found = this.events.find((e) => e.id === id);
		if (found) {
			this.selectedEventId = id;
			this.selectedEvent = found;
			this.selectedObservationIndex = Math.min(
				1,
				(found.observation_dates.all_observations?.length ?? 1) - 1
			);
			this.sliderPosition = 50;
			this.activeLayer = 'compare';
		}
	}

	/** The tour follows the first event in the catalog. */
	private get demoEventId() {
		return this.events[0]?.id ?? CURATED_EVENTS[0].id;
	}

	startJudgeDemo() {
		this.selectEvent(this.demoEventId);
		this.isDemoModeActive = true;
		this.demoStep = 1;
		this.applyDemoStep(1);
	}

	nextDemoStep() {
		if (this.demoStep < DEMO_STEP_COUNT) {
			this.demoStep += 1;
			this.applyDemoStep(this.demoStep);
		} else {
			this.endJudgeDemo();
		}
	}

	prevDemoStep() {
		if (this.demoStep > 1) {
			this.demoStep -= 1;
			this.applyDemoStep(this.demoStep);
		}
	}

	endJudgeDemo() {
		this.isDemoModeActive = false;
		this.demoStep = 0;
	}

	private applyDemoStep(step: number) {
		switch (step) {
			case 1: // Hook: the two-date swipe comparison
				this.activeLayer = 'compare';
				this.sliderPosition = 50;
				break;
			case 2: // Fly to Event
				this.selectEvent(this.demoEventId);
				break;
			case 3: // Baseline view
				this.activeLayer = 'baseline';
				this.selectedObservationIndex = 0;
				break;
			case 4: // Repeat-pass view
				this.activeLayer = 'post';
				this.selectedObservationIndex = 1;
				break;
			case 5: // Reveal change detected
				this.activeLayer = 'change_mask';
				break;
			case 6: // SAR explainer
				this.isSarModalOpen = true;
				break;
			case 7: // Grounded AI and data provenance
				this.isSarModalOpen = false;
				this.isAiPanelExpanded = true;
				this.isProvenanceExpanded = true;
				break;
		}
	}
}

export const appState = new AppState();
