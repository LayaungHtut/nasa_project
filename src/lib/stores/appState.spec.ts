import { describe, it, expect } from 'vitest';
import { appState } from './appState.svelte';

describe('Global App State Store', () => {
	it('should initialize with the first catalog event as default', () => {
		expect(appState.selectedEventId).toBe('demo-yangon-fixture');
		expect(appState.selectedEvent.id).toBe('demo-yangon-fixture');
		expect(appState.activeLayer).toBe('compare');
	});

	it('should switch events and update active event', () => {
		appState.selectEvent('bago-flood-2026');
		expect(appState.selectedEventId).toBe('bago-flood-2026');
		expect(appState.selectedEvent.location.name).toContain('Bago');

		appState.selectEvent('demo-yangon-fixture');
		expect(appState.selectedEventId).toBe('demo-yangon-fixture');
		expect(appState.selectedEvent.data_status).toBe('SYNTHETIC_PLACEHOLDER');
	});

	it('should manage Judge Demo Mode flow cleanly', () => {
		appState.selectEvent('bago-flood-2026');
		appState.startJudgeDemo();
		expect(appState.isDemoModeActive).toBe(true);
		expect(appState.demoStep).toBe(1);
		expect(appState.activeLayer).toBe('compare');

		appState.nextDemoStep();
		expect(appState.demoStep).toBe(2);
		expect(appState.selectedEventId).toBe('demo-yangon-fixture');

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
		expect(appState.isSarModalOpen).toBe(true);

		appState.nextDemoStep();
		expect(appState.demoStep).toBe(7);
		expect(appState.isSarModalOpen).toBe(false);

		appState.nextDemoStep();
		expect(appState.isDemoModeActive).toBe(false);
		expect(appState.demoStep).toBe(0);
	});
});
