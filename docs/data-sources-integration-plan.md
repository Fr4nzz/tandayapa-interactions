# Data-source integration plan — breaking the hummingbird bias

Based on the data-source inventory (2026-06-09). Goal: add non-hummingbird interaction layers
(bat pollination, bird/bat/mammal seed dispersal, insect–plant, predation, parasitism), each tagged
with an honest provenance/scope flag, merged into the existing edge-list schema.

## Scope flags (extend the current set)
- `Tandayapa core` · `nearby reserve` · `regional NW Ecuador` · `regional Andes (comparative)`
- add **`corridor-core`** = Tandayapa/Bellavista/Mashpi/Las Gralarias/Mindo/Río Guajalito/Maquipucuna
- candidate edges from elsewhere carry `certainty: "regional candidate"` + `needs_field_verification: true`.

## Phase A — open structured datasets (DOIs, CSV) — DO FIRST  ← started
1. **Bat pollination (CORRIDOR-CORE):** Maguiña-Conde & Muchhala 2024, Dryad **10.7291/D1QX26** (CC0).
   `pollenpresence.csv` = nectar bat (*Anoura caudifer/geoffroyi/fistulata*) × cloud-forest flowers
   (*Burmeistera, Centropogon, Marcgravia, Aphelandra, Pitcairnia*). 8 reserves incl. **Bellavista &
   Río Guajalito** → tag those rows `corridor-core`, type `pollinates`. THE key bat deposit.
2. **Bird seed dispersal (regional Andes):** Dehling et al. ANDEAN frugivory, Dryad **10.5061/dryad.wm37pvmn5**
   (CC0). Frugivorous bird × fleshy-fruited plant interaction events. Ecuadorian plots = Podocarpus (S
   Ecuador) → `regional Andes (comparative)`, type `dispersesSeedsOf`. The frugivory analogue to EPHI.
3. **GloBI corridor sweep:** `https://api.globalbioticinteractions.org/interaction.csv?bbox=-78.9,-0.2,-78.5,0.1&includeObservations=true`
   across all interaction types; dedupe against our DB; tag by locality. (Caveat: Muchhala 2024 not yet
   indexed in GloBI — get it from Dryad directly, GitHub issue #1026.)

## Phase B — structured global DBs, filter to the corridor species pool (candidate edges)
4. **MalAvi** (avian haemosporidians): Hosts-and-Sites table → parasite lineage × bird host, filter
   country=Ecuador. `parasiteOf`, scope regional. Complements Abad/Harrigan.
5. **HOSTS (NHM)** caterpillar host-plants: filter to corridor Lepidoptera/plant genera → candidate
   `hasHost` / herbivory edges. Plus Willmott & Freitas 2006 Ithomiini genus×hostplant-family table.
6. **Frugivoria** trait DB (EDI 10.6073/pasta/…): NOT edges — use to define the frugivore/mammal
   candidate species pool + attach traits. Don't assert edges from it.

## Phase C — corridor-local hand/AI extraction (highest relevance, messy formats)
7. **Mashpi phyllostomid seed-dispersal thesis** (UCE DSpace 25000/28699) → corridor-core bat frugivory.
8. **Reptiles of Ecuador / Amphibians & Reptiles of Mindo** (Arteaga) → Mindo-area snake diet =
   corridor predation (`preysOn`). Hand/AI-extract per-species diet sections.
9. **Philornis** botfly records (continental Ecuador) → candidate `parasiteOf` bird hosts.

## Ingestion mechanics
- Each source → an agent that fetches + parses → `.research/extracted/<slug>.json` ({ref, records[]}) in our
  schema (+ `needs_field_verification`, `ref_doi_or_url`). I review, drop out-of-scope/extralimital, merge
  into `src/data/interactions_papers.json` (or a new `interactions_external.json`), wire into the store.
- Honesty: real documented pairs only (no syndrome inference); keep true locality; flag candidate vs verified.
- After merge: re-run the GBIF image + occurrence top-ups (anonymous, fast) for any new taxa.

## Priority order
A1 (bat, corridor-core) → A2 (frugivory anchor) → A3 (GloBI sweep) → B4 MalAvi → B5 HOSTS/Ithomiini →
C7 Mashpi → C8 reptiles. Phase A is the biggest immediate win (two anchor matrices, like EPHI but for
bats & frugivores).
