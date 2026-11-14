# Limitations & Responsible-Use Statement

This document exists so nobody on the team — or in the audience — walks away with a claim we can't defend. Read this before writing any UI copy, slide, or AI prompt.

## What we can honestly claim

- "NISAR (NASA-ISRO SAR mission) L-band radar acquired real backscatter measurements over [AOI] on [date A] and [date B]."
- "We processed these two acquisitions with a documented, published-style method (speckle filtering + backscatter thresholding) to identify areas where the radar signal changed in a way consistent with new standing water."
- "This method has known false-positive and false-negative modes, described below, and a stated confidence figure — not a certainty figure."
- "SAR can observe the surface through cloud cover and at night, which is why it's valuable for flood monitoring during monsoon storms when optical satellites are often blind."

## What we must NOT claim

- "NASA detected this flood" — NASA released the raw calibrated data; **we** ran the detection. Always attribute detection to our pipeline, attribute the _data_ to NASA/ISRO/ASF.
- "AI detected this flood/earthquake/disturbance" — the AI layer only narrates numbers our deterministic pipeline already produced (see [ai-strategy.md](../ai/ai-strategy.md)). It never independently classifies imagery.
- Any specific number of "people affected," "houses destroyed," or economic loss unless sourced from a cited external dataset — we only measure _area_, not human impact, unless we explicitly bring in a population layer and cite it.
- That our threshold generalizes globally. It is tuned to specific AOIs/scenes we curated; say so.
- That this is validated/operational-grade flood mapping. It's a hackathon demonstration of a real, standard remote-sensing technique on real data — not a replacement for agency flood products (e.g., NASA's own MODIS/VIIRS or Copernicus EMS flood mapping, which use validated, calibrated algorithms).

## Known failure modes (surface these in the UI "How we know" panel)

1. **Flooded vegetation is often invisible to this method** — double-bounce scattering under flooded forest/tall crops can increase, not decrease, backscatter, defeating a simple threshold.
2. **Non-water smooth surfaces can look like water** — dry lakebeds, some paved/bare soil surfaces, and radar shadow can produce false positives.
3. **Speckle noise** is inherent to all SAR imagery; we filter it, but small/noisy "changes" are discarded by a minimum-cluster-size rule, meaning small real changes may also be missed.
4. **Acquisition timing ≠ event timing.** Our "before/after" dates are whatever NISAR happened to image; the true flood peak may have occurred hours or days off from our "post" acquisition.
5. **Data maturity**: as of the 2026 Provisional release, NISAR products may later be superseded by a Q4 2026 validated reprocessing campaign with refined calibration — our specific numbers could shift slightly if re-run on reprocessed data.
6. If we ship the deformation (GUNW) stretch feature: line-of-sight-only displacement, atmospheric-phase artifacts not independently corrected, low-coherence pixels masked out (not "zero motion," but "no reliable measurement").

## Attribution requirements

Every visualized dataset in the product must show, at minimum:

- Data source: "NASA/ISRO NISAR mission, via ASF DAAC"
- Product identifier (e.g., GCOV granule ID)
- Acquisition date(s)
- Our processing method name (e.g., "backscatter change detection, threshold method")
- A clear visual/label distinction between: **NASA observation** (raw backscatter) vs **our processing** (change mask, stats) vs **AI interpretation** (narrated explanation)

This maps directly to the three-tier distinction required in the project brief (Phase 11) and must be enforced in both the API response shape ([api-contract.md](../api/api-contract.md)) and the frontend ([frontend-contract.md](../handoff/frontend-contract.md)).
