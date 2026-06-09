#!/usr/bin/env python3
"""Pre-fetch one representative GBIF image per taxon for the static site.

Reads src/data/interactions.json, collects unique taxa from source/target,
resolves each to a GBIF usageKey, fetches a license-clean StillImage, wraps it
through the wsrv.nl resize proxy, and writes:
  - public/data/species_images.json   (taxon -> image record)
  - public/data/gbif_attribution.json  (provenance note)

Standard library only. Idempotent and re-runnable.
"""

import json
import time
import urllib.parse
import urllib.request
import urllib.error
import os
import sys

USER_AGENT = "tandayapa-interactions/0.1 (mailto:fchandi@estud.usfq.edu.ec)"
RATE_LIMIT_S = 0.2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_PATH = os.path.join(ROOT, "src", "data", "interactions.json")
OUT_DIR = os.path.join(ROOT, "public", "data")
IMAGES_PATH = os.path.join(OUT_DIR, "species_images.json")
ATTR_PATH = os.path.join(OUT_DIR, "gbif_attribution.json")

SPECIES_MATCH = "https://api.gbif.org/v1/species/match"
OCC_SEARCH = "https://api.gbif.org/v1/occurrence/search"
WSRV = "https://wsrv.nl/"

# Higher-taxonomy hints keyed by interaction group.
GROUP_HINTS = {
    "hummingbird": {"class": "Aves"},
    "bird": {"class": "Aves"},
    "bat": {"class": "Mammalia"},
    "mammal": {"class": "Mammalia"},
    "insect": {"class": "Insecta"},
    "parasite": {},          # no class hint
    "plant": {"kingdom": "Plantae"},
}

LICENSE_PARAMS = [("license", "CC0_1_0"), ("license", "CC_BY_4_0")]


def http_get_json(url, params):
    """GET a URL with query params, return parsed JSON (or None on failure)."""
    query = urllib.parse.urlencode(params, doseq=True)
    full = url + "?" + query if query else url
    req = urllib.request.Request(full, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read().decode("utf-8", "replace")
        return json.loads(data)
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, TimeoutError) as e:
        print("  HTTP error for %s: %s" % (full, e), file=sys.stderr)
        return None
    finally:
        time.sleep(RATE_LIMIT_S)


def collect_taxa(records):
    """Return ordered dict of taxon name -> group from source/target fields."""
    taxa = {}
    for r in records:
        s = r.get("source")
        if s and s not in taxa:
            taxa[s] = r.get("sourceGroup")
        t = r.get("target")
        if t and t not in taxa:
            taxa[t] = r.get("targetGroup")
    return taxa


def resolve_key(name, group):
    """Resolve a taxon name to a GBIF key. Returns (key, matched_name) or (None, None).

    For names ending in ' sp.' strip to genus and match at genus rank,
    preferring genusKey.
    """
    is_sp = name.endswith(" sp.")
    query_name = name[:-len(" sp.")].strip() if is_sp else name

    params = [("name", query_name), ("strict", "false"), ("verbose", "true")]
    for k, v in GROUP_HINTS.get(group, {}).items():
        params.append((k, v))

    res = http_get_json(SPECIES_MATCH, params)
    if not res:
        return None, None
    if res.get("matchType", "NONE") == "NONE":
        return None, None

    if is_sp:
        key = res.get("genusKey") or res.get("usageKey")
    else:
        key = res.get("usageKey") or res.get("genusKey")
    if not key:
        return None, None
    matched = res.get("scientificName") or res.get("canonicalName") or query_name
    return key, matched


def looks_like_image_url(url):
    if not url or not isinstance(url, str):
        return False
    if not url.lower().startswith(("http://", "https://")):
        return False
    return True


