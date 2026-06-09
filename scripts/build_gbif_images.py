#!/usr/bin/env python3
"""Build public/data/species_images.json: up to N representative GBIF images per taxon,
prioritising citizen-science OBSERVATIONS (iNaturalist / HUMAN_OBSERVATION) over museum
PRESERVED_SPECIMEN images (mirrors ithomiini_maps' source ranking).

Reads src/data/interactions.json + interactions_ephi.json. Stdlib only (urllib).
Output shape:  { "<taxon>": { "images": [ {image_url, original_url, license, creator,
                 attribution, source_url, basis, source}, ... ] }, ... }
Idempotent / incremental: taxa that already have an "images" array are skipped.
"""
import json, os, time, urllib.request, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGES_PATH = os.path.join(ROOT, "public", "data", "species_images.json")
ATTR_PATH = os.path.join(ROOT, "public", "data", "gbif_attribution.json")
INATURALIST_DATASET_KEY = "50c9509d-22c7-4a22-a47d-8c48425ef4a7"
UA = "tandayapa-interactions/0.2 (mailto:fchandi@estud.usfq.edu.ec)"
MAX_IMAGES = 6

CLASS_HINT = {
    "hummingbird": ("class", "Aves"), "bird": ("class", "Aves"),
    "bat": ("class", "Mammalia"), "mammal": ("class", "Mammalia"),
    "insect": ("class", "Insecta"), "plant": ("kingdom", "Plantae"),
}


def http_json(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except Exception:
        return None


def collect_taxa(records):
    taxa = {}
    for r in records:
        for who, grp in ((r["source"], r["sourceGroup"]), (r["target"], r["targetGroup"])):
            taxa.setdefault(who, grp)
    return taxa


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


def source_of(occ):
    dk = (occ.get("datasetKey") or "")
    inst = (occ.get("institutionCode") or "").lower()
    if dk == INATURALIST_DATASET_KEY or inst == "inaturalist":
        return "iNaturalist"
    return "GBIF"


def rank_key(c):
    # observations first, museum specimens last; iNaturalist gets the top slot
    basis = c.get("basis") or ""
    score = 0
    if c["source"] == "iNaturalist":
        score -= 2
    if basis == "HUMAN_OBSERVATION":
        score -= 1
    if basis in ("PRESERVED_SPECIMEN", "MATERIAL_SAMPLE", "MATERIAL_CITATION", "FOSSIL_SPECIMEN"):
        score += 3
    return score


def proxy(url):
    return "https://wsrv.nl/?url=%s&w=480&output=webp" % urllib.parse.quote(url, safe="")


def attribution(c):
    who = c.get("creator") or c.get("rightsHolder")
    bits = []
    if who:
        bits.append("© " + who)
    if c.get("source") == "iNaturalist":
        bits.append("iNaturalist")
    elif c.get("publisher"):
        bits.append(c["publisher"])
    if c.get("license"):
        lic = c["license"].rsplit("/", 2)
        bits.append("(%s)" % ("/".join([p for p in lic if p][-2:]) if "creativecommons" in c["license"] else c["license"]))
    return " ".join(bits).strip() or "Image via GBIF"


def fetch_images(key):
    candidates, seen = [], set()
    # two passes: observations first, then a general pass to top up
    passes = [
        {"taxonKey": key, "mediaType": "StillImage", "basisOfRecord": "HUMAN_OBSERVATION", "limit": "40"},
        {"taxonKey": key, "mediaType": "StillImage", "limit": "40"},
    ]
    for q in passes:
        d = http_json("https://api.gbif.org/v1/occurrence/search?" + urllib.parse.urlencode(q))
        if not d:
            continue
        for occ in d.get("results", []):
            src = source_of(occ)
            basis = occ.get("basisOfRecord")
            for m in occ.get("media", []):
                if m.get("type") != "StillImage":
                    continue
                url = m.get("identifier")
                fmt = m.get("format") or ""
                if not url or url in seen or not fmt.startswith("image/"):
                    continue
                seen.add(url)
                candidates.append({
                    "original_url": url,
                    "image_url": proxy(url),
                    "license": m.get("license") or occ.get("license"),
                    "creator": m.get("creator"),
                    "rightsHolder": m.get("rightsHolder") or occ.get("rightsHolder"),
                    "publisher": m.get("publisher") or occ.get("publisher"),
                    "basis": basis,
                    "source": src,
                    "source_url": occ.get("references") or ("https://www.gbif.org/occurrence/%s" % occ.get("gbifID")),
                })
        time.sleep(0.15)
    candidates.sort(key=rank_key)
    out = []
    for c in candidates[:MAX_IMAGES]:
        c["attribution"] = attribution(c)
        c.pop("rightsHolder", None)
        out.append(c)
    return out


def main():
    records = []
    for rel in ("interactions.json", "interactions_ephi.json", "interactions_papers.json", "interactions_ithomiini.json", "interactions_frugivory.json", "interactions_bats.json", "interactions_candidates.json", "interactions_extra.json"):
        p = os.path.join(ROOT, "src", "data", rel)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                records += json.load(f).get("records", [])
    taxa = collect_taxa(records)
    print("Collected %d unique taxa." % len(taxa))

    images = {}
    if os.path.exists(IMAGES_PATH):
        try:
            with open(IMAGES_PATH, encoding="utf-8") as f:
                images = json.load(f)
        except Exception:
            images = {}

    n_done = 0
    for name, group in taxa.items():
        if isinstance(images.get(name), dict) and images[name].get("images"):
            continue  # already in the new multi-image shape
        try:
            key = resolve_key(name, group)
            if not key:
                print("MISS %s (no match)" % name); continue
            imgs = fetch_images(key)
            if not imgs:
                print("MISS %s (no image)" % name); continue
            images[name] = {"images": imgs}
            n_done += 1
            print("OK   %s -> %d imgs (%s)" % (name, len(imgs), imgs[0]["source"]))
        except Exception as e:
            print("ERR  %s: %s" % (name, e))
        if n_done % 20 == 0 and n_done:
            with open(IMAGES_PATH, "w", encoding="utf-8") as f:
                json.dump(images, f, ensure_ascii=False, indent=0)

    with open(IMAGES_PATH, "w", encoding="utf-8") as f:
        json.dump(images, f, ensure_ascii=False, indent=0)
    with open(ATTR_PATH, "w", encoding="utf-8") as f:
        json.dump({"note": "Taxon images from GBIF (https://www.gbif.org), each under its own CC "
                   "license; observations (iNaturalist) prioritised over museum specimens."}, f, indent=2)
    n_with = sum(1 for v in images.values() if isinstance(v, dict) and v.get("images"))
    print("DONE: %d/%d taxa have images." % (n_with, len(taxa)))


if __name__ == "__main__":
    main()
