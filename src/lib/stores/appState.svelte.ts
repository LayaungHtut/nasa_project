import type { ChangeEvent } from '$lib/types/api';
import { CURATED_EVENTS } from '$lib/data/fixtures';
import { opticalEvidence } from '$lib/data/evidence';
import type { RadarReference } from '$lib/types/evidence';
import { periodPresets } from '$lib/data/timeseries';

export type LayerViewMode =
	| 'series'
	| 'field_timing'
	| 'landcover'
	| 'period'
	| 'compare'
	| 'baseline'
	| 'post'
	| 'difference'
	| 'change_mask'
	| 'optical_compare';
export type Polarization = 'HH' | 'HV';
export const DEMO_STEP_COUNT = 9;

class AppState {
	events = $state<ChangeEvent[]>(CURATED_EVENTS);
	selectedEventId = $state<string>('yangon-track40-frame10');
	selectedEvent = $state<ChangeEvent>(CURATED_EVENTS[0]);
	activeLayer = $state<LayerViewMode>('compare');
	/** Radar channel shown in the before/after layers; only HH is used for classification. */
	polarization = $state<Polarization>('HH');
	sliderPosition = $state<number>(50); // 0 to 100%
	opacity = $state<number>(0.85);
	opticalEvidence = $derived(opticalEvidence(this.selectedEvent));
	opticalSceneId = $state<string | null>(null);
	opticalScene = $derived(
		this.opticalEvidence?.scenes.find((scene) => scene.id === this.opticalSceneId) ??
			this.opticalEvidence?.scenes.at(-1)
	);
	radarReference = $state<RadarReference>('repeat');
	selectedCandidateId = $state<number | null>(null);
	selectedCandidate = $derived(
		this.opticalEvidence?.candidates.find(
			(candidate) => candidate.component === this.selectedCandidateId
		)
	);
	candidateFocusRequest = $state(0);

	selectCandidate(id: number | null, focus = false) {
		this.selectedCandidateId = id;
		if (focus && id !== null) {
			this.activeLayer = 'optical_compare';
			this.candidateFocusRequest++;
		}
	}

	// Modals & Panels
	isSarModalOpen = $state<boolean>(false);
	isLimitationsModalOpen = $state<boolean>(false);
	isAiPanelExpanded = $state<boolean>(true);
	isProvenanceExpanded = $state<boolean>(false);

	// Timeline
	selectedObservationIndex = $state<number>(1); // Default to repeat pass (index 1)
	/** Index into selectedEvent.timeseries.dates, shown by the 'series' layer. */
	seriesIndex = $state<number>(0);
	/** Two passes chosen in 'period' mode; null until the user picks, then the first preset applies. */
	periodChoice = $state<{ from: number; to: number } | null>(null);
	periodPresets = $derived(
		this.selectedEvent.timeseries
			? periodPresets(
					this.selectedEvent.timeseries,
					this.selectedEvent.observation_dates.baseline,
					this.selectedEvent.observation_dates.post_event
				)
			: []
	);
	/** Land-cover layer: overlay the two-date apparent water loss on the classes. */
	showWaterLoss = $state(true);
	periodRange = $derived(this.periodChoice ?? this.periodPresets[0] ?? null);

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
			this.seriesIndex = 0;
			this.periodChoice = null;
			this.polarization = 'HH';
			this.opticalSceneId = null;
			this.radarReference = 'repeat';
			this.selectedCandidateId = null;
			this.candidateFocusRequest = 0;
		}
	}

	startJudgeDemo() {
		this.selectEvent('yangon-track40-frame10');
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
			case 1: // Hook: the season animation when the event has one
				this.activeLayer = this.selectedEvent.timeseries ? 'series' : 'compare';
				this.seriesIndex = 0;
				this.sliderPosition = 50;
				break;
			case 2: // Fly to Event
				this.selectEvent('yangon-track40-frame10');
				break;
			case 3: // Baseline view (August 27, 2026 reference)
				this.activeLayer = 'baseline';
				this.selectedObservationIndex = 0;
				break;
			case 4: // Post-Event view (September 8, 2026 repeat pass)
				this.activeLayer = 'post';
				this.selectedObservationIndex = 1;
				break;
			case 5: // Reveal change detected
				this.activeLayer = 'change_mask';
				break;
			case 6: // HH change map and competing explanations
				this.isSarModalOpen = false;
				this.polarization = 'HH';
				this.activeLayer = 'difference';
				break;
			case 7: // Field by field: the per-pixel test with forest as the control
				this.isSarModalOpen = false;
				this.activeLayer = this.selectedEvent.timeseries ? 'field_timing' : 'difference';
				break;
			case 8: // SAR explainer
				this.isSarModalOpen = true;
				break;
			case 9: // Grounded AI and data provenance
				this.isSarModalOpen = false;
				this.isAiPanelExpanded = true;
				this.isProvenanceExpanded = true;
				break;
		}
	}
}

export const appState = new AppState();
