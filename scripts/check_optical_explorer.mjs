// Run against a production preview: npm run build, then npm run preview.
import { chromium } from 'playwright';
import assert from 'node:assert/strict';
const base = process.argv[2] || 'http://127.0.0.1:4173';
(async () => {
	let ready = false;
	for (let n = 0; n < 30; n++) {
		try {
			if ((await fetch(base, { signal: AbortSignal.timeout(2000) })).ok) {
				ready = true;
				break;
			}
		} catch {
			// The preview server may still be starting.
		}
		await new Promise((resolve) => setTimeout(resolve, 200));
	}
	assert.ok(ready, 'Local Vite server did not become ready');
	console.log('Checking optical explorer at', base);
	const browser = await chromium.launch({ headless: true });
	try {
		const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
		page.setDefaultTimeout(20000);
		page.setDefaultNavigationTimeout(60000);
		const errors = [];
		let workerStatus;
		page.on('response', (response) => {
			if (response.url().includes('maplibre-gl-worker')) workerStatus = response.status();
		});
		page.on('pageerror', (e) => errors.push(e.message));
		await page.route('https://tiles.openfreemap.org/**', (route) => route.abort());
		await page.goto(base, { waitUntil: 'domcontentloaded' });
		await page.getByText('Loading observation layers...').waitFor({ state: 'hidden' });
		await page.getByRole('button', { name: 'Optical Evidence', exact: true }).click();
		await page.getByText('Loading dated optical image…').waitFor({ state: 'hidden' });
		assert.equal(await page.getByText('Optical image unavailable.', { exact: false }).count(), 0);
		console.log('Optical preview loaded.');
		const panel = page.getByRole('region', { name: 'Explore candidate evidence' });
		await page.getByRole('combobox', { name: 'Candidate to inspect' }).selectOption('41');
		await page.waitForTimeout(800);
		await panel.getByRole('heading', { name: 'Candidate 41 · 900 m²', exact: true }).waitFor();
		assert.match(await panel.innerText(), /9 land → water/);
		const slider = page.getByRole('slider', { name: 'Radar and Optical Comparison Divider' });
		await slider.focus();
		await page.keyboard.press('Home');
		assert.equal(
			await page.getByTestId('comparison-map').evaluate((e) => e.style.clipPath),
			'inset(0px 0px 0px 0%)'
		);
		// Clear the selection, then hit the marker at the centered candidate on the optical side.
		await page.getByRole('combobox', { name: 'Candidate to inspect' }).selectOption('');
		const canvas = page.locator('canvas.maplibregl-canvas').first();
		const box = await canvas.boundingBox();
		await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
		await panel.getByRole('heading', { name: 'Candidate 41 · 900 m²', exact: true }).waitFor();
		console.log('Candidate click on optical half passed.');
		assert.equal(workerStatus, 200, 'Geometry worker must be served by the production build');
		await slider.focus();
		await page.keyboard.press('End');
		assert.equal(
			await page.getByTestId('comparison-map').evaluate((e) => e.style.clipPath),
			'inset(0px 0px 0px 100%)'
		);
		const sceneSelect = page.getByRole('combobox', { name: 'Optical observation', exact: true });
		await sceneSelect.selectOption('S2B_46QHD_20260908_0_L2A');
		await page.getByText('Loading dated optical image…').waitFor({ state: 'hidden' });
		assert.match(await panel.innerText(), /0.78 days before radar/);
		await page
			.getByRole('combobox', { name: 'Radar reference for optical comparison' })
			.selectOption('baseline');
		assert.match(await panel.innerText(), /11.22 days after radar/);
		await sceneSelect.selectOption('S2C_46QHD_20260824_0_L2A');
		await sceneSelect.selectOption('S2C_46QHD_20260913_0_L2A');
		await page.getByText('Loading dated optical image…').waitFor({ state: 'hidden' });
		await page
			.getByRole('combobox', { name: 'Radar reference for optical comparison' })
			.selectOption('repeat');
		await slider.focus();
		await page.keyboard.press('Home');
		for (let n = 0; n < 10; n++) await page.keyboard.press('ArrowRight');
		await page.setViewportSize({ width: 390, height: 844 });
		await page
			.getByRole('button', { name: 'Optical Evidence', exact: true })
			.scrollIntoViewIfNeeded();
		assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
		// A failed optical date must be explicit and must not display the previous date's image.
		await page.route('**/*20260824*_true-color.png', (route) =>
			route.fulfill({ status: 503, body: 'Unavailable' })
		);
		await sceneSelect.selectOption('S2C_46QHD_20260824_0_L2A');
		await page.getByText('Optical image unavailable.', { exact: false }).waitFor();
		await page.getByRole('button', { name: 'Repeat SAR', exact: true }).click();
		assert.equal(
			await page.getByTestId('comparison-map').evaluate((e) => e.style.visibility),
			'hidden'
		);
		await page.getByRole('button', { name: 'Swipe Compare', exact: true }).click();
		await page.getByRole('slider', { name: 'Radar Comparison Divider', exact: true }).waitFor();
		assert.deepEqual(errors, []);
		console.log(
			'PASS: candidate selection/click, dates and gaps, slider endpoints, rapid scene switching, image failure handling, radar recovery and mobile width.'
		);
	} finally {
		await browser.close();
	}
})().catch((e) => {
	console.error(e);
	process.exit(1);
});
