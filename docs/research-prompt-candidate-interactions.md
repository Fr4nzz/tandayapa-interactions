# Research prompt — Candidate ecological interactions for Tandayapa (all taxa, all interaction types)

**Paste everything below the line into a capable deep-research agent (web + literature access).**
The goal is to break the current hummingbird–plant bias of our database by compiling **candidate
interactions for the full Tandayapa community** — birds, mammals, amphibians, reptiles, insects,
and plants — and flagging which still need **field verification at Tandayapa itself**.

---

## ROLE & GOAL

You are an ecological-interactions research assistant. Build a **GloBI-compatible list of candidate
ecological interactions** for the **Tandayapa valley** (NW Pichincha, Ecuador; cloud forest of the
Chocó-Andino / Mindo–Tandayapa corridor, ~1,400–2,300 m). The output feeds an interactive web
database, so it must be a structured edge list with explicit provenance and a verification status.

The database is currently dominated by hummingbird–plant pollination. **Your job is to broaden it**
to the rest of the community and the rest of the interaction types, *without fabricating records*.

## SCOPE & STRATEGY

1. **Start from the species known to occur at (or adjacent to) Tandayapa.** Build the taxon list from:
   - The **Tandayapa Bird Lodge / Bellavista** bird checklists and **eBird** hotspots for Tandayapa,
     Bellavista, Mindo, Paz de las Aves, Refugio Paz.
   - **GBIF** occurrences within a bounding box around Tandayapa (~ lat −0.05 to 0.05, lon −78.75 to −78.65;
     widen to the Mindo–Tandayapa corridor if sparse) — birds, mammals (esp. bats, rodents, marsupials),
     amphibians, reptiles, insects (Lepidoptera incl. **Ithomiini**, bees/Euglossini, beetles), and plants.
   - Published **inventories / theses** for the corridor (PUCE, USFQ, Univ. del Azuay, EPN repositories).
2. **For each focal taxon, find documented interactions** of ALL these types (use GloBI's controlled
   vocabulary; include the reciprocal direction):
   - pollination: `visitsFlowersOf` / `pollinates` (and `pollinatedBy`) — bats, insects, birds (not just hummingbirds), rodents, flowerpiercers
   - frugivory & seed dispersal: `eats`, `eatsFruitPulpOf`, `dispersesSeedsOf` / `hasDispersalVector` — tanagers, toucans, guans, cotingas, bats, rodents, monkeys
   - herbivory: `eats` (folivory), host-plant use by caterpillars/insects (`hasHost` / `parasiteOf` for galls)
   - predation: `preysOn` / `preyedUponBy` (raptors→birds/mammals, snakes→frogs, etc.)
   - parasitism & disease: `parasiteOf` / `hasParasite` (haemosporidians, botflies *Philornis*, ticks, mites, helminths)
   - mutualism/other: `nectarRobs`, ant–plant, mycorrhizae, epiphyte–host (`epiphyteOf`)
3. **Two evidence tiers — keep them strictly separate:**
   - **Verified-at-corridor**: the interaction is documented at Tandayapa or a named corridor reserve
     (Bellavista, Mashpi, Maquipucuna, Las Gralarias, Sachatamia, Milpe, Verdecocha, Yanacocha, Otonga,
     Río Guajalito, Pahuma, Bilsa, FCAT-Chocó).
   - **Regional candidate (NEEDS FIELD VERIFICATION)**: both taxa occur at/near Tandayapa AND the
     interaction is documented for that species pair (or genus pair) *somewhere else*, so it is
     *expected* at Tandayapa but not yet observed there. Mark these clearly.
4. **Data sources to query** (all CORS-free / API or literature):
   - **GloBI**: `https://api.globalbioticinteractions.org/interaction?sourceTaxon=<name>&type=json&fields=source_taxon_name,interaction_type,target_taxon_name,target_taxon_external_id,study_citation,latitude,longitude`
     (and the inverse with `targetTaxon=`); `bbox=−78.9,−0.2,−78.5,0.1` to find georeferenced records near Tandayapa.
   - **GBIF** occurrence/search (presence at Tandayapa), **iNaturalist** observation fields/annotations
     ("interaction → visited flower of / eaten by / host"), **Macaulay/eBird** behavior notes.
   - **Primary literature & theses** (Web of Science / Scholar / repositories) for interaction matrices
     and natural-history notes for the corridor and NW Ecuador / Chocó.

## HONESTY RULES (critical)

- Never relabel a non-Tandayapa record as "Tandayapa." Keep the **true locality** and set the scope.
- Never invent a species pair from pollination/dispersal **syndrome inference alone**. A candidate edge
  requires an actual documented interaction for that (species or genus) pair somewhere.
- Distinguish **species-level** vs **genus/family-level** records (set the rank fields).
- Every edge needs a real **citation** (DOI/URL/study) — no edge without a source.
- Prefer GloBI/GBIF external IDs where available so taxa can be resolved later.

## OUTPUT FORMAT

Return a single JSON object: `{ "records": [ ... ] }`, one object per interaction edge, using EXACTLY
these fields (this matches the app's schema so it can be ingested directly):

```json
{
  "source": "Scientific name",
  "sourceGroup": "hummingbird|bird|bat|mammal|insect|plant|parasite|amphibian|reptile",
  "sourceRank": "species|genus|family",
  "target": "Scientific name",
  "targetGroup": "…",
  "targetRank": "species|genus|family",
  "type": "visitsFlowersOf|pollinates|dispersesSeedsOf|eatsFruitPulpOf|eats|preysOn|parasiteOf|nectarRobs|hasHost|epiphyteOf",
  "evidence": "observation|camera trap|pollen load|fecal/gut content|PCR|literature record",
  "locality_original": "exact locality stated in the source",
  "scope": "Tandayapa core|nearby reserve|regional NW Ecuador|regional Andes (comparative)",
  "elevation_m": 0,
  "certainty": "verified|regional candidate",
  "needs_field_verification": true,
  "ref": "Author et al. year",
  "ref_doi_or_url": "https://doi.org/…",
  "notes": "short verbatim justification (why it is expected at Tandayapa)"
}
```

Also return, at the end:
- A short **coverage summary**: # edges per interaction type and per taxon group (to show the
  hummingbird bias is reduced), and # verified vs # regional-candidate.
- A **gap list**: focal Tandayapa taxa for which NO interactions were found (priority targets for fieldwork).
- A **priority PDF/dataset retrieval list** for any paywalled interaction matrices you could not access.

## DELIVERABLE PRIORITIES

Lead with the **non-hummingbird** layers that are currently missing: bird **frugivory/seed dispersal**
(tanagers, toucans, guans, cotingas), **bat** pollination & seed dispersal, **mammal** (rodent, monkey)
frugivory, **insect–plant** (Ithomiini host plants, euglossine–orchid, herbivory), **predation**, and
**parasitism** (Philornis, ticks/mites, helminths, haemosporidians). Aim for breadth across the community,
each edge tagged verified vs. field-verification-needed.
