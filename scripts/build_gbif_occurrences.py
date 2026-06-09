#!/usr/bin/env python3
"""Build public/data/occurrences.json: georeferenced GBIF occurrences for every
taxon in src/data/interactions.json, for an occurrence map.

Stdlib only (urllib). Resolves each taxon to a GBIF usageKey via species/match,
then pages occurrence/search capturing up to ~200 georeferenced records/taxon.
"""
import json
import os
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
INTERACTIONS = os.path.join(ROOT, "src", "data", "interactions.json")
OUT = os.path.join(ROOT, "public", "data", "occurrences.json")
CREDS = "/home/franz/Documents/CodeProjs/gbif_credentials_complete.env"

MATCH_URL = "https://api.gbif.org/v1/species/match"
SEARCH_URL = "https://api.gbif.org/v1/occurrence/search"

MAX_PER_TAXON = 200        # cap records captured per taxon
PAGE_LIMIT = 300           # GBIF page size
RATE_LIMIT = 0.15          # seconds between requests
ATTRIBUTION = "GBIF.org occurrence download via occurrence/search API"


def read_email(path):
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("GBIF_EMAIL="):
                    return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return "noreply@example.org"


EMAIL = read_email(CREDS)
USER_AGENT = "tandayapa-interactions/1.0 (mailto:%s)" % EMAIL


def fetch_json(url, params):
    qs = urllib.parse.urlencode(params)
    full = "%s?%s" % (url, qs)
    req = urllib.request.Request(full, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def match_taxon(name):
    """Resolve usageKey via species/match. Strip trailing ' sp.' to genus."""
    q = name
    if q.endswith(" sp."):
        q = q[:-4].strip()
    data = fetch_json(MATCH_URL, {"name": q})
    key = data.get("usageKey")
    return key, data.get("matchType"), data.get("scientificName")


def fetch_occurrences(key):
    """Page occurrence/search, collect up to MAX_PER_TAXON compact points."""
    points = []
    offset = 0
    while len(points) < MAX_PER_TAXON:
        time.sleep(RATE_LIMIT)
        data = fetch_json(SEARCH_URL, {
            "taxonKey": key,
            "hasCoordinate": "true",
            "hasGeospatialIssue": "false",
            "limit": PAGE_LIMIT,
            "offset": offset,
        })
        results = data.get("results", [])
        if not results:
            break
        for rec in results:
            lat = rec.get("decimalLatitude")
            lng = rec.get("decimalLongitude")
            if lat is None or lng is None:
                continue
            points.append({
                "lat": round(float(lat), 5),
                "lng": round(float(lng), 5),
                "year": rec.get("year"),
                "basis": rec.get("basisOfRecord"),
                "country": rec.get("countryCode"),
            })
            if len(points) >= MAX_PER_TAXON:
                break
        if data.get("endOfRecords"):
            break
        offset += PAGE_LIMIT
    return points


def main():
    with open(INTERACTIONS) as f:
        interactions = json.load(f)

    names = set()
    for rec in interactions["records"]:
        names.add(rec["source"])
        names.add(rec["target"])
    names = sorted(names)
    print("Unique taxa: %d (UA mailto: %s)" % (len(names), EMAIL))

    out = {}
    total_points = 0
    with_occ = 0
    for i, name in enumerate(names, 1):
        try:
            time.sleep(RATE_LIMIT)
            key, mtype, sci = match_taxon(name)
            if not key:
                print("[%2d/%d] %-32s NO MATCH" % (i, len(names), name))
                out[name] = {"count": 0, "points": []}
                continue
            points = fetch_occurrences(key)
            out[name] = {"count": len(points), "points": points}
            total_points += len(points)
            if points:
                with_occ += 1
            print("[%2d/%d] %-32s key=%-9s match=%-6s -> %d pts"
                  % (i, len(names), name, key, mtype, len(points)))
        except Exception as e:  # noqa: BLE001 - per-taxon resilience
            print("[%2d/%d] %-32s ERROR: %s" % (i, len(names), name, e))
            out[name] = {"count": 0, "points": []}

    out["_meta"] = {
        "total_points": total_points,
        "taxa_with_occurrences": with_occ,
        "attribution": ATTRIBUTION,
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(out, f, separators=(",", ":"))

    size = os.path.getsize(OUT)
    print("\nDONE: %d taxa with occurrences / %d total points / %.2f MB"
          % (with_occ, total_points, size / 1e6))


if __name__ == "__main__":
    main()
