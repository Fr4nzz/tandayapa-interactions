# Ithomiini Maps → Porting Spec (Theme + Map + GBIF)

Source app: `/home/franz/Documents/CodeProjs/ithomiini_maps` (Vue 3.5 + Vite 7 + Pinia 3 + Tailwind v4 + MapLibre GL 5.13).
Target: reuse the theme system + MapLibre map system + GBIF occurrence fetch in another Vue3+Vite+Cytoscape app.

Key stack pins (from `package.json`):
- `maplibre-gl ^5.13.0`, `pinia ^3.0.4`, `vue ^3.5.24`, `tailwindcss ^4.1.18` (`@tailwindcss/vite`), `lucide-vue-next`, `@turf/turf ^7.3.4` (only needed for range/hull/hexbin viz — optional).

---

## A. THEME SYSTEM

### A.1 How it is driven

Two attributes on `<html>` (`document.documentElement`) select a CSS block; CSS does the rest. Set by the Pinia store `applyTheme()` (`src/stores/theme.js:56-89`):

```js
root.setAttribute('data-theme', currentTheme.value)  // emerald|ocean|forest|sunset|lavender
root.setAttribute('data-mode',  currentMode.value)   // light|dark
root.classList.add(`theme-${currentTheme.value}`)    // also mirrored as classes
root.classList.add(currentMode.value)                // 'dark' | 'light'
```

CSS selectors that consume them (`src/index.css`): e.g. `[data-theme="emerald"][data-mode="light"] { … }` and a dark default fallback `[data-theme="emerald"]:not([data-mode]) { … }`. `:root` also carries the emerald-light values so there is always a default (`src/index.css:38`).

Store API (`src/stores/theme.js:40-134`): `currentTheme`, `currentMode`, `isDarkMode` (computed), `setTheme(name)`, `setMode('light'|'dark')`, `toggleMode()`, `applyTheme()`. Persistence is opt-in, gated behind `localStorage['app-persist-enabled']` (`theme.js:7-38`); keys `app-theme` / `app-mode`. Defaults: `DEFAULT_THEME='emerald'`, `DEFAULT_MODE='dark'` (`src/themes/presets.js:47-48`).

Preset metadata (NOT the colors — just swatch/preview data) lives in `src/themes/presets.js:4-44`: each theme has `name`, `description`, `accentColor`, `previewBgDark`, `previewBgLight`. Helpers: `getTheme(name)`, `getThemeOptions()` (`presets.js:51-65`).

Two parallel variable systems coexist in each block:
1. **shadcn HSL triplets** (space-separated, no `hsl()` wrapper) registered for Tailwind v4 via `@theme inline { --color-background: hsl(var(--background)); … }` (`src/index.css:9-31`). Consumed as Tailwind utilities `bg-background`, `text-foreground`, etc.
2. **Legacy hex/rgba vars** (`--color-bg-primary`, `--color-accent`, …) used directly by hand-written component CSS (e.g. `SidebarMapSettings.vue` uses `var(--color-accent, #4ade80)`).

JS reads the live accent at runtime via `getComputedStyle(document.documentElement).getPropertyValue('--color-accent')` — `src/utils/mapHelpers.js:24-27`. The map watches theme/mode changes and recolors overlays (`MapEngine.vue:220-230`).

### A.2 Ready-to-adapt CSS variable block

Drop this into your global CSS. The `@theme inline` block requires Tailwind v4; if you are NOT on Tailwind v4, delete that block and keep the `[data-theme]…` blocks (the legacy `--color-*` hex vars work with plain CSS). Each theme = one light + one dark block.

```css
@import "tailwindcss"; /* Tailwind v4 only */

/* Register shadcn HSL vars as Tailwind colors (Tailwind v4 only) */
@theme inline {
  --color-background: hsl(var(--background));
  --color-foreground: hsl(var(--foreground));
  --color-card: hsl(var(--card));
  --color-card-foreground: hsl(var(--card-foreground));
  --color-popover: hsl(var(--popover));
  --color-popover-foreground: hsl(var(--popover-foreground));
  --color-primary: hsl(var(--primary));
  --color-primary-foreground: hsl(var(--primary-foreground));
  --color-secondary: hsl(var(--secondary));
  --color-secondary-foreground: hsl(var(--secondary-foreground));
  --color-muted: hsl(var(--muted));
  --color-muted-foreground: hsl(var(--muted-foreground));
  --color-accent: hsl(var(--accent));
  --color-accent-foreground: hsl(var(--accent-foreground));
  --color-destructive: hsl(var(--destructive));
  --color-destructive-foreground: hsl(var(--destructive-foreground));
  --color-border: hsl(var(--border));
  --color-input: hsl(var(--input));
  --color-ring: hsl(var(--ring));
  --color-sidebar: hsl(var(--sidebar));
  --color-sidebar-foreground: hsl(var(--sidebar-foreground));
}
```

