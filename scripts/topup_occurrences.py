#!/usr/bin/env python3
"""Incremental occurrence top-up via the anonymous GBIF occurrence/search API (fast, no creds).
Keeps the existing citable Download-API occurrences and ADDS only taxa that are missing
(e.g. the newly ingested Tinoco taxa), using the same regional Andes-Chocó bbox. Stdlib only.
"""
import json, os, time, urllib.request, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OCC = os.path.join(ROOT, "public", "data", "occurrences.json")
UA = "tandayapa-interactions/0.3 (mailto:fchandi@estud.usfq.edu.ec)"
BBOX = {"decimalLatitude": "-6,3", "decimalLongitude": "-82,-74"}
CLASS_HINT = {"hummingbird": ("class", "Aves"), "bird": ("class", "Aves"),
              "bat": ("class", "Mammalia"), "mammal": ("class", "Mammalia"),
              "insect": ("class", "Insecta"), "plant": ("kingdom", "Plantae")}


def http_json(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except Exception:
        return None


def resolve_key(name, group):
    q = {"name": name[:-4] if name.endswith(" sp.") else name, "strict": "false", "verbose": "true"}
    if name.endswith(" sp."):
        q["rank"] = "GENUS"
    hint = CLASS_HINT.get(group)
    if hint:
        q[hint[0]] = hint[1]
    d = http_json("https://api.gbif.org/v1/species/match?" + urllib.parse.urlencode(q))
    if not d or d.get("matchType") == "NONE":
        return None
    return d.get("usageKey") or d.get("acceptedUsageKey")


def fetch_points(key, cap=250):
    pts, seen, offset = [], set(), 0
    while len(pts) < cap:
        q = {"taxonKey": key, "hasCoordinate": "true", "hasGeospatialIssue": "false",
             "occurrenceStatus": "PRESENT", "limit": "300", "offset": str(offset), **BBOX}
        d = http_json("https://api.gbif.org/v1/occurrence/search?" + urllib.parse.urlencode(q))
        if not d:
            break
        for o in d.get("results", []):
            la, lo = o.get("decimalLatitude"), o.get("decimalLongitude")
            if la is None or lo is None:
                continue
            k = (round(la, 5), round(lo, 5))
            if k in seen:
                continue
            seen.add(k)
            pts.append({"lat": la, "lng": lo, "year": o.get("year") or "",
                        "basis": o.get("basisOfRecord"), "country": o.get("countryCode")})
            if len(pts) >= cap:
                break
        if d.get("endOfRecords") or not d.get("results"):
            break
        offset += 300
        time.sleep(0.15)
    return pts


def main():
    occ = json.load(open(OCC, encoding="utf-8")) if os.path.exists(OCC) else {"_meta": {}}
    taxa = {}
    for rel in ("interactions.json", "interactions_ephi.json", "interactions_papers.json", "interactions_ithomiini.json", "interactions_frugivory.json", "interactions_bats.json"):
        p = os.path.join(ROOT, "src", "data", rel)
        if os.path.exists(p):
            for r in json.load(open(p, encoding="utf-8")).get("records", []):
                taxa.setdefault(r["source"], r["sourceGroup"])
                taxa.setdefault(r["target"], r["targetGroup"])

    missing = [t for t in taxa if t not in occ]
    print("missing taxa:", len(missing))
    added = 0
    for name in missing:
        try:
            key = resolve_key(name, taxa[name])
            if not key:
                print("MISS", name, "(no match)"); continue
            pts = fetch_points(key)
            if pts:
                occ[name] = {"count": len(pts), "points": pts}
                added += 1
                print("OK  ", name, "->", len(pts), "pts")
            else:
                print("MISS", name, "(no occ in bbox)")
        except Exception as e:
            print("ERR ", name, e)

    ks = [k for k in occ if not k.startswith("_")]
    occ["_meta"]["total_points"] = sum(len(occ[k]["points"]) for k in ks)
    occ["_meta"]["taxa_with_occurrences"] = len(ks)
    note = occ["_meta"].get("note", "")
    if "occurrence/search" not in note:
        occ["_meta"]["note"] = (note + " Additional taxa topped up via the anonymous GBIF "
                                "occurrence/search API (same regional bbox).").strip()
    json.dump(occ, open(OCC, "w", encoding="utf-8"), ensure_ascii=False)
    print("DONE: added %d taxa; %d taxa / %d points total." % (added, len(ks), occ["_meta"]["total_points"]))


if __name__ == "__main__":
    main()
