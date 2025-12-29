# Securities Identity Manifest

This document describes the data source, structure, and automated ingestion process used to maintain the canonical identity manifest for US-listed financial instruments (equities, ETFs, and funds).

## 1. Data Source
The primary source of truth for US security identities is the **EODHD API**.

*   **Endpoint**: `exchange-symbol-list/US`
*   **Scope**: Aggregates all major US exchanges and provides a comprehensive list of tradeable instruments including common stocks, preferred stocks, ETFs, mutual funds, and indices.

## 2. Raw Data Available
The ingestion script processes a dated JSON file from EODHD containing the following key fields:

| Field | Description |
| :--- | :--- |
| **Code** | The ticker symbol (e.g., `AAPL`). |
| **Name** | The official company or instrument name. |
| **Isin** | International Securities Identification Number. |
| **Exchange** | The EODHD exchange code (e.g., `NASDAQ`, `NYSE ARCA`). |
| **Type** | The instrument type (e.g., `Common Stock`, `ETF`). |

## 3. The Ingestion Algorithm
To create a high-fidelity manifest for the `quasar` matching engine, the `scripts/ingest_eodhd_securities.py` script performs a multi-stage refinement process.

### Step 0: FIGI Filtering
The manifest is built around the **FIGI** as the primary global identifier.
*   **Strict Filter**: Only records with available FIGI mappings are processed. This ensures that every entry in the manifest can be cross-referenced with global financial databases.

### Step 1: MIC Exchange Mapping
EODHD exchange codes are mapped to standard **ISO 10383 Market Identifier Codes (MIC)** using an internal translation table:

| EODHD Code | MIC Code |
| :--- | :--- |
| `NASDAQ` | `XNAS` |
| `NYSE` | `XNYS` |
| `NYSE ARCA` | `ARCX` |
| `NYSE MKT` | `XASE` |

*   **Result**: If an exchange is not in this priority list, it is set to `null` to indicate a generic or non-primary listing.

### Step 2: (Symbol, Name) Deduplication
The "Matcher-Ready" requirement specifies that a specific `(symbol, name)` pair must map to a single unique identity.
1.  **Grouping**: Records are grouped by the unique combination of their ticker symbol and name.
2.  **Conflict Resolution**: If the same symbol/name appears multiple times (often due to dual-listings or secondary exchanges), the script prioritizes the record that has a mapped MIC code (e.g., preferring a NASDAQ/NYSE listing over a generic US listing).
3.  **Stability**: The first record found on a major exchange becomes the canonical master for that identity.

## 4. Summary of Results
| Phase | Record Count | Quality |
| :--- | :--- | :--- |
| **Raw JSON** | ~445,000 | High Noise (Indices, delisted entities, secondary quotes) |
| **Final Manifest** | **~64,121** | **Unique Financial Assets (Matcher-Ready)** |

**Key Feature**: Every symbol in the manifest is guaranteed to be unambiguous for the matching engine, ensuring that queries for a ticker like `AAPL` or `SPY` return exactly one canonical record with its associated global FIGI.