**Per-mode / per-preset variable values.** Each block defines the SAME 21 shadcn HSL vars (`--background --foreground --card --card-foreground --popover --popover-foreground --primary --primary-foreground --secondary --secondary-foreground --muted --muted-foreground --accent --accent-foreground --destructive --destructive-foreground --border --input --ring --sidebar --sidebar-foreground`, plus `--radius: 0.5rem` once on `:root`) AND the SAME 18 legacy vars (`--color-bg-primary --color-bg-secondary --color-bg-tertiary --color-bg-overlay --color-border --color-border-light --color-text-primary --color-text-secondary --color-text-muted --color-accent --color-accent-hover --color-accent-subtle --color-danger --color-warning --color-info --color-shadow-color --color-shadow-color-light`).

The full authoritative values are in `src/index.css:38-490`. The distinguishing tokens per preset (copy the whole block from index.css; quick reference below):

| Preset | Mode | `--primary` (HSL) | `--color-accent` | `--color-bg-primary` | `--background` (HSL) |
|---|---|---|---|---|---|
| emerald | light | `142 71% 35%` | `#16a34a` | `#f8f9fa` | `0 0% 98%` |
| emerald | dark  | `142 71% 45%` | `#4ade80` | `#1a1a2e` | `240 10% 9%` |
| ocean   | light | `190 90% 40%` | `#0891b2` | `#f0f7fa` | `200 30% 97%` |
| ocean   | dark  | `190 90% 50%` | `#00d4ff` | `#0d1b2a` | `210 50% 10%` |
| forest  | light | `85 60% 40%`  | `#4d7c0f` | `#f5f9f0` | `80 30% 97%` |
| forest  | dark  | `85 60% 50%`  | `#8bc34a` | `#1a2e1a` | `150 30% 8%` |
| sunset  | light | `25 95% 50%`  | `#ea580c` | `#fdf8f3` | `30 40% 97%` |
| sunset  | dark  | `25 95% 55%`  | `#ff7f50` | `#2e1a1a` | `20 30% 10%` |
| lavender| light | `270 60% 55%` | `#8b5cf6` | `#faf8fc` | `270 30% 98%` |
| lavender| dark  | `270 60% 60%` | `#a78bfa` | `#1f1a2e` | `270 25% 10%` |

Selector pattern to reproduce (light is plain, dark doubles as the no-`data-mode` default):
```css
:root,
[data-theme="emerald"][data-mode="light"] { /* …light vars… */ }

[data-theme="emerald"][data-mode="dark"],
[data-theme="emerald"]:not([data-mode]) { /* …dark vars… */ }
/* repeat for ocean / forest / sunset / lavender */
```
Base styles (`src/index.css:496-505`): `* { @apply border-border } body { @apply bg-background text-foreground }`.

**Recommendation:** copy `src/index.css:1-505` verbatim, copy `src/themes/presets.js` and `src/stores/theme.js` verbatim. They have zero map/data dependencies (theme.js only imports `presets` + a `log` util you can stub to `console`). The `ThemeSelector.vue` component (`src/components/ThemeSelector.vue`) is a self-contained pill toggle + dropdown + swatches; it depends only on shadcn-vue `Select/Label/Separator` + lucide icons — port it only if you already have shadcn-vue, otherwise rebuild from its 3 store calls (`setTheme`, `toggleMode`, `currentTheme/isDarkMode`).

---

## B. MAP SYSTEM (MapLibre GL)

### B.1 Library + init

`maplibre-gl ^5.13.0`. CSS imported in component: `import 'maplibre-gl/dist/maplibre-gl.css'` (`MapEngine.vue:4`).

Init (`MapEngine.vue:394-413`):
```js
map.value = new maplibregl.Map({
  container: mapContainer.value,
  style: styleConfig.style,           // string URL or inline style object
  center: [-60, -5], zoom: 4,
  attributionControl: false, maxZoom: 18, minZoom: 2,
  canvasContextAttributes: { preserveDrawingBuffer: true }, // needed for PNG export
})
map.addControl(new maplibregl.NavigationControl(), 'top-right')
map.addControl(new maplibregl.ScaleControl({ maxWidth: 200, unit: 'metric' }), 'bottom-right')
map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-left')
map.addControl(new maplibregl.FullscreenControl(), 'top-right')
```
A `ResizeObserver` on the container calls `map.resize()` (`MapEngine.vue:362-372`) — essential when the map shares layout with a Cytoscape pane.

