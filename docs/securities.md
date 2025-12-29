# Securities Identity Manifest

This document describes the data sources, structure, and automated ingestion process used to maintain the canonical identity manifest for US-listed financial instruments (equities, ETFs, and funds).

## 1. Data Sources

The securities manifest combines data from two EODHD API endpoints to ensure comprehensive coverage and global identifier mapping:

### Primary Data Source: Securities List
*   **Endpoint**: `exchange-symbol-list/US`
*   **Purpose**: Provides comprehensive list of tradeable US instruments
*   **Scope**: Aggregates all major US exchanges including common stocks, preferred stocks, ETFs, mutual funds, and indices

### Supplementary Data Source: Identifier Mappings
*   **Endpoint**: `id-mapping` (with `filter[ex]=US`)
*   **Purpose**: Provides FIGI and ISIN mappings for global cross-referencing
*   **Scope**: Maps ticker symbols to standardized financial identifiers

## 2. Raw Data Available

The ingestion process works with two dated files from EODHD:

### Securities List JSON Fields
| Field | Description |
| :--- | :--- |
| **Code** | The ticker symbol (e.g., `AAPL`). |
| **Name** | The official company or instrument name. |
| **Exchange** | The EODHD exchange code (e.g., `NASDAQ`, `NYSE ARCA`). |
| **Type** | The instrument type (e.g., `Common Stock`, `ETF`). |

### Identifier Mappings JSON Fields
| Field | Description |
| :--- | :--- |
| **symbol** | The ticker symbol (may include exchange suffix like `AAPL.US`). |
| **figi** | Financial Instrument Global Identifier (primary global standard). |
| **isin** | International Securities Identification Number. |
| **name** | Associated company/fund name. |

## 3. The Ingestion Algorithm

To create a high-fidelity manifest for the `quasar` matching engine, the `scripts/ingest_eodhd_securities.py` script performs a multi-stage process combining both data sources.

### Step 0: Data Loading & Preparation
1.  **Load Securities List**: Import the raw securities data from EODHD exchange-symbol-list endpoint.
2.  **Load Identifier Mappings**: Import the cleaned FIGI mapping data from EODHD id-mapping endpoint.
3.  **Symbol Normalization**: Strip `.US` suffix from mapping symbols for compatibility with securities data.

### Step 1: FIGI Enrichment
*   **Cross-Reference**: Each security record is matched with FIGI mappings using symbol lookup.
*   **Strict Filtering**: Only securities with available FIGI mappings are retained. This ensures every manifest entry can be globally cross-referenced.
*   **ISIN Preservation**: ISIN data is captured alongside FIGI for additional validation.

### Step 2: MIC Exchange Mapping
EODHD exchange codes are mapped to standard **ISO 10383 Market Identifier Codes (MIC)** using an internal translation table:

| EODHD Code | MIC Code |
| :--- | :--- |
| `NASDAQ` | `XNAS` |
| `NYSE` | `XNYS` |
| `NYSE ARCA` | `ARCX` |
| `NYSE MKT` | `XASE` |

*   **Result**: If an exchange is not in this priority list, it is set to `null` to indicate a generic or non-primary listing.

### Step 3: (Symbol, Name) Deduplication
The "Matcher-Ready" requirement ensures a specific `(symbol, name)` pair maps to exactly one unique identity.
1.  **Grouping**: Records are grouped by the unique combination of ticker symbol and name.
2.  **Conflict Resolution**: For duplicate symbol/name pairs (often from dual-listings), the script prioritizes records with mapped MIC codes (preferring NASDAQ/NYSE over generic listings).
3.  **Canonical Selection**: The first qualifying record on a major exchange becomes the master identity.

## 4. Summary of Results

| Phase | Record Count | Description |
| :--- | :--- | :--- |
| **Securities List (Raw)** | ~445,000 | High noise (indices, delisted entities, secondary quotes) |
| **Identifier Mappings (Raw)** | ~105,000 | Comprehensive FIGI coverage with duplicates |
| **Combined & Filtered** | ~47,000 | FIGI-enriched securities with deduplication |
| **Final Manifest** | **47,085** | **Unique Financial Assets (Matcher-Ready)** |

**Key Features**:
- Every symbol maps to exactly one canonical record
- All entries include validated FIGI for global cross-referencing
- MIC exchange codes ensure proper market identification
- Zero ambiguity for matching engine queries (e.g., `AAPL` → exactly one record)

