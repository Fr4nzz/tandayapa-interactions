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

## Status — Phase 0 (scaffold)

A working interactive graph rendering ~23 **real** sample interactions extracted from open-access
sources (Maquipucuna/EPHI, Muchhala 2002/2006, Mahoney 2018, Guevara 2017, Abad 2021). Hover a node
to highlight its neighbors; click for a detail panel; filter by interaction type.

This is **sample data only**, not the full database. See `PLAN-tandayapa.md` (in the agent workspace)
for the full roadmap: data model, the Duchenne/EPHI anchor dataset (~1,690 interactions), the GBIF
image pipeline, the open-access paper-fetch tooling, and deployment.

## Data model

One row = one interaction edge: `taxon_1/2`, `interaction_type` (visitsFlowersOf | pollinates |
dispersesSeedsOf | eatsFruitPulpOf | parasiteOf), `evidence_type`, `locality_original` +
`locality_scope` (Tandayapa core / nearby reserve / regional), `elevation`, `certainty_flag`, source.

**Honesty rule:** interactions keep their true locality; nearby-reserve records are flagged by scope,
never relabeled "Tandayapa." No interactions are fabricated from syndrome inference.

## License

MIT (code). Interaction records retain their original source citations; GBIF images retain
per-image CC licenses + attribution.