def extract_image(occ_results):
    """Walk occurrence results -> media; return first usable StillImage dict or None."""
    for occ in occ_results:
        media = occ.get("media") or []
        for m in media:
            if m.get("type") != "StillImage":
                continue
            identifier = m.get("identifier")
            if not looks_like_image_url(identifier):
                continue
            return {
                "identifier": identifier,
                "media_license": m.get("license"),
                "occ_license": occ.get("license"),
                "creator": m.get("rightsHolder") or m.get("creator")
                or occ.get("rightsHolder") or occ.get("recordedBy"),
                "publisher": m.get("publisher") or occ.get("publisher")
                or occ.get("institutionCode"),
                "references": m.get("references") or occ.get("references"),
                "gbifID": occ.get("gbifID") or occ.get("key"),
                "species": occ.get("species"),
                "scientificName": occ.get("scientificName"),
            }
    return None


def fetch_image(key):
    """Fetch a license-clean image for a taxon key. Returns image dict or None."""
    base = [("taxonKey", str(key)), ("mediaType", "StillImage"), ("limit", "20")]

    # First try: restrict to CC0 / CC-BY-4.0.
    res = http_get_json(OCC_SEARCH, base + LICENSE_PARAMS)
    if res and res.get("results"):
        img = extract_image(res["results"])
        if img:
            return img

    # Retry once without the license filter; keep whatever license the record has.
    res = http_get_json(OCC_SEARCH, base)
    if res and res.get("results"):
        img = extract_image(res["results"])
        if img:
            return img
    return None


def wsrv_proxy(original_url):
    q = urllib.parse.urlencode({"url": original_url, "w": "480", "output": "webp"})
    return WSRV + "?" + q


def build_attribution(creator, publisher, license_str):
    parts = []
    lead = "©"
    if creator:
        lead += " " + creator
    if publisher:
        lead += ", " + publisher if creator else " " + publisher
    bits = lead.strip()
    if bits == "©":
        bits = ""
    if bits:
        parts.append(bits)
    if license_str:
        parts.append("(%s)" % license_str)
    return " ".join(parts).strip() or None


def main():
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    records = data.get("records", [])
    taxa = collect_taxa(records)
    n_total = len(taxa)
    print("Collected %d unique taxa from %d records." % (n_total, len(records)))

    images = {}
    n_found = 0
    missed = []

    for name, group in taxa.items():
        try:
            key, matched = resolve_key(name, group)
            if not key:
                print("MISS %s (no match)" % name)
                missed.append(name)
                continue
            img = fetch_image(key)
            if not img:
                print("MISS %s (no image)" % name)
                missed.append(name)
                continue

            license_str = img.get("media_license") or img.get("occ_license")
            creator = img.get("creator")
            publisher = img.get("publisher")
            gbif_id = img.get("gbifID")
            original = img["identifier"]

            record = {
                "image_url": wsrv_proxy(original),
                "original_url": original,
                "license": license_str,
                "creator": creator,
                "publisher": publisher,
                "attribution": build_attribution(creator, publisher, license_str),
                "source_url": ("https://www.gbif.org/occurrence/%s" % gbif_id)
                if gbif_id else None,
                "gbifID": str(gbif_id) if gbif_id is not None else None,
            }
            images[name] = record
            n_found += 1
            print("OK %s -> %s" % (name, license_str or "unknown"))
        except Exception as e:  # noqa: BLE001 — one taxon must not abort the run
            print("MISS %s (error: %s)" % (name, e), file=sys.stderr)
            missed.append(name)

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(IMAGES_PATH, "w", encoding="utf-8") as f:
        json.dump(images, f, ensure_ascii=False, indent=2, sort_keys=True)

    attribution = {
        "note": ("Occurrence and media data from GBIF (https://www.gbif.org). "
                 "Images are reproduced under their individual per-record Creative "
                 "Commons licenses (CC0 / CC-BY); see each entry's license and "
                 "source_url for attribution."),
        "source": "https://www.gbif.org",
        "generated_by": "scripts/build_gbif_images.py",
    }
    with open(ATTR_PATH, "w", encoding="utf-8") as f:
        json.dump(attribution, f, ensure_ascii=False, indent=2)

    print("\nimages: %d/%d" % (n_found, n_total))
    if missed:
        print("missed: " + ", ".join(missed))


if __name__ == "__main__":
    main()
