import csv
from pathlib import Path
from collections import Counter

# Configuration
KAIKO_FILE = Path("data/raw/kaiko/kaiko_asset_figi_20251229.csv")

def analyze_kaiko_crypto():
    """Analyze Kaiko crypto FIGI data for coverage statistics and duplicates."""
    print(f"Analyzing Kaiko crypto data from: {KAIKO_FILE}")

    total_entries = 0
    entries_with_figi = 0
    entries_with_isin = 0
    entries_with_both = 0

    # Track symbols for duplicate analysis
    figi_symbols = Counter()

    # Track some samples
    figi_samples = []
    both_samples = []
    duplicate_samples = []

    try:
        with open(KAIKO_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                total_entries += 1

                figi = row.get('FIGI Code', '').strip()
                isin = row.get('ISIN', '').strip()
                symbol = row.get('Code', '').strip()

                has_figi = bool(figi)
                has_isin = bool(isin)

                if has_figi:
                    entries_with_figi += 1
                    figi_symbols[symbol] += 1

                    if len(figi_samples) < 5:
                        figi_samples.append({
                            'name': row.get('Asset Name', ''),
                            'code': symbol,
                            'figi': figi
                        })

                if has_isin:
                    entries_with_isin += 1

                if has_figi and has_isin:
                    entries_with_both += 1
                    if len(both_samples) < 5:
                        both_samples.append({
                            'name': row.get('Asset Name', ''),
                            'code': symbol,
                            'figi': figi,
                            'isin': isin
                        })

    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # Analyze duplicates among FIGI entries
    symbols_with_duplicates = {symbol: count for symbol, count in figi_symbols.items() if count > 1}
    duplicate_count = len(symbols_with_duplicates)

    # Results
    print(f"\n=== Kaiko Crypto FIGI Analysis ===")
    print(f"Total entries: {total_entries:,}")

    print(f"\nCoverage Statistics:")
    print(f"Entries with FIGI: {entries_with_figi:,} ({entries_with_figi/total_entries*100:.1f}%)")
    print(f"Entries with ISIN: {entries_with_isin:,} ({entries_with_isin/total_entries*100:.1f}%)")
    print(f"Entries with both FIGI and ISIN: {entries_with_both:,} ({entries_with_both/total_entries*100:.1f}%)")

    print(f"\nFIGI-only entries: {entries_with_figi - entries_with_both:,}")
    print(f"ISIN-only entries: {entries_with_isin - entries_with_both:,}")

    print(f"\n=== Duplicate Symbol Analysis (among FIGI entries) ===")
    print(f"Total unique symbols with FIGI: {len(figi_symbols):,}")
    print(f"Symbols with duplicates: {duplicate_count:,} ({duplicate_count/len(figi_symbols)*100:.2f}%)")

    if symbols_with_duplicates:
        print(f"\nTop 5 symbols with most duplicates:")
        sorted_duplicates = sorted(symbols_with_duplicates.items(), key=lambda x: x[1], reverse=True)
        for symbol, count in sorted_duplicates[:5]:
            print(f"  {symbol}: {count} entries")

        # Show example duplicate
        if sorted_duplicates:
            example_symbol = sorted_duplicates[0][0]
            print(f"\nExample duplicate symbol '{example_symbol}':")

            # Re-read file to get details of duplicates
            with open(KAIKO_FILE, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                example_entries = [
                    {
                        'name': row.get('Asset Name', ''),
                        'figi': row.get('FIGI Code', ''),
                        'isin': row.get('ISIN', ''),
                        'eth_address': row.get('ETH Address', '')
                    }
                    for row in reader
                    if row.get('Code', '').strip() == example_symbol and row.get('FIGI Code', '').strip()
                ]

                for i, entry in enumerate(example_entries[:3], 1):
                    print(f"  Entry {i}: {entry['name']} - FIGI: {entry['figi']}, ISIN: {entry['isin'] or 'None'}")

                if len(example_entries) > 3:
                    print(f"  ... and {len(example_entries) - 3} more entries")

    if figi_samples:
        print(f"\nSample entries with FIGI:")
        for sample in figi_samples:
            print(f"  {sample['name']} ({sample['code']}): {sample['figi']}")

    if both_samples:
        print(f"\nSample entries with both FIGI and ISIN:")
        for sample in both_samples:
            print(f"  {sample['name']} ({sample['code']}): FIGI={sample['figi']}, ISIN={sample['isin']}")

if __name__ == "__main__":
    analyze_kaiko_crypto()
