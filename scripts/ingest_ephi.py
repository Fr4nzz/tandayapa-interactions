#!/usr/bin/env python3
"""Ingest the Duchenne/EPHI plant-hummingbird interaction dataset into our edge-list schema.

Source: Duchenne et al. 2022, Dryad doi:10.5061/dryad.vhhmgqnvw
        "Ecuadorian Plant-Hummingbird interactions over an elevation gradient in the
        Andes, sampled with camera traps in 11 localities."
        (Dryad download is bearer-token gated; the identical file — verified by
         SHA-256 a0f7705e... — is mirrored on Zenodo record 7056230.)

Real file: data_for_modelo2.txt  (CSV, comma-delimited, UTF-8)
Real header (verified from the file, NOT assumed):
    plant,hummingbird,site,y,m,date,latitude,longitude,elev,mnumb,nsampl,value

Each input row is one camera-trap observation on a given date. `value` is the number
of recorded interactions for that (plant, hummingbird, site, date). We collapse to one
edge per unique (hummingbird, plant, site) triple — the natural interaction granularity
(1,686 valid triples; the dataset's headline ~1,690 includes 4 rows with a BLANK plant
name, which carry no plant identity and are therefore skipped — see SKIPPED note below).

Output edge schema (one record per (hummingbird, plant, site)):
    source       : hummingbird (scientific name, verbatim)
    sourceGroup  : 'hummingbird'
    target       : plant (scientific name, verbatim)
    targetGroup  : 'plant'
    type         : 'visitsFlowersOf'
    evidence     : 'camera trap (EPHI)'
    locality     : cleaned site name
    scope        : 'nearby reserve'
    elevation_m  : integer site elevation (matches existing interactions.json convention)
    ref          : 'Duchenne et al. 2022 (EPHI, Dryad)'
    certainty    : 'verified'

We emit ONLY pairs that actually appear in the file. Nothing is inferred or fabricated.
"""
import argparse
import csv
import json
import os
from collections import defaultdict

DOI = "10.5061/dryad.vhhmgqnvw"
REF = "Duchenne et al. 2022 (EPHI, Dryad)"
SOURCE_TITLE = (
    "Ecuadorian Plant-Hummingbird interactions over an elevation gradient in the "
    "Andes, sampled with camera traps in 11 localities (Duchenne et al. 2022, EPHI)"
)

# Cosmetic cleanup of the raw `site` tokens into human-readable localities.
# Keys are the verbatim values found in the file; anything not listed is title-cased
# / de-camelCased on the fly. We do NOT merge distinct sites.
SITE_NAMES = {
    "Alaspungo": "Alaspungo",
    "LasGralarias": "Las Gralarias",
    "Maquipucuna": "Maquipucuna",
    "MashpiLaguna": "Mashpi Laguna",
    "Mashpi_Capuchin": "Mashpi Capuchin",
    "Sachatamia": "Sachatamia",
    "SantaLuciaLower": "Santa Lucia (Lower)",
    "SantaLuciaUpper": "Santa Lucia (Upper)",
    "UnPocoChoco": "Un Poco del Chocó",
    "Verdecocha": "Verdecocha",
    "Yanacocha": "Yanacocha",
}


def clean_site(raw):
    raw = raw.strip()
    if raw in SITE_NAMES:
        return SITE_NAMES[raw]
    # Fallback: split camelCase / underscores into spaced words.
    import re
    s = raw.replace("_", " ")
    s = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s)
    return s.strip()


def parse(infile):
    """Return (records, stats). One record per unique (hummingbird, plant, site)."""
    # accumulate per triple so we can carry summed interaction counts + elevation
    agg_value = defaultdict(int)        # triple -> summed `value`
    agg_obs = defaultdict(int)          # triple -> number of source rows
    site_raw = {}                       # triple -> raw site token
    elev = {}                           # raw site -> elevation int
    skipped_blank_plant = 0
    skipped_blank_hb = 0
    total_rows = 0

    with open(infile, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        required = {"plant", "hummingbird", "site"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(
                f"ERROR: input file missing expected columns {missing}; "
                f"found header: {reader.fieldnames}"
            )
        for row in reader:
            total_rows += 1
            plant = (row.get("plant") or "").strip()
            hb = (row.get("hummingbird") or "").strip()
            site = (row.get("site") or "").strip()
            if not plant:
                skipped_blank_plant += 1
                continue
            if not hb:
                skipped_blank_hb += 1
                continue
            triple = (hb, plant, site)
            site_raw[triple] = site
            try:
                agg_value[triple] += int(float(row.get("value") or 0))
            except ValueError:
                pass
            agg_obs[triple] += 1
            # elevation is constant per site in this dataset; record first seen
            if site not in elev:
                try:
                    elev[site] = int(round(float(row.get("elev"))))
                except (TypeError, ValueError):
                    pass

    records = []
    for triple in sorted(agg_value):
        hb, plant, site = triple
        rec = {
            "source": hb,
            "sourceGroup": "hummingbird",
            "target": plant,
            "targetGroup": "plant",
            "type": "visitsFlowersOf",
            "evidence": "camera trap (EPHI)",
            "locality": clean_site(site),
            "scope": "nearby reserve",
            "ref": REF,
            "certainty": "verified",
        }
        if site in elev:
            rec["elevation_m"] = elev[site]
        records.append(rec)

    stats = {
        "total_data_rows": total_rows,
        "skipped_blank_plant": skipped_blank_plant,
        "skipped_blank_hummingbird": skipped_blank_hb,
        "unique_edges": len(records),
        "n_sites": len({site_raw[t] for t in site_raw}),
        "n_hummingbirds": len({t[0] for t in agg_value}),
        "n_plants": len({t[1] for t in agg_value}),
        "total_interactions_summed": sum(agg_value.values()),
    }
    return records, stats


def main():
    ap = argparse.ArgumentParser(description="Ingest EPHI Dryad dataset into edge-list schema")
    ap.add_argument("-i", "--infile", default="/tmp/ephi_data/data_for_modelo2.txt",
                    help="path to data_for_modelo2.txt")
    ap.add_argument("-o", "--out", default="src/data/interactions_ephi.json")
    a = ap.parse_args()

    records, stats = parse(a.infile)

    out = {
        "_meta": {
            "source": SOURCE_TITLE,
            "doi": DOI,
            "dryad_url": f"https://doi.org/{DOI}",
            "mirror": "Zenodo record 7056230 (identical file, SHA-256 a0f7705e21dca0b3ec8b107c20ffb42206b0efaeabaa82c3600b14605c99b6a3)",
            "ref": REF,
            "data_file": "data_for_modelo2.txt",
            "columns_found": ["plant", "hummingbird", "site", "y", "m", "date",
                              "latitude", "longitude", "elev", "mnumb", "nsampl", "value"],
            "edge_rule": "one edge per unique (hummingbird, plant, site); only pairs present in the file",
            "n_records": stats["unique_edges"],
            "stats": stats,
        },
        "records": records,
    }

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print(json.dumps(stats, indent=2))
    print(f"wrote {stats['unique_edges']} edges -> {a.out}")


if __name__ == "__main__":
    main()
