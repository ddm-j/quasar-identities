import csv
import os
import yaml
import json
from pathlib import Path
from jsonschema import validate, ValidationError

# Configuration
RAW_DATA_DIR = Path("data/raw/kaiko")
ANNA_DATA_FILE = Path("data/processed/anna/crypto_anna.yaml")
OUTPUT_FILE = Path("manifests/crypto/crypto.yaml")  # Canonical crypto manifest
SCHEMA_FILE = Path("schemas/identity.schema.json")

def find_latest_file(directory, pattern):
    """Find the latest dated file in a directory based on a regex pattern."""
    files = []
    regex_pattern = f"{pattern}\\d{{8}}\\.csv"

    if not directory.exists():
        return None

    for f in os.listdir(directory):
        if f.startswith(pattern) and f.endswith('.csv'):
            # Extract date from filename
            date_str = f.replace(pattern, '').replace('.csv', '')
            if len(date_str) == 8 and date_str.isdigit():
                files.append((date_str, f))

    if not files:
        return None

    files.sort(reverse=True)
    return directory / files[0][1]

def ingest_kaiko_crypto():
    """Ingest Kaiko crypto FIGI data and create manifest."""
    input_path = find_latest_file(RAW_DATA_DIR, "kaiko_asset_figi_")
    if not input_path:
        print(f"No matching files found in {RAW_DATA_DIR}")
        return

    print(f"Processing latest file: {input_path}")

    # Load schema for validation
    with open(SCHEMA_FILE, "r") as f:
        schema = json.load(f)

    # Load ANNA data for ISIN-based enrichment
    print("Loading ANNA data for enrichment...")
    anna_data = []
    try:
        with open(ANNA_DATA_FILE, 'r', encoding='utf-8') as f:
            import yaml as yaml_module
            anna_data = yaml_module.safe_load(f)
        print(f"Loaded {len(anna_data)} ANNA records for enrichment")
    except Exception as e:
        print(f"Warning: Could not load ANNA data for enrichment: {e}")
        anna_data = []

    # Create ISIN lookup for ANNA enrichment
    anna_by_isin = {}
    for record in anna_data:
        isin = record.get('isin')
        if isin:
            anna_by_isin[isin] = record

    print(f"ANNA ISIN lookup: {len(anna_by_isin)} records available for enrichment")

    records = []

    try:
        with open(input_path, 'r', encoding='utf-8-sig') as f:  # utf-8-sig handles BOM
            # Read the header line and clean it
            header_line = f.readline().strip()
            # Remove BOM and quotes from headers
            headers = [col.strip('"').lstrip('\ufeff') for col in header_line.split(',')]
            reader = csv.DictReader(f, fieldnames=headers)

            for row in reader:
                figi = row.get('FIGI Code', '').strip()
                isin = row.get('ISIN', '').strip()
                symbol = row.get('Code', '').strip()
                name = row.get('Asset Name', '').strip()

                # Filter: Must have FIGI, symbol, name and be cryptocurrency
                # (Keep existing filtering for schema compatibility)
                if not figi or not symbol or not name:
                    continue

                if row.get('Asset Class', '').strip() != 'cryptocurrency':
                    continue

                # Create base record
                record = {
                    "figi": figi,
                    "symbol": symbol.upper(),  # Convert to uppercase
                    "name": name,
                    "exchange": None
                }

                # ISIN-based enrichment with ANNA data
                if isin and isin in anna_by_isin:
                    anna_record = anna_by_isin[isin]

                    # Get all unique aliases from both sources
                    kaiko_aliases = {record['symbol']}  # Kaiko has single symbol
                    anna_aliases = set(alias.strip().upper() for alias in anna_record['symbol'].split(';'))

                    # Combine and deduplicate all aliases
                    all_aliases = kaiko_aliases | anna_aliases

                    if len(all_aliases) > 1:  # Only enrich if we actually add aliases
                        # Update the symbol field with semicolon-separated aliases
                        record['symbol'] = ';'.join(sorted(all_aliases))
                        print(f"Enriched {record['symbol']} (added {len(all_aliases) - 1} aliases from ANNA)")

                records.append(record)

    except Exception as e:
        print(f"Error reading file: {e}")
        return

    print(f"Loaded {len(records):,} crypto records with FIGI")

    # Deduplication: Keep first occurrence of each symbol
    seen_symbols = set()
    deduplicated_records = []

    for record in records:
        symbol = record["symbol"]
        if symbol not in seen_symbols:
            seen_symbols.add(symbol)
            deduplicated_records.append(record)

    duplicate_count = len(records) - len(deduplicated_records)
    print(f"Removed {duplicate_count:,} duplicate symbol records")
    print(f"Remaining {len(deduplicated_records):,} unique crypto assets")

    # Schema validation
    print("Validating records against schema...")

    validation_errors = 0
    validated_records = []

    for record in deduplicated_records:
        try:
            validate(instance=record, schema=schema)
            validated_records.append(record)
        except ValidationError as e:
            validation_errors += 1
            print(f"Schema validation error for {record.get('symbol', 'unknown')}: {e.message}")

    print(f"Schema validation: {len(validated_records):,} passed, {validation_errors:,} failed")

    # Save manifest
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    import yaml
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        yaml.dump(validated_records, f, sort_keys=False, default_flow_style=False, allow_unicode=True)

    print(f"Successfully processed {len(validated_records)} unique crypto assets.")
    print(f"Manifest saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    import json
    ingest_kaiko_crypto()
