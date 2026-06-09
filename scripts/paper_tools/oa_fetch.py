#!/usr/bin/env python3
"""OA-only paper fetcher. Given a DOI, searches legitimate open-access sources
(Unpaywall -> OpenAlex -> Europe PMC -> Crossref -> Dryad/Zenodo) for a PDF/dataset
and optionally downloads it. No Sci-Hub / no paywall bypass.

Usage:
    python scripts/paper_tools/oa_fetch.py 10.1098/rspb.2022.0064
    python scripts/paper_tools/oa_fetch.py 10.5061/dryad.vhhmgqnvw -o papers/ --download

Contact email (required by Unpaywall/OpenAlex polite pool) is read from
UNPAYWALL_EMAIL or GBIF_EMAIL in the environment or a local .env file.
"""
import argparse, os, sys, json, re
from pathlib import Path
from urllib.parse import quote
import urllib.request

UA = "tandayapa-interactions-oa-fetch/0.1 (mailto:%s)"


def load_email() -> str:
    if os.environ.get("UNPAYWALL_EMAIL"):
        return os.environ["UNPAYWALL_EMAIL"].strip()
    if os.environ.get("GBIF_EMAIL"):
        return os.environ["GBIF_EMAIL"].strip()
    for cand in [Path(".env"), Path(".env.example")]:
        if cand.exists():
            for line in cand.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    if k.strip() in ("UNPAYWALL_EMAIL", "GBIF_EMAIL") and v.strip():
                        return v.strip()
    return ""


def _get(url, email=""):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA % (email or "anon")})
        with urllib.request.urlopen(req, timeout=25) as r:
            if r.status == 200:
                return r.read()
    except Exception:
        pass
    return None


def _json(url, email=""):
    b = _get(url, email)
    if not b:
        return None
    try:
        return json.loads(b)
    except Exception:
        return None


def from_unpaywall(doi, email):
    d = _json(f"https://api.unpaywall.org/v2/{doi}?email={quote(email)}", email)
    if not d:
        return None
    # Only accept a direct PDF; a bare landing-page URL is not useful, and
    # letting it through would shadow better sources (e.g. Europe PMC) downstream.
    loc = d.get("best_oa_location") or {}
    if loc.get("url_for_pdf"):
        return ("unpaywall", loc["url_for_pdf"])
    for l in d.get("oa_locations") or []:
        c = (l or {}).get("url_for_pdf")
        if c:
            return ("unpaywall", c)
    return None


def from_openalex(doi, email):
    d = _json(f"https://api.openalex.org/works/https://doi.org/{doi}?mailto={quote(email)}", email)
    if not d:
        return None
    for c in [(d.get("best_oa_location") or {}).get("pdf_url"),
              (d.get("primary_location") or {}).get("pdf_url"),
              (d.get("open_access") or {}).get("oa_url")]:
        if c and c.lower().endswith(".pdf"):
            return ("openalex", c)
    return None


def from_europepmc(doi):
    d = _json("https://www.ebi.ac.uk/europepmc/webservices/rest/search?"
              f"query=DOI:{quote(doi)}&format=json&resultType=core")
    if not d:
        return None
    res = (d.get("resultList") or {}).get("result") or []
    if not res:
        return None
    for u in (res[0].get("fullTextUrlList") or {}).get("fullTextUrl") or []:
        if u.get("documentStyle") == "pdf" and u.get("availabilityCode") == "OA":
            return ("europepmc", u["url"])
    return None


def from_crossref(doi, email):
    d = _json(f"https://api.crossref.org/works/{quote(doi)}?mailto={quote(email)}", email)
    if not d:
        return None
    for l in (d.get("message") or {}).get("link") or []:
        if l.get("content-type") == "application/pdf":
            return ("crossref", l["URL"])
    return None


def from_dryad(doi):
    if "dryad" not in doi.lower():
        return None
    enc = quote(f"doi:{doi}", safe="")
    d = _json(f"https://datadryad.org/api/v2/datasets/{enc}")
    if not d:
        return None
    href = ((d.get("_links") or {}).get("stash:download") or {}).get("href")
    if href:
        return ("dryad", "https://datadryad.org" + href)  # ZIP, not PDF
    return None


def resolve(doi, email):
    doi = doi.strip().lower().replace("https://doi.org/", "")
    chain = [
        from_unpaywall(doi, email) if email else None,
        from_openalex(doi, email or "anon@example.com"),
        from_europepmc(doi),
        from_crossref(doi, email or "anon@example.com"),
        from_dryad(doi),
    ]
    for hit in chain:
        if hit:
            return hit
    return None


def main():
    ap = argparse.ArgumentParser(description="OA-only DOI -> PDF/dataset resolver")
    ap.add_argument("doi")
    ap.add_argument("-o", "--out", default="papers")
    ap.add_argument("--download", action="store_true")
    a = ap.parse_args()

    email = load_email()
    if not email:
        print("WARN: no UNPAYWALL_EMAIL/GBIF_EMAIL found; Unpaywall step skipped.", file=sys.stderr)

    hit = resolve(a.doi, email)
    if not hit:
        print(json.dumps({"doi": a.doi, "oa_pdf_url": None, "status": "no_oa_source"}))
        sys.exit(1)

    src, url = hit
    print(json.dumps({"doi": a.doi, "source": src, "oa_pdf_url": url}))

    if a.download:
        Path(a.out).mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^\w.-]", "_", a.doi)
        body = _get(url, email)
        if not body:
            print("download failed", file=sys.stderr)
            sys.exit(2)
        ext = ".zip" if src == "dryad" else ".pdf"
        dest = Path(a.out) / f"{slug}{ext}"
        dest.write_bytes(body)
        print(f"saved -> {dest} ({len(body)} bytes)")


if __name__ == "__main__":
    main()
