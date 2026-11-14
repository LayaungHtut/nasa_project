import manifest from '../../../data/validation/yangon-track40-frame10/map-evidence.json';
import comparison from '../../../data/validation/yangon-track40-frame10/comparison.json';
import { independentValidation } from './validation';
import type { ChangeEvent } from '$lib/types/api';
import type { OpticalEvidence, OpticalScene, RadarReference } from '$lib/types/evidence';

export function opticalEvidence(event: ChangeEvent): OpticalEvidence | undefined {
	if (
		!independentValidation(event) ||
		manifest.candidate_mask_sha256 !== comparison.candidate_mask_sha256
	)
		return undefined;
	return manifest as unknown as OpticalEvidence;
}

export function timeGap(scene: OpticalScene, reference: RadarReference): string {
	const days = scene[`${reference}_offset_days`];
	return `${Math.abs(days).toFixed(2)} days ${days < 0 ? 'before' : 'after'} radar`;
}
