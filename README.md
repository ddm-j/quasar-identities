# Quasar Identities

A collection of canonical financial instrument manifests designed for unambiguous asset identification.

## Overview

In the world of quantitative finance and algorithmic trading, mapping ticker symbols to real-world assets is a non-trivial challenge. Ticker symbols are recycled, duplicated across exchanges, and change over time.

This repository provides **Identity Manifests**: highly-curated, deduplicated, and validated lists of financial instruments. Each "Identity" represents a unique financial asset, mapping its trading symbols to a global, immutable standard like **FIGI** (Financial Instrument Global Identifier) for both securities and crypto assets.

### Why use this?

- **Zero Ambiguity**: Ensures that a symbol like `AAPL` or `USDC` refers to exactly one unique financial identity in your system.
- **Cross-Source Consistency**: Map data from multiple providers (EODHD, ANNA, etc.) to a single internal identifier.
- **Matcher-Ready**: Cleaned and pre-processed to remove noise like delisted entities, technical bridge tokens, and secondary listings.

## Available Manifests

| Manifest | Source of Truth | Documentation |
| :--- | :--- | :--- |
| **Crypto** | Kaiko API (enriched with ANNA) | [docs/crypto.md](docs/crypto.md) |
| **US Securities** | EODHD API | [docs/securities.md](docs/securities.md) |

## Identity Schema

All manifests follow a standardized JSON schema located in `schemas/identity.schema.json`.

```yaml
- figi: BBG000B9XRY4
  symbol: AAPL
  name: Apple Inc
  exchange: XNAS
```

Or with aliases:

```yaml
- figi: BBG000B9XRY4
  symbol: BTC;XBT
  name: Bitcoin
  exchange: null
```

- **figi**: The global FIGI identifier for the asset.
- **symbol**: The primary ticker symbol (or semicolon-separated aliases for enhanced recognition).
- **name**: The official name of the instrument.
- **exchange**: The primary listing exchange (Market Identifier Code) or `null` for crypto.

## Usage

While these manifests were built to power the `quasar` matching engine, they are standalone data files usable by any trading system or security master.

### Script Workflows

To regenerate or update the manifests from raw data, follow these workflows. Note that some scripts require API credentials stored in a `.env` file.

#### Crypto Manifest Workflow

1. **Download Raw Data**
   - Download Kaiko crypto data from: https://instruments.kaiko.com/#/assets
   - Download ANNA crypto data from: https://anna-web.org/digital-assets-1/
   - Save Kaiko data as `data/raw/kaiko/kaiko_asset_figi_YYYYMMDD.csv`
   - Save ANNA data as `data/raw/anna/ISIN-DTI-List-YYYYMMDD.csv`

2. **Process ANNA Data (Stage 1)**
   ```bash
   python scripts/ingest_anna_crypto.py
   ```
   - Input: `data/raw/anna/ISIN-DTI-List-YYYYMMDD.csv`
   - Output: `data/processed/anna/crypto_anna.yaml` (1,534 records)

3. **Enrich Kaiko Data (Stage 2)**
   ```bash
   python scripts/ingest_kaiko_crypto.py
   ```
   - Input: `data/raw/kaiko/kaiko_asset_figi_YYYYMMDD.csv` + `data/processed/anna/crypto_anna.yaml`
   - Output: `manifests/crypto/crypto.yaml` (7,476 enriched records)

#### Securities Manifest Workflow

1. **Fetch Raw Securities Data**
   ```bash
   python scripts/fetch_eodhd_raw.py
   ```
   - Requires: EODHD API token in `.env`
   - Output: `data/raw/eodhd/us_securities_YYYYMMDD.json`

2. **Fetch Identifier Mappings**
   ```bash
   python scripts/fetch_eodhd_id_mapping.py
   ```
   - Requires: EODHD API token in `.env`
   - Output: `data/raw/eodhd/id_mapping_us_raw_YYYYMMDD.json`

3. **Clean Identifier Mappings**
   ```bash
   python scripts/clean_eodhd_id_mappings.py
   ```
   - Input: `data/raw/eodhd/id_mapping_us_raw_YYYYMMDD.json`
   - Output: `data/raw/eodhd/id_mapping_us_YYYYMMDD.json`

4. **Generate Securities Manifest**
   ```bash
   python scripts/ingest_eodhd_securities.py
   ```
   - Input: `data/raw/eodhd/us_securities_YYYYMMDD.json` + `data/raw/eodhd/id_mapping_us_YYYYMMDD.json`
   - Output: `manifests/securities/securities.yaml` (47,085 records)