### B.2 Basemap option list (style URLs)

Source of truth: `src/utils/mapStyles.js:2-117`. Each entry: `{ name, theme:'day'|'night', provider?, style, pair? }`. `pair` is the opposite-mode counterpart used for auto-switch.

**Day (light) basemaps:**
| key | name | style | pair |
|---|---|---|---|
| `light` | Light | `https://basemaps.cartocdn.com/gl/positron-gl-style/style.json` | `dark` |
| `stadia-smooth` | Smooth | `https://tiles.stadiamaps.com/styles/alidade_smooth.json` | `stadia-dark` |
| `stadia-toner-lite` | Toner Lite | `https://tiles.stadiamaps.com/styles/stamen_toner_lite.json` | `stadia-toner` |
| `stadia-terrain` | Stamen Terrain | `https://tiles.stadiamaps.com/styles/stamen_terrain.json` | — |
| `terrain` | Terrain | inline raster → `https://tile.opentopomap.org/{z}/{x}/{y}.png` (tileSize 256, maxzoom 17) | — |
| `streets` | Streets | inline raster → `https://tile.openstreetmap.org/{z}/{x}/{y}.png` (maxzoom 19) | — |
| `satellite` | Satellite | inline raster → `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}` (maxzoom 19) | — |

**Night (dark) basemaps:**
| key | name | style | pair |
|---|---|---|---|
| `dark` | Dark | `https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json` | `light` |
| `stadia-dark` | Smooth Dark | `https://tiles.stadiamaps.com/styles/alidade_smooth_dark.json` | `stadia-smooth` |
| `stadia-toner` | Toner | `https://tiles.stadiamaps.com/styles/stamen_toner.json` | `stadia-toner-lite` |

Notes: CARTO Positron/Dark-Matter and OSM/OpenTopoMap/Esri raster need NO API key. **Stadia styles require a Stadia API key / allowed-domain** in production. Default starting style is `dark` (`useStyleSwitcher.js:5` `currentStyle = ref('dark')`).

Inline raster style shape (reuse for any XYZ tile source):
```js
{ version: 8,
  sources: { 'osm-streets': { type:'raster', tiles:['https://tile.openstreetmap.org/{z}/{x}/{y}.png'], tileSize:256, attribution:'© OpenStreetMap contributors' } },
  layers: [{ id:'osm-streets-layer', type:'raster', source:'osm-streets', minzoom:0, maxzoom:19 }] }
```

### B.3 Dark/light pairing + switching

- `getBasemapPair(currentBasemap, targetMode)` (`mapStyles.js:120-130`): if current basemap's `theme` already matches target mode, returns it unchanged; else returns its `.pair` (or itself if none).
- `getStylesByTheme()` (`mapStyles.js:133-147`): groups entries into `{ day:[], night:[] }` for the dropdown.
- Mode toggle wiring (`MapEngine.vue:260-273` `toggleThemeMode`): compute `pairedBasemap = getBasemapPair(currentStyle, newMode)`, call `themeStore.toggleMode()`, then `switchStyle(pairedBasemap)` only if it changed. So flipping app light/dark ALSO swaps the basemap to its day/night counterpart.

`useStyleSwitcher(map, addDataLayer, callbacks)` (`src/composables/useStyleSwitcher.js`):
- Returns `{ currentStyle, switchStyle(styleName) }`.
- `switchStyle` saves camera (`center/zoom/bearing/pitch`), calls `map.setStyle(styleConfig.style)`, then — once the new style is ready — `jumpTo` the saved camera and re-adds overlays via `addDataLayer({ skipZoom:true })`.
- Robustness: a `switchGeneration` counter discards stale `style.load` callbacks during rapid switching (`useStyleSwitcher.js:11,46`); `whenStyleReady` polls `map.isStyleLoaded()` every 50ms with a 5s cap (`:13-30`); listens to BOTH `style.load` and `styledata` plus a 100ms fallback timeout for inline raster styles that parse synchronously (`:80-86`).
- `callbacks`: `setStyleChanging(bool)`, `recreateClusterExtentCircle()`, `onStyleReady()` (used to re-add country boundaries, bbox, host-plant layers — `MapEngine.vue:186-194`).

