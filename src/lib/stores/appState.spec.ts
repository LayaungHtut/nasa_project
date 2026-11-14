import { describe, it, expect } from 'vitest';
import { appState } from './appState.svelte';

describe('Global App State Store', () => {
	it('should initialize with yangon-track40-frame10 as default event', () => {
		expect(appState.selectedEventId).toBe('yangon-track40-frame10');
		expect(appState.selectedEvent.id).toBe('yangon-track40-frame10');
		expect(appState.selectedEvent.data_status).toBe('REAL');
		expect(appState.activeLayer).toBe('compare');
	});

	it('should switch events and update active event', () => {
		appState.selectEvent('demo-yangon-fixture');
		expect(appState.selectedEventId).toBe('demo-yangon-fixture');
		expect(appState.selectedEvent.data_status).toBe('SYNTHETIC_PLACEHOLDER');

		appState.selectEvent('bago-flood-2026');
		expect(appState.selectedEventId).toBe('bago-flood-2026');
		expect(appState.selectedEvent.location.name).toContain('Bago');

		// Switch back to real event
		appState.selectEvent('yangon-track40-frame10');
		expect(appState.selectedEventId).toBe('yangon-track40-frame10');
		expect(appState.selectedEvent.data_status).toBe('REAL');
	});

	it('should manage Judge Demo Mode flow cleanly', () => {
		appState.startJudgeDemo();
		expect(appState.isDemoModeActive).toBe(true);
		expect(appState.demoStep).toBe(1);

		appState.nextDemoStep();
		expect(appState.demoStep).toBe(2);
		expect(appState.selectedEventId).toBe('yangon-track40-frame10');

		appState.nextDemoStep();
		expect(appState.demoStep).toBe(3);
		expect(appState.activeLayer).toBe('baseline');

		appState.nextDemoStep();
		expect(appState.demoStep).toBe(4);
		expect(appState.activeLayer).toBe('post');

		appState.nextDemoStep();
		expect(appState.demoStep).toBe(5);
		expect(appState.activeLayer).toBe('change_mask');

		appState.nextDemoStep();
		expect(appState.demoStep).toBe(6);
		expect(appState.activeLayer).toBe('difference');
		expect(appState.polarization).toBe('HH');

		appState.nextDemoStep();
		expect(appState.demoStep).toBe(7);
		expect(appState.activeLayer).toBe(
			appState.selectedEvent.timeseries ? 'field_timing' : 'difference'
		);

		appState.nextDemoStep();
		expect(appState.isSarModalOpen).toBe(true);
		appState.nextDemoStep();
		expect(appState.demoStep).toBe(9);
		expect(appState.isSarModalOpen).toBe(false);
		appState.nextDemoStep();
		expect(appState.isDemoModeActive).toBe(false);
		expect(appState.demoStep).toBe(0);
	});
	it('clears optical selection when switching events', () => {
		appState.selectEvent('yangon-track40-frame10');
		appState.selectCandidate(41, true);
		expect(appState.activeLayer).toBe('optical_compare');
		expect(appState.selectedCandidate?.area_m2).toBe(900);
		appState.opticalSceneId = appState.opticalEvidence!.scenes[0].id;
		appState.radarReference = 'baseline';
		appState.selectEvent('demo-yangon-fixture');
		expect(appState.selectedCandidate).toBeUndefined();
		expect(appState.opticalScene).toBeUndefined();
		expect(appState.selectedCandidateId).toBeNull();
		expect(appState.activeLayer).toBe('compare');
		appState.selectEvent('yangon-track40-frame10');
		expect(appState.radarReference).toBe('repeat');
		expect(appState.opticalScene?.datetime).toContain('2026-09-13');
	});
});
