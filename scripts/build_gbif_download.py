#!/usr/bin/env python3
"""
build_gbif_download.py — single CITABLE GBIF Download-API pipeline.

Replaces the per-taxon occurrence/search approach with ONE authenticated, batched
asynchronous Download-API request (citable DOI, DWCA export). Python stdlib only.

Reference: .research/ithomiini_port_spec.md section C.2 (the authoritative flow).

Outputs (written atomically via *.tmp -> os.replace):
  public/data/occurrences.json
  public/data/species_images.json
  public/data/gbif_attribution.json

SAFETY: never overwrites existing working JSONs with worse/empty data. If the
download fails or yields far fewer taxa than the search-API baseline
(58 occ taxa / ~300 image taxa), the existing files are KEPT and the problem
is reported.
"""

import base64
import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
import zipfile

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRED_FILE = "/home/franz/Documents/CodeProjs/gbif_credentials_complete.env"
INTERACTIONS = [
    os.path.join(ROOT, "src", "data", "interactions.json"),
    os.path.join(ROOT, "src", "data", "interactions_ephi.json"),
]
PAPERS_DIR = os.path.join(ROOT, "papers")
ZIP_PATH = os.path.join(PAPERS_DIR, "gbif_download.zip")
EXTRACT_DIR = os.path.join(PAPERS_DIR, "gbif_dwca")
PUBLIC_DATA = os.path.join(ROOT, "public", "data")
OUT_OCC = os.path.join(PUBLIC_DATA, "occurrences.json")
OUT_IMG = os.path.join(PUBLIC_DATA, "species_images.json")
OUT_ATTR = os.path.join(PUBLIC_DATA, "gbif_attribution.json")

# GBIF endpoints
MATCH_URL = "https://api.gbif.org/v1/species/match"
DOWNLOAD_REQUEST_URL = "https://api.gbif.org/v1/occurrence/download/request"
DOWNLOAD_STATUS_URL = "https://api.gbif.org/v1/occurrence/download/"

# Baseline from the search-API version — refuse to overwrite with worse data.
BASELINE_OCC_TAXA = 58
BASELINE_IMG_TAXA = 300

# Tunables
POLL_INTERVAL = 30
MAX_POLL = 40
POINTS_CAP = 250
IMAGES_CAP = 6
INAT_DATASET_KEY = "50c9509d-22c7-4a22-a47d-8c48425ef4a7"
USER_AGENT = "tandayapa-interactions-gbif-pipeline/1.0 (stdlib)"

# Regional bbox (bound size + Tandayapa relevance)
BBOX = {"lat_min": "-6", "lat_max": "3", "lon_min": "-82", "lon_max": "-74"}


def log(msg):
    print(msg, flush=True)


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------
def load_credentials():
    creds = {}
    with open(CRED_FILE, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            creds[k.strip()] = v.strip()
    user = creds.get("GBIF_USERNAME")
    pw = creds.get("GBIF_PASSWORD")
    email = creds.get("GBIF_EMAIL")
    if not (user and pw and email):
        raise RuntimeError("Missing GBIF_USERNAME / GBIF_PASSWORD / GBIF_EMAIL")
    token = base64.b64encode(f"{user}:{pw}".encode("utf-8")).decode("ascii")
    return user, pw, email, token


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def http_get_json(url, auth_token=None, timeout=60):
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", USER_AGENT)
    req.add_header("Accept", "application/json")
    if auth_token:
        req.add_header("Authorization", f"Basic {auth_token}")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_post(url, body_bytes, auth_token, timeout=120):
    req = urllib.request.Request(url, data=body_bytes, method="POST")
    req.add_header("User-Agent", USER_AGENT)
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Basic {auth_token}")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8").strip(), resp.status


# ---------------------------------------------------------------------------
# STEP 1 — collect taxa
# ---------------------------------------------------------------------------
GROUP_HINT = {
    "hummingbird": ("class", "Aves"),
    "bird": ("class", "Aves"),
    "bat": ("class", "Mammalia"),
    "mammal": ("class", "Mammalia"),
    "insect": ("class", "Insecta"),
    "plant": ("kingdom", "Plantae"),
    # 'parasite' intentionally has no hint -> resolved loosely or skipped
}


