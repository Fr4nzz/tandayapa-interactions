# Tandayapa Ecological Interactions

Interactive network of ecological interactions in **Tandayapa / NW Ecuador (Chocó Andino,
Mindo–Tandayapa corridor)** — a GloBI-compatible, explorable map of who pollinates, disperses,
eats, and parasitizes whom.

🔗 Live (once deployed): https://fr4nzz.github.io/tandayapa-interactions/

## Stack

Vue 3 · Vite · Tailwind v4 · reka-ui · Pinia · **Cytoscape.js + fcose** (graph engine) · pnpm.

## Develop

```bash
pnpm install
pnpm dev        # http://localhost:5173
pnpm build      # -> dist/
pnpm preview
```

## Status

Interactive network of **59 real interactions** across 59 taxa, hand-extracted from open-access
sources (Maquipucuna/EPHI, Muchhala 2002/2006/2009, Mahoney 2018, Guevara 2017, Abad 2021,
Dellinger 2014). Features:

- Dark-canvas force graph (Cytoscape.js + fcose), node size by interaction degree.
- **Hover** → highlight a taxon's neighborhood, dim the rest. **Click** → detail panel with a
  **GBIF photo** (97% of taxa), partners grouped by interaction type, locality, scope & source.
- **Filter** by interaction type, taxon group, and locality scope (all with live counts).
- **Search** taxa, switch layouts (force / concentric / circle / tree), fit, and **export PNG**.
- GBIF images are pre-baked at build time into static JSON (`scripts/build_gbif_images.py`) —
  no live API calls in the browser.

This is still a **curated sample**, not the full database — the Duchenne/EPHI Dryad anchor
(~1,690 plant–hummingbird interactions) is pending ingestion (see `scripts/paper_tools/oa_fetch.py`
and `PLAN-tandayapa.md`).

## Data model

One row = one interaction edge: `taxon_1/2`, `interaction_type` (visitsFlowersOf | pollinates |
dispersesSeedsOf | eatsFruitPulpOf | parasiteOf), `evidence_type`, `locality_original` +
`locality_scope` (Tandayapa core / nearby reserve / regional), `elevation`, `certainty_flag`, source.

**Honesty rule:** interactions keep their true locality; nearby-reserve records are flagged by scope,
never relabeled "Tandayapa." No interactions are fabricated from syndrome inference.

## License

MIT (code). Interaction records retain their original source citations; GBIF images retain
per-image CC licenses + attribution.
