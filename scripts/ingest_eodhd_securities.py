import os
import json
import yaml
import re
from pathlib import Path
from collections import defaultdict
from jsonschema import validate, ValidationError

# Configuration
RAW_DATA_DIR = Path("data/raw/eodhd")
OUTPUT_FILE = Path("manifests/securities/securities.yaml")
SCHEMA_FILE = Path("schemas/identity.schema.json")

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

def load_figi_mappings():
    """Load FIGI mappings from the latest cleaned ID mapping file."""
    input_path = find_latest_file(RAW_DATA_DIR, r"id_mapping_us_(\d{8})\.json")
    if not input_path:
        print("Warning: No cleaned ID mapping files found. FIGI lookups will be skipped.")
        return {}

    print(f"Loading FIGI mappings from: {input_path}")

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            mapping_data = json.load(f)

        # Create symbol -> FIGI mapping (strip .US suffix for compatibility)
        figi_map = {}
        for record in mapping_data:
            symbol = record.get('symbol')
            figi = record.get('figi')
            if symbol and figi and symbol.endswith('.US'):
                # Strip .US suffix to match securities data format
                clean_symbol = symbol[:-3]  # Remove .US
                figi_map[clean_symbol] = figi

        print(f"Loaded {len(figi_map):,} FIGI mappings")
        return figi_map

    except Exception as e:
        print(f"Error loading FIGI mappings: {e}")
        return {}

def ingest_eodhd_securities():
    input_path = find_latest_file(RAW_DATA_DIR, r"us_securities_(\d{8})\.json")
    if not input_path:
        print(f"No matching files found in {RAW_DATA_DIR}")
        return

    print(f"Processing latest file: {input_path}")

    # --- STEP 1: Load FIGI mappings ---
    figi_mappings = load_figi_mappings()

    with open(input_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # --- STEP 2: Filter and Map ---
    # Group by (symbol, name) to ensure unique mappings
    unique_mappings = {}

    for entry in raw_data:
        symbol = entry.get("Code")
        # Filter: Only process symbols that have FIGI mappings
        if symbol not in figi_mappings:
            continue
        name = entry.get("Name")
        
        if not symbol or not name:
            continue

        # Map exchange using the MIC dictionary
        eodhd_exchange = entry.get("Exchange", "")
        exchange_mic = EXCHANGE_MAP.get(eodhd_exchange) # None if not in map

        # Create record
        record = {
            "symbol": symbol,
            "name": name,
            "exchange": exchange_mic,
            "figi": figi_mappings[symbol]
        }

        # Deduplication: One unique (symbol, name) -> FIGI mapping
        # If multiple entries exist for the same (symbol, name), we keep the one
        # that has a mapped exchange (priority to major exchanges)
        key = (symbol, name)
        if key not in unique_mappings:
            unique_mappings[key] = record
        else:
            # If current has a mapped exchange and existing doesn't
            # User requirement: "There may only be one unique (symbol, name) -> FIGI mapping."
            # We'll stick to the first one found that has a MIC code, or just the first one.
            if unique_mappings[key]["exchange"] is None and record["exchange"] is not None:
                unique_mappings[key] = record

    # Convert back to list and sort by symbol
    final_records = list(unique_mappings.values())
    final_records.sort(key=lambda x: x["symbol"])

    # FIGI mappings are already added during record creation, and filtering ensures all records have FIGI

    # --- STEP 3: Validate schema ---
    print("Validating records against schema...")

    with open(SCHEMA_FILE, "r") as f:
        schema = json.load(f)

    validation_errors = 0
    validated_records = []

    for record in final_records:
        try:
            validate(instance=record, schema=schema)
            validated_records.append(record)
        except ValidationError as e:
            validation_errors += 1
            print(f"Schema validation error for {record.get('symbol', 'unknown')}: {e.message}")

    print(f"Schema validation: {len(validated_records):,} passed, {validation_errors:,} failed")

    final_records = validated_records

    # --- STEP 4: Save ---
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        yaml.dump(final_records, f, sort_keys=False, default_flow_style=False, allow_unicode=True)

    print(f"Successfully processed {len(final_records)} unique securities.")
    print(f"Manifest saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    ingest_eodhd_securities()