def collect_taxa():
    """Return dict: name -> group (group = whichever was first seen)."""
    taxa = {}
    for path in INTERACTIONS:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        for rec in data.get("records", []):
            for name_key, grp_key in (("source", "sourceGroup"), ("target", "targetGroup")):
                name = (rec.get(name_key) or "").strip()
                grp = (rec.get(grp_key) or "").strip()
                if not name:
                    continue
                if name not in taxa:
                    taxa[name] = grp
    return taxa


# ---------------------------------------------------------------------------
# STEP 2 — resolve keys (anonymous species/match)
# ---------------------------------------------------------------------------
def resolve_taxon(name, group):
    """Resolve a taxon name to a GBIF usageKey (genusKey for ' sp.').

    Returns dict with key, accepted_canonical, genus, or None.
    """
    is_sp = name.endswith(" sp.")
    query_name = name[:-4].strip() if is_sp else name

    params = {"name": query_name, "strict": "false", "verbose": "true"}
    hint = GROUP_HINT.get(group)
    if hint:
        params[hint[0]] = hint[1]

    url = MATCH_URL + "?" + urllib.parse.urlencode(params)
    try:
        result = http_get_json(url, timeout=45)
    except Exception as exc:  # noqa: BLE001
        log(f"  ! match error for {name!r}: {exc}")
        return None

    if not result or result.get("matchType") == "NONE":
        return None

    if is_sp:
        key = result.get("genusKey") or result.get("usageKey")
    else:
        key = result.get("usageKey")
    if not key:
        return None

    genus = (result.get("genus") or "").strip()
    # acceptedCanonical: prefer canonicalName, else species, else scientificName stem
    accepted = (
        result.get("canonicalName")
        or result.get("species")
        or result.get("scientificName")
        or ""
    ).strip()

    return {
        "key": int(key),
        "accepted_canonical": accepted,
        "genus": genus,
        "is_sp": is_sp,
    }


def build_taxon_maps():
    taxa = collect_taxa()
    log(f"STEP 1: collected {len(taxa)} unique taxon names "
        f"across {len(INTERACTIONS)} interaction files")

    key_to_name = {}              # usageKey/genusKey -> my taxon name
    canonical_to_name = {}        # acceptedCanonical lower -> my taxon name
    genus_to_name = {}            # genus lower -> my taxon name
    resolved_keys = set()
    unresolved = []

    log("STEP 2: resolving taxon keys via species/match (anonymous) ...")
    for i, (name, group) in enumerate(sorted(taxa.items()), 1):
        res = resolve_taxon(name, group)
        if not res:
            unresolved.append(name)
            continue
        key = res["key"]
        resolved_keys.add(key)
        # first writer wins for the key map; do not clobber an exact-species
        # mapping with a later one
        key_to_name.setdefault(key, name)
        if res["accepted_canonical"]:
            canonical_to_name.setdefault(res["accepted_canonical"].lower(), name)
        if res["genus"]:
            genus_to_name.setdefault(res["genus"].lower(), name)
        # also index the bare genus of a "Genus sp." record
        if res["is_sp"]:
            base = name[:-4].strip().lower()
            genus_to_name.setdefault(base, name)
        time.sleep(0.05)
        if i % 50 == 0:
            log(f"  ... resolved {len(resolved_keys)} keys ({i}/{len(taxa)} processed)")

    log(f"STEP 2 done: {len(resolved_keys)} resolved keys, "
        f"{len(unresolved)} unresolved")
    if unresolved:
        log("  unresolved: " + ", ".join(unresolved[:30])
            + (" ..." if len(unresolved) > 30 else ""))

    return {
        "resolved_keys": sorted(resolved_keys),
        "key_to_name": key_to_name,
        "canonical_to_name": canonical_to_name,
        "genus_to_name": genus_to_name,
    }


