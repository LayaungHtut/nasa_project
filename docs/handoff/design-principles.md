# Design Principles — for Antigravity

Not a full style guide (that's your call) — just the non-negotiables from the science/architecture side.

1. **Real data first, polish second.** A plain-but-correct map with clearly-labeled real NISAR data beats a beautiful map with placeholder numbers. If something can't be backed by an API field, don't show it.
2. **Attribution is not a footnote.** "NASA/ISRO NISAR mission via ASF DAAC" plus the granule ID and acquisition date must be visible on the same screen as the visualization, not buried in an about page.
3. **Confidence is a first-class UI element, not an afterthought.** Every detected-change claim shows its `confidence` value near the claim, not just in a details modal.
4. **AI content is always labeled.** No exception. See [frontend-contract.md](frontend-contract.md)'s three-tier rule.
5. **Explain the "how," not just the "what."** A panel answering "how did SAR see this?" (radar backscatter, works through cloud/night, etc.) is as important as the "what changed" panel — this is what makes the project feel like a NISAR demo and not a generic change-detection map.
6. **Design for a stage demo on unknown wifi.** Prefer pre-rendered/cached assets over live network calls where possible; degrade gracefully (skeleton states, not spinners-forever) if the API or AI call is slow.
7. **Accessible to non-experts.** Assume the judge/viewer has never heard "SAR," "backscatter," or "interferogram" — every technical term used in the UI needs a one-line plain-language gloss, inline or via a tooltip, not just in a glossary page nobody opens.
