# EPHI (Duchenne et al. 2022) Dryad dataset — ingest notes

Dataset: "Ecuadorian Plant-Hummingbird interactions over an elevation gradient in the
Andes, sampled with camera traps in 11 localities."
DOI: 10.5061/dryad.vhhmgqnvw  ·  Ref: Duchenne et al. 2022 (EPHI, Dryad)

## Download (gotcha)

The Dryad v2 API download endpoints now require a bearer token:
- `GET /api/v2/datasets/.../download` → 401 `{"error":"Unauthorized, must have current bearer token"}`
- `GET /api/v2/files/<id>/download` → 401
- public `downloads/file_stream/<id>` → 403
- anonymous OAuth client_credentials token → not issued
So `scripts/paper_tools/oa_fetch.py --download` resolves the correct URL but the fetch
returns 401 (the script's plain urllib GET can't authenticate).

Workaround used: Dryad mirrors this dataset to **Zenodo record 7056230** with the
*identical* file. Verified by SHA-256:
`a0f7705e21dca0b3ec8b107c20ffb42206b0efaeabaa82c3600b14605c99b6a3`
(matches the `digest` reported by `GET /api/v2/files/1757175`). Download (no auth):
- `https://zenodo.org/api/records/7056230/files/data_for_modelo2.txt/content`
- `https://zenodo.org/api/records/7056230/files/README.txt/content`

Files saved to `papers/data_for_modelo2.txt` and `papers/README.txt`.

## Real file structure (verified, not assumed)

Two files in the deposit:
- `data_for_modelo2.txt` (1,427,515 bytes) — the data
- `README.txt` (577 bytes) — column descriptions

`data_for_modelo2.txt` is **CSV, comma-delimited, UTF-8**, with a header row.
NOTE: the assumed schema in the task (site/plant/hummingbird/month/frequency,
tab/txt) was close in spirit but the real header order/names differ — use the real ones:

```
plant,hummingbird,site,y,m,date,latitude,longitude,elev,mnumb,nsampl,value
```

Column meanings (from README.txt):
| column      | meaning |
|-------------|---------|
| plant       | scientific name of the plant |
| hummingbird | scientific name of the hummingbird |
| site        | sampled site (one of 11) |
| y           | year |
| m           | month (3-letter) |
| date        | observation date (YYYY-MM-DD) |
| latitude    | site latitude |
| longitude   | site longitude |
| elev        | site elevation (m); constant per site |
| mnumb       | month as a number |
| nsampl      | number of months sampled at that site that year |
| value       | number of recorded interactions for that row |

Sample rows:
```
Abutilon pictum,Phaethornis yaruqui,Maquipucuna,2020,Oct,2020-10-28,0.106916,-78.629222,1603.598389,10,11,5
Abutilon sp,Coeligena wilsoni,SantaLuciaLower,2017,Aug,2017-08-15,0.116924,-78.5979585,1945.673584,8,12,13
```

Each row = one camera-trap observation on a date. Granularity is per
(plant, hummingbird, site, date); many rows collapse to the same interaction edge.

## Counts (from the actual file)

- 12,336 data rows
- 11 sites (raw tokens): Alaspungo, LasGralarias, Maquipucuna, MashpiLaguna,
  Mashpi_Capuchin, Sachatamia, SantaLuciaLower, SantaLuciaUpper, UnPocoChoco,
  Verdecocha, Yanacocha
- 42 hummingbird species
- 280 plant names (incl. 17 genus/morphospecies-level like "Abutilon sp", "Sp 1.")
- **1,173** unique (hummingbird, plant) pairs (site-agnostic)
- **1,690** unique (hummingbird, plant, site) triples — the dataset's headline number
- Elevation is constant per site (single value each), so it is carried as `elevation_m`.

## Edge rule chosen

One edge per unique **(hummingbird, plant, site)** triple (site-level), matching the
~1,690 headline and the existing `interactions.json` convention (which is per-locality).

### Skipped records (NOT fabricated, NOT included)
4 rows have a **blank `plant`** field (hummingbird + site present, no plant identity):
- Aglaiocercus coelestis / SantaLuciaLower / 2018-09-15
- Coeligena wilsoni / SantaLuciaLower / 2017-04-15
- Ocreatus underwoodii / SantaLuciaLower / 2018-09-15
- Urosticte benjamini / SantaLuciaLower / 2017-04-15

These carry no plant target → cannot form a valid edge, so they are skipped. That is
why the emitted edge count is **1,686**, not 1,690 (1,690 − 4 blank-plant triples = 1,686).
No hummingbird names were blank.

## Output

`src/data/interactions_ephi.json` → `{ "_meta": {...}, "records": [...] }`
1,686 edges, each:
`{source: hummingbird, sourceGroup:'hummingbird', target: plant, targetGroup:'plant',
type:'visitsFlowersOf', evidence:'camera trap (EPHI)', locality:<cleaned site>,
scope:'nearby reserve', elevation_m:<int>, ref:'Duchenne et al. 2022 (EPHI, Dryad)',
certainty:'verified'}`

Site tokens were cleaned for display (e.g. SantaLuciaLower → "Santa Lucia (Lower)",
UnPocoChoco → "Un Poco del Chocó", Mashpi_Capuchin → "Mashpi Capuchin"); no sites merged.
Parser: `scripts/ingest_ephi.py` (re-run: `python3 scripts/ingest_ephi.py`).
