# GloBI-Powered Features for the Tandayapa Interaction Explorer

Research notes + concrete, implementable feature specs for our **static Vue site**.
All GloBI endpoints below are live, CORS-friendly JSON, **no API key required** — safe to call
straight from the browser, or to pre-bake into static JSON at build time.

- API base: `https://api.globalbioticinteractions.org`
- Browse/UI base: `https://www.globalbioticinteractions.org`
- Result formats: `type=json` (default), `type=json.v2`, `type=csv`, `type=tsv`, `type=dot`

---

## Key data shapes (verified live, 2026-06)

### `/interaction` — the workhorse
Query: `GET /interaction?sourceTaxon=Apis%20mellifera&interactionType=visitsFlowersOf&type=json&fields=...&limit=...&offset=...`

Returns a compact **columns + data** matrix (NOT objects):
```json
{
  "columns": ["source_taxon_name","source_taxon_external_id","interaction_type",
              "target_taxon_name","target_taxon_external_id","study_citation","latitude","longitude"],
  "data": [
    ["Apis mellifera","GBIF:1341976","pollinates","Crotalaria dewildemanniana","no:match",null,null,null]
  ]
}
```
Note `"no:match"` is GloBI's sentinel for an unresolved external id — must be filtered in UI.

Useful params: `sourceTaxon`, `targetTaxon`, `interactionType`, `bbox=minLon,minLat,maxLon,maxLat`,
`lat`/`lng`, `excludeChildTaxa=true`, `accordingTo=<source/study>`, `includeObservations=true`,
`limit` (default 1024), `offset`, `field=`/`fields=`.

### `/interactionTypes` — controlled vocabulary + INVERSE PAIRS (critical)
Returns every interaction term with its `source`/`target` role labels and ontology IRI:
```json
"pollinates":   {"source":"pollinator","target":"plant",     "termIRI":".../RO_0002455"},
"pollinatedBy": {"source":"plant",     "target":"pollinator","termIRI":".../RO_0002456"}
```

**Canonical inverse pairs (use these to FIX directional labels in our DB):**

| Forward (source→target) | Inverse (target→source) | Roles |
|---|---|---|
| `eats` | `eatenBy` | consumer / food |
| `preysOn` | `preyedUponBy` | predator / prey |
| `kills` | `killedBy` | killer / victim |
| `pollinates` | `pollinatedBy` | pollinator / plant |
| `visitsFlowersOf` | `flowersVisitedBy` | visitor / plant |
| `visits` | `visitedBy` | visitor / host |
| `parasiteOf` | `hasParasite` | parasite / host |
| `endoparasiteOf` | `hasEndoparasite` | endoparasite / host |
| `ectoparasiteOf` | `hasEctoparasite` | ectoparasite / host |
| `parasitoidOf` | `hasParasitoid` | parasitoid / host |
| `pathogenOf` | `hasPathogen` | pathogen / host |
| `vectorOf` | `hasVector` | vector / pathogen |
| `dispersalVectorOf` | `hasDispersalVector` | disperser / seed |
| `hostOf` | `hasHost` | host / symbiont |
| `epiphyteOf` | `hasEpiphyte` | epiphyte / host plant |
| `providesNutrientsFor` | `acquiresNutrientsFrom` | host / consumer |
| `ectomycorrhizalHostOf` | `hasEctomycorrhizalHost` | plant root / fungus |
| `arbuscularMycorrhizalHostOf` | `hasArbuscularMycorrhizalHost` | plant root / fungus |
| `createsHabitatFor` | `hasHabitat` | habitat / inhabitant |

Symmetric (self-inverse, no flip needed): `interactsWith`, `symbiontOf`, `mutualistOf`,
`commensalistOf`, `coOccursWith`, `coRoostsWith`, `ecologicallyRelatedTo`, `adjacentTo`.

### `/imagesForName/{name}` — thumbnail + common name + lineage
```json
{"thumbnailURL":"https://commons.wikimedia.org/.../Apis%20mellifera...jpg?width=100",
 "infoURL":"http://www.wikidata.org/entity/Q30034",
 "scientificName":"Apis mellifera","commonName":"Honey Bee",
 "taxonPath":"Animalia | Arthropoda | Insecta | Hymenoptera | Apidae | Apis | Apis mellifera"}
```

### `/findCloseMatchesForTaxon/{name}` — fuzzy/typo-tolerant search
Returns `taxon_name`, `taxon_common_names` (pipe-delimited, multi-language `name @lang`),
`taxon_path`, and `taxon_path_ids` (e.g. `WD:Q30034 | GBIF:... | NCBI:...`). Tolerates misspellings
("Apis melifera" → "Apis mellifera").

