import os
import json
import yaml
import re
from pathlib import Path
from collections import defaultdict

# Configuration
RAW_DATA_DIR = Path("data/raw/eodhd")
OUTPUT_FILE = Path("manifests/securities/securities.yaml")

# MIC Mapping from quasar provider
EXCHANGE_MAP = {
    "NASDAQ": "XNAS",
    "NYSE": "XNYS",
    "NYSE ARCA": "ARCX",
    "NYSE MKT": "XASE"
}

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
    return directory / files[0][1]

def ingest_eodhd_securities():
    input_path = find_latest_file(RAW_DATA_DIR, r"us_securities_(\d{8})\.json")
    if not input_path:
        print(f"No matching files found in {RAW_DATA_DIR}")
        return

    print(f"Processing latest file: {input_path}")

    with open(input_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # --- STEP 1 & 2: Filter and Map ---
    # Group by (symbol, name) to ensure unique mappings
    unique_mappings = {}

    for entry in raw_data:
        isin = entry.get("Isin")
        # Filter: Entries must have an ISIN
        if not isin or isin == "Unknown":
            continue

        symbol = entry.get("Code")
        name = entry.get("Name")
        
        if not symbol or not name:
            continue

        # Map exchange using the MIC dictionary
        eodhd_exchange = entry.get("Exchange", "")
        exchange_mic = EXCHANGE_MAP.get(eodhd_exchange) # None if not in map

        # Create record
        record = {
            "isin": isin,
            "symbol": symbol,
            "name": name,
            "exchange": exchange_mic
        }

        # Deduplication: One unique (symbol, name) -> ISIN mapping
        # If multiple entries exist for the same (symbol, name), we keep the one 
        # that has a mapped exchange (priority to major exchanges)
        key = (symbol, name)
        if key not in unique_mappings:
            unique_mappings[key] = record
        else:
            # If current has a mapped exchange and existing doesn't, or if current ISIN is different?
            # User requirement: "There may only be one unique (symbol, name) -> ISIN mapping."
            # We'll stick to the first one found that has a MIC code, or just the first one.
            if unique_mappings[key]["exchange"] is None and record["exchange"] is not None:
                unique_mappings[key] = record

    # Convert back to list and sort by symbol
    final_records = list(unique_mappings.values())
    final_records.sort(key=lambda x: x["symbol"])

    # --- STEP 3: Save ---
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        yaml.dump(final_records, f, sort_keys=False, default_flow_style=False, allow_unicode=True)

    print(f"Successfully processed {len(final_records)} unique securities.")
    print(f"Manifest saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    ingest_eodhd_securities()