# ---------------------------------------------------------------------------
# STEP 3 — submit download
# ---------------------------------------------------------------------------
def build_predicate(keys):
    return {
        "type": "and",
        "predicates": [
            {"type": "in", "key": "TAXON_KEY", "values": [str(k) for k in keys]},
            {"type": "equals", "key": "HAS_COORDINATE", "value": "true"},
            {"type": "equals", "key": "HAS_GEOSPATIAL_ISSUE", "value": "false"},
            {"type": "equals", "key": "OCCURRENCE_STATUS", "value": "PRESENT"},
            {"type": "not", "predicate": {
                "type": "in", "key": "BASIS_OF_RECORD",
                "values": ["FOSSIL_SPECIMEN", "LIVING_SPECIMEN"]}},
            {"type": "and", "predicates": [
                {"type": "greaterThanOrEquals", "key": "DECIMAL_LATITUDE", "value": BBOX["lat_min"]},
                {"type": "lessThanOrEquals", "key": "DECIMAL_LATITUDE", "value": BBOX["lat_max"]},
                {"type": "greaterThanOrEquals", "key": "DECIMAL_LONGITUDE", "value": BBOX["lon_min"]},
                {"type": "lessThanOrEquals", "key": "DECIMAL_LONGITUDE", "value": BBOX["lon_max"]},
            ]},
        ],
    }


def submit_download(keys, user, email, token):
    body = {
        "creator": user,
        "notificationAddresses": [email],
        "sendNotification": False,
        "format": "DWCA",
        "predicate": build_predicate(keys),
    }
    body_bytes = json.dumps(body).encode("utf-8")
    log(f"STEP 3: submitting download request for {len(keys)} taxon keys ...")
    key, status = http_post(DOWNLOAD_REQUEST_URL, body_bytes, token)
    log(f"STEP 3: download submitted (HTTP {status}) -> key {key}")
    return key


# ---------------------------------------------------------------------------
# STEP 4 — poll
# ---------------------------------------------------------------------------
def wait_for_download(download_key, token):
    log(f"STEP 4: polling download {download_key} "
        f"(every {POLL_INTERVAL}s, up to {MAX_POLL} attempts) ...")
    for attempt in range(1, MAX_POLL + 1):
        try:
            info = http_get_json(DOWNLOAD_STATUS_URL + download_key, auth_token=token, timeout=60)
        except Exception as exc:  # noqa: BLE001
            log(f"  poll {attempt}: error {exc} (retrying)")
            time.sleep(POLL_INTERVAL)
            continue
        status = info.get("status")
        recs = info.get("totalRecords")
        log(f"  poll {attempt}/{MAX_POLL}: status={status} totalRecords={recs}")
        if status == "SUCCEEDED":
            return info
        if status in ("FAILED", "KILLED", "CANCELLED"):
            raise RuntimeError(f"Download {download_key} ended with status {status}")
        time.sleep(POLL_INTERVAL)
    raise RuntimeError(f"Download {download_key} not ready after {MAX_POLL} polls")


# ---------------------------------------------------------------------------
# STEP 5 — download + extract
# ---------------------------------------------------------------------------
def download_and_extract(download_link, token):
    os.makedirs(PAPERS_DIR, exist_ok=True)
    log(f"STEP 5: downloading zip from {download_link} ...")
    req = urllib.request.Request(download_link, method="GET")
    req.add_header("User-Agent", USER_AGENT)
    req.add_header("Authorization", f"Basic {token}")
    with urllib.request.urlopen(req, timeout=600) as resp, open(ZIP_PATH, "wb") as out:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
    size = os.path.getsize(ZIP_PATH)
    log(f"STEP 5: saved {ZIP_PATH} ({size} bytes)")

    os.makedirs(EXTRACT_DIR, exist_ok=True)
    occ_path = img_path = None
    with zipfile.ZipFile(ZIP_PATH) as zf:
        names = zf.namelist()
        for member in names:
            base = os.path.basename(member)
            if base == "occurrence.txt":
                zf.extract(member, EXTRACT_DIR)
                occ_path = os.path.join(EXTRACT_DIR, member)
            elif base == "multimedia.txt":
                zf.extract(member, EXTRACT_DIR)
                img_path = os.path.join(EXTRACT_DIR, member)
    log(f"STEP 5: extracted occurrence.txt={bool(occ_path)} multimedia.txt={bool(img_path)}")
    if not occ_path:
        raise RuntimeError("occurrence.txt not found in DWCA zip")
    return occ_path, img_path


