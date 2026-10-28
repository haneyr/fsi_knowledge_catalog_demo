#!/usr/bin/env python3
"""Batched Phase P4 Governance Verification for alitch-ca-demo."""
import os
import sys
sys.path.insert(0, "scripts")
os.environ.setdefault("GOOGLE_API_USE_CLIENT_CERTIFICATE", "false")
os.environ.setdefault("CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE", "false")

from common import load_config, api_call, DATAPLEX_URL, LINEAGE_URL

def paginate(url, key):
    items = []
    page_token = None
    while True:
        u = f"{url}{'&' if '?' in url else '?'}pageSize=100"
        if page_token:
            u += f"&pageToken={page_token}"
        resp = api_call(u, "GET")
        items.extend(resp.get(key, []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return items

def main():
    cfg = load_config()
    pid = cfg["project_id"]
    print(f"=== Phase P4 Governance Verification ({pid}) ===")

    # 1. Entry Types (global)
    ets = paginate(f"{DATAPLEX_URL}/projects/{pid}/locations/global/entryTypes", "entryTypes")
    retail_ets = [e for e in ets if "/retail-" in e["name"]]
    print(f"1. Custom Entry Types (global): {len(retail_ets)} (expected 9)")

    # 2. Aspect Types (global)
    ats = paginate(f"{DATAPLEX_URL}/projects/{pid}/locations/global/aspectTypes", "aspectTypes")
    retail_ats = [a for a in ats if "/retail-" in a["name"]]
    print(f"2. Custom + Marker Aspect Types (global): {len(retail_ats)} (expected 14: 7 custom + 7 marker)")

    # 3. Entry Groups, Source Entries & Rule Library (us)
    egs = paginate(f"{DATAPLEX_URL}/projects/{pid}/locations/us/entryGroups", "entryGroups")
    retail_egs = [g for g in egs if "/retail-" in g["name"]]
    src_entries = 0
    rule_entries = 0
    for g in ["retail-orion-store-pos", "retail-lumen-commerce-loyalty", "retail-helios-merch-supply", "retail-rule-library-global"]:
        loc = "global" if g == "retail-rule-library-global" else "us"
        es = paginate(f"{DATAPLEX_URL}/projects/{pid}/locations/{loc}/entryGroups/{g}/entries", "entries")
        if g == "retail-rule-library-global":
            rule_entries = len(es)
        else:
            src_entries += len(es)
    print(f"3. Custom Source Entry Groups (us): {len([g for g in retail_egs if 'rule' not in g['name']])} groups, {src_entries} source entries (3 instances + 3 schemas + 13 tables = 19)")

    # 4. Glossary (us)
    glossaries = paginate(f"{DATAPLEX_URL}/projects/{pid}/locations/us/glossaries", "glossaries")
    gid = glossaries[0]["name"].split("/")[-1]
    cats = paginate(f"{DATAPLEX_URL}/projects/{pid}/locations/us/glossaries/{gid}/categories", "categories")
    terms = paginate(f"{DATAPLEX_URL}/projects/{pid}/locations/us/glossaries/{gid}/terms", "terms")
    print(f"4. Business Glossary (us, {gid} - '{glossaries[0].get('displayName')}'): {len(cats)} categories (expected 28), {len(terms)} terms (expected 84)")

    # 5. Data Products (us)
    dps = paginate(f"{DATAPLEX_URL}/projects/{pid}/locations/us/dataProducts", "dataProducts")
    retail_dps = [d for d in dps if "/retail-" in d["name"]]
    print(f"5. Data Products (us): {len(retail_dps)} ({[d['name'].split('/')[-1] for d in retail_dps]})")

    # 6. Lineage Processes (us)
    procs = paginate(f"{LINEAGE_URL}/projects/{pid}/locations/us/processes", "processes")
    print(f"6. Lineage Processes (us): {len(procs)} processes (125 links logged)")

    # 7. Rule Library Templates (us)
    print(f"7. Rule Library Templates (retail-rule-library): {rule_entries} (expected 10)")

    # 8. DataScans (us-central1)
    scans = paginate(f"{DATAPLEX_URL}/projects/{pid}/locations/us-central1/dataScans", "dataScans")
    retail_scans = [s for s in scans if "/retail-" in s["name"]]
    prof = [s for s in retail_scans if s["name"].endswith("-profile")]
    ins = [s for s in retail_scans if s["name"].endswith("-insights")]
    qual = [s for s in retail_scans if s["name"].endswith("-quality")]
    print(f"8. DataScans (us-central1): {len(retail_scans)} total ({len(prof)} profile, {len(ins)} insights, {len(qual)} quality)")

    # 9. Policy Tag Taxonomy (us)
    tax = api_call(f"https://datacatalog.googleapis.com/v1/projects/{pid}/locations/us/taxonomies", "GET").get("taxonomies", [])
    print(f"9. Policy Tag Taxonomies (us): {len(tax)} ({[t.get('displayName') for t in tax]})")

if __name__ == "__main__":
    main()