### B.4 Point / occurrence rendering (the data layer)

`useDataLayer(map, { onShowPopup })` (`src/composables/useDataLayer.js`) — returns `addDataLayer`, `fitBoundsToData`, `clearClusterExtentCircle`, `recreateClusterExtentCircle`, `updateClusterExtentColors`, `setStyleChanging`. Source/layer IDs and behaviors:

- **Source** `points-source` (GeoJSON, `addDataLayer:256-264`): `cluster: shouldCluster`, `clusterMaxZoom:14`, `clusterRadius:<radiusPixels>`, `clusterMinPoints:2`, `generateId:true`. Fast path reuses the source via `source.setData()` and only rebuilds layers when cluster on/off or radius changes (`:236-283`).
- **Cluster layers** (when clustering on, `:529-563`): circle layer `clusters` (filter `['has','point_count']`), radius `step` on `point_count` (12→16→20→25→32 at 20/50/100/500), color `step` (`#4ade80→#22d3ee→#facc15→#fb923c→#ef4444`), white stroke; symbol layer `cluster-count` showing `point_count_abbreviated + "\nrecords"`.
- **Individual points** (`:566-697`): layer `points-layer`. Two render modes:
  - circle (default): `circle-radius` zoom-interpolated from `style.pointSize`, `circle-color` via a `['match', ['get', colorAttr], …]` expression built from `store.activeColorMap` (legend overflow → grey `#6b7280`), per-feature `circle-sort-key` so colored points draw above grey, stroke color can be per-species.
  - symbol "baked shape" mode (`legendStore.shapeSettings.enabled`): pre-renders colored shape images with `map.addImage(name, data, {pixelRatio:2})` and an `icon-image` match expression (works around MapLibre per-feature border limitation).
- **Hover highlight**: layer `points-highlight` (`:708-721`), a transparent ring filtered to the hovered feature id; updated on `mouseenter/mouseleave` of `points-layer` (`:841-867`).
- **Click → popup**: `points-layer` click handler (`:811-838`) gathers all points at the clicked coordinate via `store.getPointsAtCoordinates(lat,lng)` and calls `onShowPopup({ type:'point', coordinates, lngLat, points, … })`.
- **Cluster click** (`:732-799`): tries `source.getClusterLeaves()` (with a 500ms timeout) and falls back to a haversine proximity search, computes cluster stats, draws an extent circle (`cluster-extent-dynamic` fill + outline, colored from the live theme accent via `getThemeAccentColor()`), then `onShowPopup({ type:'cluster', points, clusterStats, isCluster:true })`.
- **Other viz modes** also live here and share `points-source`: `heatmap-layer` (`:286-324`, settings-driven intensity/radius/opacity, blue→red ramp), and `ranges` (`:327-527`) producing either hexbin density (`@turf` hex grid, yellow→red ramp) or convex/concave hull polygons grouped by species/subspecies/genus/mimicry. Both optionally draw `range-points`. Drop these if your target only needs points/clusters.
- **Fit bounds** (`fitBoundsToData`, `:876-893`): single feature → `flyTo zoom 8`; else `fitBounds` with 50px padding, `maxZoom:12`.

**Popups** are Vue components teleported into a MapLibre `Popup` via `setDOMContent` (`MapEngine.vue:108-124`), with an alternative "docked" right-panel mode (`:135-181`). Popup class `custom-popup enhanced-popup`, `maxWidth:'500px'`, `closeButton:false, closeOnClick:true`.

**Reactivity:** `MapEngine.vue` watches `store.displayGeoJSON`, `clusteringEnabled`, `clusterSettings`, `visualizationMode`, `heatmapSettings`, `rangeSettings`, `styleVersion`, `focusPoint`, etc., funneling through a 50ms-debounced `debouncedAddDataLayer({ skipZoom })` (`:463-598`). Color recolor on theme change: `updateClusterExtentColors()` in a `watch([currentTheme,currentMode])` (`:220-230`).

### B.5 Map component API to build (target app)

Mirror this minimal surface (strip ranges/heatmap/shapes/SDM/host-plant unless needed):

