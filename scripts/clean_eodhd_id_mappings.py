import json
import os
from datetime import datetime
from pathlib import Path

# Configuration
RAW_DATA_DIR = Path("data/raw/eodhd")

def find_latest_raw_file(directory, pattern="id_mapping_us_raw_"):
    """Find the latest raw ID mapping file."""
    files = []
    regex_pattern = f"{pattern}\\d{{8}}\\.json"

    if not directory.exists():
        return None

    for f in os.listdir(directory):
        if f.startswith(pattern) and f.endswith('.json'):
            # Extract date from filename
            date_str = f.replace(pattern, '').replace('.json', '')
            if len(date_str) == 8 and date_str.isdigit():
                files.append((date_str, f))

    if not files:
        return None

    files.sort(reverse=True)
    return directory / files[0][1]

def clean_eodhd_id_mappings():
    """Clean raw ID mapping data by removing entries with null FIGI and duplicate symbols."""
    input_path = find_latest_raw_file(RAW_DATA_DIR)

    if not input_path:
        print(f"No raw ID mapping files found in {RAW_DATA_DIR}")
        return

    print(f"Loading raw data from: {input_path}")

    # Load raw data
    with open(input_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    print(f"Loaded {len(raw_data):,} raw records")

    # Step 1: Filter out entries with null FIGI
    figi_filtered = [record for record in raw_data if record.get('figi') is not None]
    figi_filtered_count = len(raw_data) - len(figi_filtered)
    print(f"Removed {figi_filtered_count:,} records with null FIGI")

    # Step 2: Remove duplicate symbols, keeping only the first occurrence
    seen_symbols = set()
    unique_symbol_data = []

    for record in figi_filtered:
        symbol = record['symbol']
        if symbol not in seen_symbols:
            seen_symbols.add(symbol)
            unique_symbol_data.append(record)

    symbol_duplicate_count = len(figi_filtered) - len(unique_symbol_data)
    print(f"Removed {symbol_duplicate_count:,} duplicate symbol records")
    print(f"Remaining {len(unique_symbol_data):,} records with unique symbols")

    total_removed = figi_filtered_count + symbol_duplicate_count
    print(f"\nTotal records removed: {total_removed:,}")
    print(f"Final cleaned dataset: {len(unique_symbol_data):,} records")

    # Save cleaned data
    datestr = datetime.now().strftime("%Y%m%d")
    output_filename = f"id_mapping_us_{datestr}.json"
    output_path = RAW_DATA_DIR / output_filename

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(unique_symbol_data, f, indent=2)

    print(f"Cleaned data saved to: {output_path}")

    # Show sample of cleaned data
    if unique_symbol_data:
        print(f"\nSample cleaned record:")
        print(json.dumps(unique_symbol_data[0], indent=2))

if __name__ == "__main__":
    clean_eodhd_id_mappings()
