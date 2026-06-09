# Build scripts

Build-time Python helpers. They pre-bake static JSON the frontend reads at runtime — the
deployed site makes **no live API calls**.

## `build_gbif_images.py`

For every taxon in `src/data/interactions.json`, resolves a GBIF `usageKey` and fetches one
representative, license-clean image via the GBIF occurrence API, proxied through wsrv.nl for a
resized WebP. Writes:

- `public/data/species_images.json` — `taxon -> { image_url, license, creator, attribution, source_url, … }`
- `public/data/gbif_attribution.json` — dataset-level attribution note.

```bash
python3 scripts/build_gbif_images.py
```

Stdlib only (urllib). Idempotent and re-runnable. Taxa with no image are omitted; the UI handles
missing images gracefully.

## `paper_tools/oa_fetch.py`

**Open-access only** DOI → PDF/dataset resolver (a clean-room port of the user's `paper-search`
tooling, deliberately **without** any Sci-Hub / paywall-bypass path). Source order:
Unpaywall → OpenAlex → Europe PMC → Crossref → Dryad/Zenodo.

```bash
# print the OA PDF URL
python3 scripts/paper_tools/oa_fetch.py 10.1098/rspb.2022.0064
# -> {"source":"europepmc","oa_pdf_url":"https://europepmc.org/articles/PMC9470273?pdf=render"}

# resolve + download the Duchenne/EPHI interactions dataset
python3 scripts/paper_tools/oa_fetch.py 10.5061/dryad.vhhmgqnvw -o papers/ --download
```

Reads a contact email from `UNPAYWALL_EMAIL` or `GBIF_EMAIL` (env or `.env`), required by the
Unpaywall/OpenAlex polite pool. Use this to pull the open papers/datasets that enrich the
interaction database (see `PLAN-tandayapa.md`, retrieval list).