# ---------------------------------------------------------------------------
# STEP 6 — parse occurrence.txt
# ---------------------------------------------------------------------------
def fnum(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def map_to_taxon(row, maps):
    species = (row.get("species") or "").strip().lower()
    if species and species in maps["canonical_to_name"]:
        return maps["canonical_to_name"][species]
    genus = (row.get("genus") or "").strip().lower()
    if genus and genus in maps["genus_to_name"]:
        return maps["genus_to_name"][genus]
    # fall back to acceptedScientificName/scientificName canonical match
    return None


def parse_occurrences(occ_path, maps):
    log("STEP 6: parsing occurrence.txt ...")
    occ = {}                  # myTaxon -> {count, points, _seen}
    gbif_lookup = {}          # gbifID -> (myTaxon, basis, datasetKey)
    csv.field_size_limit(1 << 24)
    total_rows = 0
    mapped_rows = 0
    with open(occ_path, "r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for row in reader:
            total_rows += 1
            lat = fnum(row.get("decimalLatitude"))
            lng = fnum(row.get("decimalLongitude"))
            if lat is None or lng is None:
                continue
            taxon = map_to_taxon(row, maps)
            if not taxon:
                continue
            mapped_rows += 1
            basis = (row.get("basisOfRecord") or "").strip()
            country = (row.get("countryCode") or "").strip()
            gbif_id = (row.get("gbifID") or "").strip()
            dataset_key = (row.get("datasetKey") or "").strip()

            year_raw = (row.get("year") or "").strip()
            try:
                year = int(year_raw) if year_raw else ""
            except ValueError:
                year = ""

            if gbif_id:
                gbif_lookup[gbif_id] = (taxon, basis, dataset_key)

            bucket = occ.setdefault(taxon, {"count": 0, "points": [], "_seen": set()})
            bucket["count"] += 1
            if len(bucket["points"]) >= POINTS_CAP:
                continue
            rkey = (round(lat, 5), round(lng, 5))
            if rkey in bucket["_seen"]:
                continue
            bucket["_seen"].add(rkey)
            bucket["points"].append({
                "lat": round(lat, 6),
                "lng": round(lng, 6),
                "year": year,
                "basis": basis,
                "country": country,
            })

    for t in occ:
        occ[t].pop("_seen", None)

    log(f"STEP 6: parsed {total_rows} rows, {mapped_rows} mapped to "
        f"{len(occ)} taxa")
    return occ, gbif_lookup


# ---------------------------------------------------------------------------
# STEP 7 — parse multimedia.txt
# ---------------------------------------------------------------------------
IMG_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff")


def looks_like_image(url, fmt):
    if not url:
        return False
    u = url.lower()
    if not (u.startswith("http://") or u.startswith("https://")):
        return False
    if (fmt or "").lower().startswith("image/"):
        return True
    if any(ext in u for ext in IMG_EXT):
        return True
    # iNaturalist / many providers serve extensionless image endpoints
    if "inaturalist" in u or "/photos/" in u or "/media/" in u:
        return True
    return False


def rank_for(source, basis):
    """Lower sort value = higher priority. iNat observation first, specimen last."""
    if source == "iNaturalist" and basis == "HUMAN_OBSERVATION":
        return 0
    if basis == "HUMAN_OBSERVATION":
        return 1
    if basis == "MACHINE_OBSERVATION":
        return 2
    if basis == "PRESERVED_SPECIMEN":
        return 4
    return 3


def parse_multimedia(img_path, gbif_lookup):
    images = {}  # myTaxon -> list of (rank, idx, record)
    if not img_path:
        log("STEP 7: no multimedia.txt — skipping images")
        return {}
    log("STEP 7: parsing multimedia.txt ...")
    csv.field_size_limit(1 << 24)
    rows_seen = 0
    img_rows = 0
    idx = 0
    with open(img_path, "r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for row in reader:
            rows_seen += 1
            if (row.get("type") or "").strip() != "StillImage":
                continue
            identifier = (row.get("identifier") or "").strip()
            fmt = (row.get("format") or "").strip()
            if not looks_like_image(identifier, fmt):
                continue
            gbif_id = (row.get("gbifID") or "").strip()
            meta = gbif_lookup.get(gbif_id)
            if not meta:
                continue
            taxon, basis, dataset_key = meta

            publisher = (row.get("publisher") or "").strip()
            is_inat = (
                dataset_key == INAT_DATASET_KEY
                or "inaturalist" in publisher.lower()
                or "inaturalist" in identifier.lower()
            )
            source = "iNaturalist" if is_inat else "GBIF"
            license_ = (row.get("license") or "").strip()
            creator = (row.get("creator") or "").strip() or (row.get("rightsHolder") or "").strip()
            references = (row.get("references") or "").strip()
            source_url = references or f"https://www.gbif.org/occurrence/{gbif_id}"

            enc = urllib.parse.quote(identifier, safe="")
            image_url = f"https://wsrv.nl/?url={enc}&w=480&output=webp"

            lic_part = f" ({license_})" if license_ else ""
            cred = creator if creator else "unknown"
            attribution = f"© {cred}, {source}{lic_part}"

            record = {
                "original_url": identifier,
                "image_url": image_url,
                "license": license_,
                "creator": creator,
                "publisher": publisher,
                "source": source,
                "basis": basis,
                "source_url": source_url,
                "attribution": attribution,
            }
            img_rows += 1
            idx += 1
            images.setdefault(taxon, []).append((rank_for(source, basis), idx, record))

    out = {}
    for taxon, items in images.items():
        items.sort(key=lambda x: (x[0], x[1]))
        seen_urls = set()
        picked = []
        for _, _, rec in items:
            if rec["original_url"] in seen_urls:
                continue
            seen_urls.add(rec["original_url"])
            picked.append(rec)
            if len(picked) >= IMAGES_CAP:
                break
        if picked:
            out[taxon] = {"images": picked}

    log(f"STEP 7: scanned {rows_seen} media rows, {img_rows} usable images, "
        f"{len(out)} taxa with images")
    return out


# ---------------------------------------------------------------------------
# Atomic write + validation
# ---------------------------------------------------------------------------
def write_json_atomic(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
    # validate non-empty valid JSON
    with open(tmp, "r", encoding="utf-8") as fh:
        json.load(fh)
    if os.path.getsize(tmp) == 0:
        raise RuntimeError(f"Refusing to write empty {path}")
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    # Optional resume: `--resume <downloadKey>` skips STEP 3 submission and
    # reuses an already-submitted download (polls it to completion, then
    # downloads + parses). Avoids re-submitting a large export.
    resume_key = None
    args = sys.argv[1:]
    if args and args[0] == "--resume" and len(args) >= 2:
        resume_key = args[1].strip()

    user, pw, email, token = load_credentials()
    log(f"Credentials loaded for GBIF user {user!r}")

    maps = build_taxon_maps()
    keys = maps["resolved_keys"]
    if not keys:
        log("ABORT: no resolved taxon keys; keeping existing files.")
        return 1

    download_key = resume_key
    try:
        if resume_key:
            log(f"RESUME: reusing existing download key {resume_key} "
                "(skipping submission)")
        else:
            download_key = submit_download(keys, user, email, token)
        info = wait_for_download(download_key, token)
    except Exception as exc:  # noqa: BLE001
        log(f"ABORT: download submit/poll failed: {exc}")
        log("Keeping existing output files unchanged.")
        if download_key:
            log(f"  Resume later with: python3 scripts/build_gbif_download.py "
                f"--resume {download_key}")
        return 1

    doi = info.get("doi") or ""
    total_records = info.get("totalRecords") or 0
    size = info.get("size") or 0
    download_link = info.get("downloadLink")
    log(f"Download SUCCEEDED: doi={doi} totalRecords={total_records} "
        f"size={size} link={download_link}")

    if not download_link:
        log("ABORT: no downloadLink in succeeded download; keeping existing files.")
        return 1

    try:
        occ_path, img_path = download_and_extract(download_link, token)
    except Exception as exc:  # noqa: BLE001
        log(f"ABORT: download/extract failed: {exc}; keeping existing files.")
        return 1

    occ, gbif_lookup = parse_occurrences(occ_path, maps)
    images = parse_multimedia(img_path, gbif_lookup)

    occ_taxa = len(occ)
    img_taxa = len(images)
    total_points = sum(len(v["points"]) for v in occ.values())

    citation = (
        f"GBIF Occurrence Download https://doi.org/{doi} "
        f"accessed via GBIF.org on the build date"
    )
    attribution_text = (
        "GBIF.org occurrence download via the Download API (DWCA, citable DOI). "
        "Observations prioritised; images served as URLs under each record's CC license."
    )

    # ---- SAFETY GATE: do not overwrite with materially worse data ----
    # Occurrence taxa must at least roughly match the search-API baseline.
    OCC_FLOOR = int(BASELINE_OCC_TAXA * 0.85)   # ~49
    if occ_taxa < OCC_FLOOR or total_points == 0:
        log(f"ABORT (safety): occ taxa {occ_taxa} < floor {OCC_FLOOR} "
            f"or zero points ({total_points}). Search-API baseline was "
            f"{BASELINE_OCC_TAXA}. KEEPING existing files; NOT overwriting.")
        log(f"  (images would have been {img_taxa} taxa)")
        return 2

    occurrences_out = dict(occ)
    occurrences_out["_meta"] = {
        "total_points": total_points,
        "taxa_with_occurrences": occ_taxa,
        "doi": doi,
        "citation": citation,
        "attribution": attribution_text,
    }

    attribution_out = {
        "doi": doi,
        "citation": citation,
        "note": (
            "Occurrence and media data from a single citable GBIF Download API "
            "export (DWCA). Images are served as URLs under each record's "
            "individual Creative Commons license (see each entry's license and "
            "source_url). Observations (iNaturalist / HUMAN_OBSERVATION) are "
            "prioritised over preserved specimens."
        ),
        "source": "https://www.gbif.org",
        "total_records": total_records,
        "generated_by": "scripts/build_gbif_download.py",
    }

    # Write occurrences first (the gated, must-have file).
    write_json_atomic(OUT_OCC, occurrences_out)
    log(f"WROTE {OUT_OCC} ({occ_taxa} taxa, {total_points} points)")

    # Images: only overwrite if we got a reasonable amount; else keep existing.
    img_floor = int(BASELINE_IMG_TAXA * 0.5)
    if img_taxa >= img_floor:
        species_images_out = dict(images)
        write_json_atomic(OUT_IMG, species_images_out)
        log(f"WROTE {OUT_IMG} ({img_taxa} taxa with images)")
        img_replaced = True
    else:
        log(f"KEEP {OUT_IMG}: only {img_taxa} image taxa < floor {img_floor} "
            f"(baseline {BASELINE_IMG_TAXA}); existing images preserved.")
        img_replaced = False

    write_json_atomic(OUT_ATTR, attribution_out)
    log(f"WROTE {OUT_ATTR}")

    # ---------------- FINAL REPORT ----------------
    log("")
    log("================ FINAL REPORT ================")
    log(f"DOI:                 https://doi.org/{doi}")
    log(f"totalRecords:        {total_records}")
    log(f"taxa w/ occurrences: {occ_taxa} (baseline {BASELINE_OCC_TAXA})")
    log(f"total map points:    {total_points}")
    log(f"taxa w/ images:      {img_taxa} (baseline {BASELINE_IMG_TAXA})")
    log(f"occurrences.json:    {OUT_OCC} -> REPLACED")
    log(f"species_images.json: {OUT_IMG} -> "
        f"{'REPLACED' if img_replaced else 'KEPT (existing better)'}")
    log(f"gbif_attribution.json: {OUT_ATTR} -> REPLACED")
    log("=============================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