### `/findExternalUrlForTaxon/{name}` — resolves to an authoritative provider page
`{"url":"http://www.itis.gov/.../search_value=154396"}` (redirects by name to ITIS/GBIF/EOL etc.)

### Other useful endpoints
- `/taxon/{name}/{interactionType}` and `/taxon/{name}/{interactionType}/{targetTaxon}` — distinct partners, terse.
- `/interactionFields` — machine-readable dictionary of every field (DwC-aligned descriptions).
- `/findExternalUrlForExternalId/{id}` — resolve a `GBIF:123`/`EOL:456` id to a provider URL.
- `/images/{taxonId}` — image(s) by external id.
- `/reports/sources`, `/reports/studies` — dataset/study stats + citations.
- `/shortestPathsBetweenTaxon/{a}/andTaxon/{b}` — interaction-graph path between two taxa.
- `/locations` — distinct georeferenced observation points.
- `/prefixes` — external taxonomy id prefixes (GBIF, EOL, NCBI, ITIS, OTT, WD…).
- `/cypher?query=...` — raw Neo4j Cypher over the interaction graph (advanced; great for build-time joins).

External-id link templates (for resolving `*_external_id` ourselves, no extra fetch):
`GBIF:123` → `https://www.gbif.org/species/123` · `EOL:123` → `https://eol.org/pages/123` ·
`NCBI:123` → `https://www.ncbi.nlm.nih.gov/taxonomy/123` · `WD:Q123` → `https://www.wikidata.org/wiki/Q123` ·
`ITIS:123` → `https://www.itis.gov/.../search_value=123` · `INAT_TAXON:123` → `https://www.inaturalist.org/taxa/123`.

---

## FEATURES

### 1. Canonical interaction-type normalizer + directional-label fixer
**What:** Build-time map of every interaction type ↔ its inverse, plus source/target role labels,
fetched once from `/interactionTypes`. Use it to normalize our DB's directional labels (e.g. rewrite
a row stored as `flowersVisitedBy` into a consistent `visitsFlowersOf` direction, or render the
correct verb depending on which taxon the user is viewing).
**Data:** `GET /interactionTypes` → bake to `src/data/interactionTypes.json`.
**UI:** No new screen. Powers correct verb + arrow direction everywhere (e.g. on a plant page show
"pollinated by → Bombus", on the bee page show "pollinates → that plant" — same edge, flipped term).
A small `inverseOf(type)` and `roleLabels(type)` helper in a Vue composable.

### 2. "View on GloBI" deep links
**What:** Per-taxon and per-interaction outbound links to GloBI's own browse UI for users who want the
full record set.
**Data:** none (URL construction).
**UI:** Button on every taxon card: `https://www.globalbioticinteractions.org/?interactionType=visitsFlowersOf&sourceTaxon=<name>`
and the browse page `…/browse/?sourceTaxon=<name>`. Opens in new tab.

### 3. Taxon external-ID badge row (GBIF / EOL / Wikidata / iNat / NCBI / ITIS)
**What:** For each taxon, show clickable provider badges built from the `*_external_id` already present
in interaction rows, enriched by `taxon_path_ids` from close-match.
**Data:** `*_taxon_external_id` columns we already fetch + `/findCloseMatchesForTaxon/{name}` for the
full id set; resolve via the link templates above (no network needed for known prefixes).
**UI:** A row of small pill links under the taxon name. "no:match" ids hidden.

### 4. Taxon thumbnail + vernacular-name header
**What:** Enrich each taxon header with a Wikimedia thumbnail, the English common name, and a
breadcrumb of its higher taxonomy.
**Data:** `GET /imagesForName/{name}` → `thumbnailURL`, `commonName`, `taxonPath`.
**UI:** Avatar image + "Honey Bee" subtitle + `Hymenoptera › Apidae › Apis` breadcrumb on the detail panel.
Cache results to a static JSON keyed by taxon so the live site makes zero runtime calls for known taxa.

### 5. "Related interactions not yet in our DB" panel
**What:** For the focused taxon, fetch GloBI's interactions and diff against our local DB; surface
partners/edges GloBI knows about that we don't, flagged as "from GloBI, unverified locally."
**Data:** `GET /interaction?sourceTaxon=<name>&type=json&fields=interaction_type,target_taxon_name,target_taxon_external_id,study_citation`
(+ the inverse query with `targetTaxon=<name>`). Diff target names against our DB.
**UI:** Collapsible "More from GloBI (N)" list under the taxon's known interactions, each row tagged with
its interaction verb, an external badge, and a citation tooltip. A "suggest adding" affordance for editors.

