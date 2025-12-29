import os
import requests
import json
from datetime import datetime
from pathlib import Path

# Configuration
RAW_DATA_DIR = Path("data/raw/eodhd")
ENV_FILE = Path(".env")

def load_env():
    """Simple .env loader to avoid extra dependencies like python-dotenv."""
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

def fetch_eodhd_id_mappings():
    """
    Fetch all EODHD ID mappings for US exchange.
    Retrieves paginated data and saves to a single JSON file.
    """
    load_env()
    api_token = os.getenv("EODHD_API_TOKEN")

    if not api_token or api_token == "your_api_token_here":
        print("Error: Please set a valid EODHD_API_TOKEN in the .env file.")
        return

    url = "https://eodhd.com/api/id-mapping"
    params = {
        "api_token": api_token,
        "filter[ex]": "US",
        "fmt": "json"
    }

    print("Fetching EODHD ID mappings for US exchange...")

    all_data = []
    page_count = 0
    total_records = 0

    current_url = url
    current_params = params.copy()

    while True:
        try:
            response = requests.get(current_url, params=current_params)
            response.raise_for_status()

            page_data = response.json()
            page_records = page_data.get('data', [])

            all_data.extend(page_records)
            page_count += 1
            total_records += len(page_records)

            print(f"Page {page_count}: {len(page_records)} records (total: {total_records:,})")

            # Check for next page
            links = page_data.get('links', {})
            next_url = links.get('next')

            if not next_url:
                break

            current_url = next_url
            current_params = {"api_token": api_token}

        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            break

    print(f"\nCompleted! Retrieved {len(all_data):,} total records across {page_count} pages")

    # Save data to file
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    datestr = datetime.now().strftime("%Y%m%d")
    output_path = RAW_DATA_DIR / f"id_mapping_us_raw_{datestr}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2)

    print(f"Data saved to: {output_path}")

if __name__ == "__main__":
    fetch_eodhd_id_mappings()
