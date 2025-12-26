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

def fetch_eodhd_raw():
    load_env()
    api_token = os.getenv("EODHD_API_TOKEN")
    
    if not api_token or api_token == "your_api_token_here":
        print("Error: Please set a valid EODHD_API_TOKEN in the .env file.")
        return

    # Endpoint for all US tradeable instruments (Equities, ETFs, Funds, Indices)
    # We are not using the 'type' filter as requested.
    url = "https://eodhd.com/api/exchange-symbol-list/US"
    params = {
        "api_token": api_token,
        "fmt": "json"
    }

    print(f"Connecting to EODHD API to fetch all US securities...")
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}")
        try:
            print(f"Response: {response.text}")
        except:
            pass
        return

    data = response.json()
    
    # Ensure directory exists
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save to disk with datestamp
    datestr = datetime.now().strftime("%Y%m%d")
    output_path = RAW_DATA_DIR / f"us_securities_{datestr}.json"
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    
    print(f"Successfully retrieved {len(data)} records.")
    print(f"Raw data saved to: {output_path}")

if __name__ == "__main__":
    fetch_eodhd_raw()