### 6. Typo-tolerant taxon search / autocomplete
**What:** Search box that tolerates misspellings and matches common names in many languages, mapping user
input to a canonical scientific name before we query our DB.
**Data:** `GET /findCloseMatchesForTaxon/{query}` → `taxon_name`, `taxon_common_names`, `taxon_path`.
**UI:** Autocomplete dropdown showing scientific name + common name + lineage hint; selecting one routes
to that taxon's page in our app.

### 7. Interaction-type legend with official definitions
**What:** A legend/glossary explaining each interaction verb used in our network, with its ontology
definition and role labels, so non-specialists understand "ectoparasiteOf" vs "parasitoidOf".
**Data:** `/interactionTypes` (roles + `termIRI` → links to the OBO Relations Ontology term page,
`http://purl.obolibrary.org/obo/RO_xxxx`). Optionally `/interactionFields` for field-level help.
**UI:** A filterable legend panel / hover-cards on edge labels; each entry: verb, "source is the
<pollinator>, target is the <plant>", and an "ontology definition ↗" link.

### 8. Citation & provenance display per edge
**What:** Show where each interaction claim comes from — study title, citation, and source dataset —
to make the explorer scientifically credible and attributable.
**Data:** add fields `study_title`, `study_citation`, `study_source_citation`, `study_source_doi`,
`study_url` to `/interaction` queries; `/reports/studies` for dataset-level metadata.
**UI:** A "ℹ source" popover on each edge/row showing the citation, a DOI link, and "data via GloBI"
attribution. Footer credit line for GloBI overall.

### 9. JSON/CSV export in GloBI-compatible columns
**What:** Let users export the currently viewed interactions (ours + GloBI-enriched) as CSV/JSON using
GloBI's exact column names, so the file round-trips back into GloBI tooling / rglobi.
**Data:** mirror GloBI columns: `source_taxon_name, source_taxon_external_id, interaction_type,
target_taxon_name, target_taxon_external_id, latitude, longitude, study_citation`. Optionally proxy a
live `type=csv` GloBI export.
**UI:** "Export ▾" button → CSV / JSON; client-side Blob download, no backend.

### 10. Geographic / map filtering of interactions
**What:** Filter interactions to the Tandayapa region (or any bbox) and plot georeferenced records.
**Data:** `/interaction?...&bbox=minLon,minLat,maxLon,maxLat` with `fields=...,latitude,longitude,locality,event_date`;
`/locations` for all observation points.
**UI:** A small Leaflet map on the explorer; bbox prefilled to the Tandayapa reserve. Points clickable
to the underlying interaction + citation. Region filter toggle on the network view.

### 11. "Connection between two species" path finder
**What:** Given any two taxa, show the shortest chain of interactions linking them (e.g. bird → eats →
insect → pollinates → plant) — a compelling "food-web detective" feature.
**Data:** `GET /shortestPathsBetweenTaxon/{a}/andTaxon/{b}` (returns ordered taxon/interaction steps).
**UI:** Two taxon pickers + a rendered chain of nodes/edges using our existing graph component, each hop
labeled with the verb (normalized via feature #1) and citation popover (#8).

### 12. Build-time enrichment pipeline (Cypher / bulk fetch)
**What:** A Node build script that, for every taxon in our DB, pre-fetches GloBI interactions, images,
external ids, and citations into static JSON — keeping the deployed site fully static and fast with no
runtime API dependency or rate-limit risk.
**Data:** loop `/interaction`, `/imagesForName`, `/findCloseMatchesForTaxon` per taxon; advanced joins via
`/cypher?query=...`. Output to `src/data/globi/*.json`.
**UI:** Invisible — but enables features #3, #4, #5, #7, #8 to render instantly offline. Add a "last synced
<date>" note and a CI step to refresh periodically.

---

## Implementation notes for a static Vue site
- All endpoints are public + CORS-enabled → callable from the browser; but **prefer build-time baking**
  (feature #12) for known taxa to keep the site static, fast, and resilient.
- Always request `type=json` with an explicit `fields=` list to keep payloads small and stable.
- Filter `"no:match"` external ids and `null` cells before rendering.
- The columns+data matrix is not objects — write one small `rowsToObjects(resp)` helper and reuse it.
- Respect provenance: surface citations (#8) and a visible "Interaction data via GloBI
  (globalbioticinteractions.org)" credit.
