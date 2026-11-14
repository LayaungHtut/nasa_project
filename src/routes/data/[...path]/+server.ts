import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import fs from 'node:fs';
import path from 'node:path';

/**
 * Serves processed data files (PNGs, GeoJSONs, JSONs) from data/
 * Mirrored exactly from FastAPI's app.mount("/data", StaticFiles(directory="data"))
 */
export const GET: RequestHandler = async ({ params }) => {
	const filePath = params.path;
	if (!filePath) throw error(404, 'File path required');

	// Prevent directory traversal
	const safePath = path.normalize(filePath).replace(/^(\.\.[/\\])+/, '');
	const fullPath = path.resolve(process.cwd(), 'data', safePath);

	if (!fullPath.startsWith(path.resolve(process.cwd(), 'data'))) {
		throw error(403, 'Access denied');
	}

	if (!fs.existsSync(fullPath) || fs.statSync(fullPath).isDirectory()) {
		throw error(404, 'File not found');
	}

	const ext = path.extname(fullPath).toLowerCase();
	let contentType = 'application/octet-stream';
	if (ext === '.json' || ext === '.geojson') contentType = 'application/json';
	else if (ext === '.png') contentType = 'image/png';
	else if (ext === '.jpg' || ext === '.jpeg') contentType = 'image/jpeg';
	else if (ext === '.tif' || ext === '.tiff') contentType = 'image/tiff';

	const fileBuffer = fs.readFileSync(fullPath);

	return new Response(fileBuffer, {
		headers: {
			'Content-Type': contentType,
			'Cache-Control': 'public, max-age=3600',
			'Access-Control-Allow-Origin': '*'
		}
	});
};

