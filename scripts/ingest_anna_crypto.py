import os
import csv
import re
import yaml
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict, deque
from jsonschema import validate, ValidationError

# Configuration
RAW_DATA_DIR = Path("data/raw/anna")
OUTPUT_FILE = Path("manifests/crypto/crypto.yaml")
SCHEMA_FILE = Path("schemas/identity.schema.json")

def find_latest_file(directory, pattern):
    """Find the latest dated file in a directory based on a regex pattern."""
    files = []
    regex = re.compile(pattern)
    
    if not directory.exists():
        return None

    for f in os.listdir(directory):
        match = regex.search(f)
        if match:
            date_str = match.group(1)
            files.append((date_str, f))
    
    if not files:
        return None
    
    files.sort(reverse=True)
    return files[0][1]

def parse_date(date_str):
    """Parse MM/DD/YY or MM/DD/YYYY to datetime for comparison."""
    if not date_str:
        return datetime.max
    try:
        if len(date_str.split('/')[-1]) == 2:
            return datetime.strptime(date_str, "%m/%d/%y")
        else:
            return datetime.strptime(date_str, "%m/%d/%Y")
    except ValueError:
        return datetime.max

def get_status_priority(status):
    """Return numeric priority for status. Lower is better/higher priority."""
    priorities = {
        "Validated": 1,
        "Provisional": 2,
        "Private": 3,
        "Reserved": 4
    }
    return priorities.get(status, 99)

def get_link_count(row):
    """Count the number of linked DTIs."""
    links = row.get("Linked DTI(s)", "")
    if not links:
        return 0
    return len(links.split(';'))

def ingest_anna_crypto():
    latest_filename = find_latest_file(RAW_DATA_DIR, r"ISIN-DTI-List-(\d{8})\.csv")
    if not latest_filename:
        print(f"No matching files found in {RAW_DATA_DIR}")
        return

    input_path = RAW_DATA_DIR / latest_filename
    print(f"Processing latest file: {input_path}")

    with open(SCHEMA_FILE, "r") as f:
        schema = json.load(f)

    # --- STEP 0: PRE-FILTER ---
    isin_groups = defaultdict(list)

    with open(input_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Type") != "Referential Instrument":
                continue
            if row.get("CFI") != "TMXXXX":
                continue
            status = row.get("DTI Status", "")
            if status in ["Private", "Reserved"]:
                continue
            isin = row.get("ISIN", "").strip()
            if not isin:
                continue
            isin_groups[isin].append(row)

    # --- STEP 1: ISIN-CENTRIC CONSOLIDATION ---
    intermediate_records = []
    for isin, group_rows in isin_groups.items():
        sorted_rows = sorted(group_rows, key=lambda x: (
            get_status_priority(x.get("DTI Status")),
            -get_link_count(x),
            parse_date(x.get("Added Date"))
        ))
        master_row = sorted_rows[0]
        
        all_aliases = set()
        for row in group_rows:
            for s in row.get("DTI Short Name", "").split(';'):
                if s.strip():
                    all_aliases.add(s.strip().upper())
            fisn = row.get("FISN", "")
            if '/' in fisn:
                fisn_sym = fisn.split('/')[-1].strip()
                if fisn_sym:
                    all_aliases.add(fisn_sym.upper())

        merged_symbols = ";".join(sorted(list(all_aliases)))
        
        intermediate_records.append({
            "isin": isin,
            "symbol": merged_symbols,
            "name": master_row.get("DTI Long Name", "").strip(),
            "exchange": None,
            "_status_pri": get_status_priority(master_row.get("DTI Status")),
            "_link_count": get_link_count(master_row),
            "_added_date": parse_date(master_row.get("Added Date"))
        })

    # --- STEP 2: ASSET-NAME CONSOLIDATION ---
    asset_name_groups = defaultdict(list)
    for rec in intermediate_records:
        primary_sym = rec["symbol"].split(';')[0].strip().upper()
        name = rec["name"].strip().lower()
        key = (primary_sym, name)
        asset_name_groups[key].append(rec)

    consolidated_by_name = []
    for key, group in asset_name_groups.items():
        sorted_group = sorted(group, key=lambda x: (
            x["_status_pri"],
            -x["_link_count"],
            x["_added_date"]
        ))
        winner = sorted_group[0]
        merged_aliases = set()
        for rec in group:
            for s in rec["symbol"].split(';'):
                merged_aliases.add(s.strip().upper())
        
        consolidated_by_name.append({
            "isin": winner["isin"],
            "symbol": ";".join(sorted(list(merged_aliases))),
            "name": winner["name"],
            "exchange": None,
            "_status_pri": winner["_status_pri"],
            "_link_count": winner["_link_count"],
            "_added_date": winner["_added_date"]
        })

    # --- STEP 3: ANY-SYMBOL OVERLAP PRUNING ---
    # Find connected components of records sharing ANY symbol
    # 1. Build adjacency list
    adj = defaultdict(set)
    sym_to_records = defaultdict(list)
    for i, rec in enumerate(consolidated_by_name):
        syms = rec["symbol"].split(';')
        for s in syms:
            sym_to_records[s].append(i)
    
    for records in sym_to_records.values():
        for i in range(len(records)):
            for j in range(i + 1, len(records)):
                adj[records[i]].add(records[j])
                adj[records[j]].add(records[i])
    
    # 2. Find components
    visited = [False] * len(consolidated_by_name)
    final_records = []
    
    for i in range(len(consolidated_by_name)):
        if not visited[i]:
            component = []
            queue = deque([i])
            visited[i] = True
            while queue:
                curr = queue.popleft()
                component.append(consolidated_by_name[curr])
                for neighbor in adj[curr]:
                    if not visited[neighbor]:
                        visited[neighbor] = True
                        queue.append(neighbor)
            
            # Resolve winner for the component
            # Authority: Highest Links > 1, then Seniority, then Status
            sorted_component = sorted(component, key=lambda x: (
                -1 if x["_link_count"] > 1 else 0,
                x["_added_date"],
                x["_status_pri"]
            ))
            
            winner = sorted_component[0]
            
            # Use ONLY the winner's data (no pollution from losers)
            winner_aliases = set(winner["symbol"].split(';'))
            
            # Sort aliases by length (shortest first), then alphabetically
            sorted_aliases = sorted(list(winner_aliases), key=lambda x: (len(x), x))
            
            final_records.append({
                "isin": winner["isin"],
                "symbol": ";".join(sorted_aliases),
                "name": winner["name"],
                "exchange": None
            })

    # --- STEP 4: FINAL VALIDATION & SAVE ---
    # Final sort of list
    final_records.sort(key=lambda x: x["symbol"].lower())

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        yaml.dump(final_records, f, sort_keys=False, default_flow_style=False, allow_unicode=True)

    print(f"Total Unique ISINs (Step 1): {len(intermediate_records)}")
    print(f"Consolidated Assets (Step 2): {len(consolidated_by_name)}")
    print(f"Final Overlap-Pruned Assets (Step 3): {len(final_records)}")
    print(f"Successfully saved manifest to {OUTPUT_FILE}")

if __name__ == "__main__":
    ingest_anna_crypto()