```
<MapEngine
  :geojson="FeatureCollection"            // points; [lng,lat]
  :color-map="{ value: '#hex', … }"       // attr value → color
  :color-attr="'scientific_name'"         // feature property to color by
  :viz-mode="'points'|'clusters'|'heatmap'"
  :cluster-settings="{ radiusPixels:80, showClusterPoints:true }"
  @map-ready="(map)=>{}"
  @point-click="({coordinates,points})=>{}"
  @cluster-click="({coordinates,points,clusterStats})=>{}"
/>
```
Internals to port: `useStyleSwitcher` (verbatim — only depends on `mapStyles`), `mapStyles.js` (verbatim), `mapHelpers.js` (`removeLayerAndSource`, `generateCirclePolygon`, `getThemeAccentColor`, `colorToRgba` — verbatim), and a trimmed `useDataLayer` keeping `points-source` / `points-layer` / `points-highlight` / `clusters` / `cluster-count` only. The basemap dropdown + theme dropdown + mode toggle markup is in `MapEngine.vue:850-979` (self-contained, theme-var styled). Pinia stores it expects can be replaced by props; the only hard MapLibre dependency is `maplibre-gl`.

---

## C. GBIF OCCURRENCE FETCH

Two distinct flows exist. Pick by volume.

### C.1 Lighter flow — `occurrence/search` (recommended for "fetch occurrences for N taxa")

Reference impl: `scripts/host_plants/host_plant_pipeline.py` — `resolve_taxon` (`:462-545`) + `fetch_occurrences` (`:567-627`). No credentials, no DOI, synchronous, paginated. Constants (`:45-47,64`): `GBIF_SPECIES_MATCH_URL="https://api.gbif.org/v1/species/match"`, `GBIF_OCCURRENCE_SEARCH_URL` = `https://api.gbif.org/v1/occurrence/search`, `GBIF_PLANT_KINGDOM_KEY=6`, `REQUEST_DELAY_SECONDS=0.2`.

Recipe (per taxon):
1. **Resolve name → taxonKey** (`:493-503`): `GET /v1/species/match` with `{name, rank:'SPECIES'|'GENUS', kingdom, verbose:'true', strict:'false'}`. Use `usageKey` (or `acceptedUsageKey`). Reject if `matchType=='NONE'`, kingdom mismatch, or rank mismatch (`:508-510`).
2. **Page occurrences** (`fetch_occurrences`, `:572-617`):
```python
query = {
  "taxonKey": taxon_key,
  "hasCoordinate": "true",
  "occurrenceStatus": "PRESENT",
  # optional bbox filter (comma "min,max"):
  "decimalLongitude": f"{min_lon},{max_lon}",
  "decimalLatitude":  f"{min_lat},{max_lat}",
}
offset, page_limit = 0, min(300, limit)   # GBIF caps page size at 300
while len(records) < limit:
    r = requests.get(GBIF_OCCURRENCE_SEARCH_URL, params={**query, "limit":page_limit, "offset":offset}, timeout=45)
    data = r.json()
    for item in data["results"]:
        # filter: coords present, occurrenceStatus PRESENT, 'COORDINATE_INVALID' not in issues
        # dedupe on rounded (lon,lat)
        records.append({…})              # see field list below
    if data.get("endOfRecords") or not data["results"]: break
    offset += page_limit
    time.sleep(0.2)
```
Filter `occurrence_is_usable` (`:555-564`): lon/lat not None, `occurrenceStatus` PRESENT, no `COORDINATE_INVALID` issue, within optional bbox. Dedupe by rounded 6-dp `(lon,lat)` (`:589-594`). Fields kept per record (`:595-611`): `gbifID, species, genus, family, scientificName, decimalLongitude, decimalLatitude, coordinateUncertaintyInMeters, basisOfRecord, eventDate, country, datasetName, publisher, license, issues`. Note the **`offset+limit ≤ 100000` hard cap** on GBIF search — use the Download API (C.2) beyond that.

### C.2 Heavy flow — async Download API (citable DOI, whole-dataset)

Reference impl: `scripts/gbif_download_api.py` (full file). Requires creds `GBIF_USERNAME/GBIF_PASSWORD/GBIF_EMAIL` (env vars first, else `gbif_credentials.env` KEY=VALUE file — `load_credentials:84-119`). HTTP basic-auth `auth=(USERNAME, PASSWORD)` on every call.

