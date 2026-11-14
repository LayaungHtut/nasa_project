import { describe, expect, it } from 'vitest';
import { getAuthoritativeEvent, getAuthoritativeEvents } from './events';
import { buildReport } from './report';
import { seasonFindings } from '$lib/data/timeseries';

describe('Analysis report', () => {
	it('quotes the same numbers as the app and embeds its figures', async () => {
		const event = (await getAuthoritativeEvent('yangon-track40-frame10'))!;
		const html = buildReport(event)!;
		const f = seasonFindings(event.timeseries!);
		expect(html).toContain(`${f.loss.paddyPct}% of it lies on paddy fields`);
		expect(html).toContain(`${f.paddyRise.toFixed(1)} dB relative to forest`);
		expect(html).toContain(`${f.loss.total.toFixed(2)} km² of apparent water loss`);
		// Land cover, water loss and field timing maps travel inside the file.
		expect(html.match(/data:image\/png;base64,/g)).toHaveLength(3);
		// Every pass is in the table, and no value fell through as undefined or NaN.
		expect(html.match(/<tr[ >]/g)!.length).toBeGreaterThanOrEqual(event.timeseries!.dates.length);
		// Image data is base64, where those letters can occur by chance.
		expect(html.replace(/data:image\/[a-z+]+;base64,[\w+/=]+/g, '')).not.toMatch(/undefined|NaN/);
	});

	it('escapes text from the records', async () => {
		const event = (await getAuthoritativeEvent('yangon-track40-frame10'))!;
		const html = buildReport({ ...event, title: '<script>alert(1)</script>' })!;
		expect(html).not.toContain('<script>alert(1)</script>');
		expect(html).toContain('&lt;script&gt;');
	});

	it('is never produced for a synthetic scenario', async () => {
		const synthetic = (await getAuthoritativeEvents()).filter((e) => e.data_status !== 'REAL');
		expect(synthetic.length).toBeGreaterThan(0);
		for (const e of synthetic) expect(buildReport(e)).toBeUndefined();
	});
});