Flow:
1. **Taxon keys**: `GET https://api.gbif.org/v1/species/match` per genus with strict validation (rank GENUS, order Lepidoptera, family Nymphalidae) — `get_genus_taxon_key:143-180`; cached to `gbif_taxon_keys.json` (`get_all_taxon_keys:215-279`).
2. **Reuse check** (`find_recent_download:286-338`): `GET /v1/occurrence/download/user/{username}` (basic-auth), reuse a `SUCCEEDED` download <24h old whose predicate TAXON_KEY set matches (`_extract_taxon_keys_from_predicate:341-362` recurses `and`/`not` predicates).
3. **Submit** (`submit_download_request:365-424`): `POST https://api.gbif.org/v1/occurrence/download/request` (basic-auth, `Content-Type: application/json`). Body:
```json
{ "creator":"<USERNAME>", "notificationAddresses":["<EMAIL>"], "sendNotification":true, "format":"DWCA",
  "predicate": { "type":"and", "predicates":[
    { "type":"in", "key":"TAXON_KEY", "values":[<keys…>] },
    { "type":"equals", "key":"HAS_COORDINATE", "value":"true" },
    { "type":"equals", "key":"HAS_GEOSPATIAL_ISSUE", "value":"false" },
    { "type":"equals", "key":"OCCURRENCE_STATUS", "value":"PRESENT" },
    { "type":"not", "predicate":{ "type":"in", "key":"BASIS_OF_RECORD", "values":["FOSSIL_SPECIMEN","LIVING_SPECIMEN"] } }
  ] } }
```
Response body is the plain-text `download_key`.
4. **Poll** (`wait_for_download:427-460`): `GET /v1/occurrence/download/{key}` (basic-auth) every `POLL_INTERVAL_SECONDS=30`, up to `MAX_POLL_ATTEMPTS=120` (60 min). Stop on `status=='SUCCEEDED'`; abort on `FAILED/KILLED/CANCELLED`.
5. **Download + extract DWCA** (`download_and_extract:463-547`): `GET download_info['downloadLink']` (stream, `timeout=600`), it's a ZIP containing `occurrence.txt` (+ optional `multimedia.txt`); validates/reuses an existing local zip, deletes zip after extract. Both files are **tab-separated** Darwin Core.
6. **Parse** (`process_occurrence_file:697-800`): `csv.DictReader(f, delimiter='\t')`. Per row: require `decimalLatitude/decimalLongitude` floats; build `scientific_name` from `genus + specificEpithet`; clean author citations (`clean_scientific_name:554-579`); read `infraspecificEpithet`, `country/countryCode`, `eventDate`, `basisOfRecord`, `institutionCode`, `coordinateUncertaintyInMeters`, etc. Image URLs come from `multimedia.txt` (`load_multimedia_lookup:582-614`, first `StillImage` per `gbifID`). Source tagging (`get_source:673-682`): iNaturalist (datasetKey `50c9509d-22c7-4a22-a47d-8c48425ef4a7`), UNAM, or other.
7. **Citation** (`save_citation:803-838`): `download_info['doi']` → `citation_text = "GBIF Occurrence Download https://doi.org/{doi} accessed via GBIF.org on {date}"`.

DWCA also carries pre-resolved taxonomy (`taxonKey, acceptedTaxonKey, taxonomicStatus, taxonRank`) you can harvest without extra API calls (`enrich_taxonomy_cache:886-1042`).

**Mirror for "fetch occurrences for N taxa":** for ≤ a few thousand pts/taxon and no DOI needed → loop C.1 (`match` → paged `search`, 300/page, 0.2s delay, dedupe). For a citable full export → C.2 (one Download API request with a `TAXON_KEY in [...]` predicate, poll, parse DWCA). The download predicate quality filters (HAS_COORDINATE / HAS_GEOSPATIAL_ISSUE=false / OCCURRENCE_STATUS=PRESENT / exclude FOSSIL+LIVING) are the canonical "research-grade" set to copy.

---

## D. Port checklist (copy-verbatim vs adapt)

- **Verbatim:** `src/themes/presets.js`, `src/stores/theme.js` (stub `../utils/logger`), `src/index.css` theme blocks, `src/utils/mapStyles.js`, `src/utils/mapHelpers.js`, `src/composables/useStyleSwitcher.js`.
- **Adapt (trim):** `src/composables/useDataLayer.js` (keep points+clusters, drop ranges/heatmap/shapes), `src/components/MapEngine.vue` (keep init + basemap/theme dropdowns + point popups), `src/components/ThemeSelector.vue` (needs shadcn-vue or rebuild).
- **Adapt (Python):** `scripts/gbif_download_api.py` (heavy) and the `fetch_occurrences`/`resolve_taxon` pair from `scripts/host_plants/host_plant_pipeline.py` (light).
