# Crypto Identity Manifest

This document describes the hybrid data sources, structure, and automated ingestion process used to maintain the canonical identity manifest for digital assets (cryptocurrencies).

## Overview

The crypto manifest uses a **hybrid enrichment approach** that combines Kaiko's broad market coverage with ANNA's comprehensive alias system. This ensures maximum symbol recognition while maintaining global identifier standards.

### Key Innovation: ISIN-Bridged Enrichment
- **Primary Data**: Kaiko API provides FIGI-based identities with extensive coverage
- **Alias Enhancement**: ANNA Service Bureau data adds symbol aliases via ISIN matching
- **FIGI Integrity**: Duplicate resolution ensures 100% FIGI uniqueness
- **Result**: 7,466 enriched records with 20 additional aliases for enhanced recognition

## Data Sources

### Primary Data Source: Kaiko API
*   **Provider**: Kaiko (specialized crypto data platform)
*   **Scope**: Comprehensive coverage of active cryptocurrencies with FIGI mappings
*   **Purpose**: Primary source of truth for crypto identities and global identifiers

### Enrichment Data Source: ANNA Service Bureau
*   **Provider**: ANNA Service Bureau (DTIF partner)
*   **Scope**: ISIN-based identities with comprehensive symbol aliases
*   **Purpose**: Provides alias enrichment and validation via ISIN cross-referencing

## Workflow Architecture

The crypto manifest is built through a **two-stage pipeline**:

### Stage 1: ANNA Processing (Intermediate)
Raw ANNA data is processed into clean ISIN-based identities. See [docs/crypto_anna_processing.md](crypto_anna_processing.md) for detailed ANNA processing workflow.

**Input**: Raw ANNA CSV with ISIN, DTI, and symbol aliases
**Output**: `data/processed/anna/crypto_anna.yaml` (1,534 clean records)
**Purpose**: Creates reference dataset for ISIN-based enrichment

### Stage 2: Kaiko Enrichment (Final)
Kaiko data is enriched with ANNA aliases via ISIN matching and resolved for FIGI duplicates to create the canonical manifest.

**Processing Steps**:
1. ISIN-based alias enrichment
2. FIGI duplicate resolution (merge same-name, drop different-name)
3. Schema validation and final deduplication

**Input**:
- Raw Kaiko CSV (FIGI, ISIN, symbols)
- Processed ANNA data (ISIN reference)

**Output**: `manifests/crypto/crypto.yaml` (7,466 enriched records)
**Purpose**: Produces final manifest with enhanced symbol recognition and FIGI uniqueness

## Raw Data Available

### Kaiko CSV Fields
| Field | Description |
| :--- | :--- |
| **FIGI Code** | Financial Instrument Global Identifier (primary standard). |
| **ISIN** | International Securities Identification Number. |
| **Code** | Primary ticker symbol. |
| **Asset Name** | Official cryptocurrency name. |

### ANNA Processing Output
| Field | Description |
| :--- | :--- |
| **isin** | International Securities Identification Number. |
| **symbol** | Semicolon-separated aliases (e.g., `BTC;XBT`). |
| **name** | Official cryptocurrency name. |
| **exchange** | Set to `null` for cryptocurrencies. |

## The Enrichment Algorithm

The `scripts/ingest_kaiko_crypto.py` script performs ISIN-based enrichment using a four-step process:

### Step 1: Data Loading
1.  **Load Kaiko Data**: Import FIGI-based crypto identities from Kaiko CSV.
2.  **Load ANNA Reference**: Import processed ANNA data for alias enrichment.
3.  **ISIN Indexing**: Create lookup tables for efficient ISIN matching.

### Step 2: ISIN-Based Enrichment
For each Kaiko record with an ISIN:
1.  **ISIN Lookup**: Find matching record in ANNA data using ISIN as key.
2.  **Alias Combination**: Combine Kaiko symbols with ANNA aliases.
3.  **Deduplication**: Remove duplicates and create unique alias set.
4.  **Symbol Update**: Replace single symbol with semicolon-separated aliases.

### Step 3: FIGI Duplicate Resolution
Address Kaiko data quality issues where same FIGI is assigned to different assets:
1.  **FIGI Grouping**: Group records by FIGI identifier.
2.  **Name Consistency Check**: For FIGIs with multiple records:
    - **Same Names**: Merge symbols with ";" separator, keep one record.
    - **Different Names**: Drop all records (maintains data integrity).
3.  **Uniqueness Guarantee**: Ensures each FIGI maps to exactly one canonical asset.

### Step 4: Manifest Finalization
1.  **Schema Validation**: Ensure all records conform to identity schema.
2.  **Deduplication**: Remove duplicate symbols (keeping first occurrence).
3.  **Sorting**: Sort records by symbol for consistent output.

## Enrichment Logic Examples

### Case 1: Single Alias Addition
```
Kaiko Record: symbol="BTC", ISIN="XTV15WLZJMF0", FIGI="..."
ANNA Record: symbol="BTC;XBT", ISIN="XTV15WLZJMF0"
Result: symbol="BTC;XBT" (added 1 alias)
```

### Case 2: Multiple Alias Addition
```
Kaiko Record: symbol="BCH", ISIN="XT919BF3W7L4", FIGI="..."
ANNA Record: symbol="BCC;BCH;XBC", ISIN="XT919BF3W7L4"
Result: symbol="BCC;BCH;XBC" (added 2 aliases)
```

### Case 3: Wrapped Token Enrichment
```
Kaiko Record: symbol="WAVAX", ISIN="XTS6JCBF70N8", FIGI="..."
ANNA Record: symbol="AVAX;WAVAX", ISIN="XTS6JCBF70N8"
Result: symbol="AVAX;WAVAX" (added base token alias)
```

### Case 4: FIGI Duplicate Resolution

**Same Name Merge:**
```
Duplicate FIGI KKG00000HN36:
- Record 1: symbol="GXS", name="GXChain"
- Record 2: symbol="GXC", name="GXChain"
Result: symbol="GXC;GXS", name="GXChain" (1 record kept)
```

**Different Name Drop:**
```
Duplicate FIGI KKG00000DLJ7:
- Record 1: symbol="BST", name="Blocksquare Token"
- Record 2: symbol="WILD", name="Wilder World"
- Record 3: symbol="RLTM", name="Reality Metaverse"
Result: All 3 records dropped (ambiguous asset identity)
```

## Manifest Characteristics

### Coverage & Quality
| Metric | Value | Notes |
| :--- | :--- | :--- |
| **Total Records** | 7,466 | After FIGI duplicate resolution (from 7,476) |
| **ISIN Coverage** | 98% | 147/150 Kaiko ISINs matched to ANNA |
| **Enriched Records** | 19 | Records enhanced with additional aliases |
| **Additional Aliases** | 20 | Total aliases added through enrichment |
| **FIGI Uniqueness** | 100% | All FIGIs are unique after duplicate resolution |
| **Schema Compliance** | 100% | All records pass identity schema validation |

### Symbol Enhancement Impact
- **Base Coverage**: 7,466 symbols from Kaiko data (after FIGI duplicate resolution)
- **Enhanced Recognition**: +20 aliases (13.3% increase for ISIN-enabled records)
- **Alias Types**: Alternative names, wrapped tokens, legacy symbols
- **Validation**: All enrichments verified via ISIN matching
- **FIGI Integrity**: 100% uniqueness guaranteed through duplicate resolution

## Usage & Integration

### For Matching Engines
```python
# Query for Bitcoin - finds all variants
matches = find_by_symbol("BTC")      # Direct match
matches = find_by_symbol("XBT")      # Alias match
matches = find_by_symbol("WBTC")     # Different asset (no match)
```

### For Portfolio Systems
- **Global IDs**: FIGI provides universal identification
- **Symbol Flexibility**: Aliases enable recognition of asset references across sources
- **Validation**: ISIN cross-referencing ensures accuracy

## Comparison with Securities

| Aspect | Crypto Manifest | Securities Manifest |
| :--- | :--- | :--- |
| **Primary ID** | FIGI | FIGI |
| **Data Sources** | 2 (Kaiko + ANNA) | 2 (Securities + Mappings) |
| **Enrichment Method** | ISIN matching | Symbol matching |
| **Alias System** | Semicolon-separated | Single symbols |
| **Scale** | 7,466 records | 47,085 records |

## Future Enhancements

### Potential Improvements
- **Symbol Matching Fallback**: For records without ISIN matches
- **Additional Data Sources**: Integration of other crypto data providers
- **Alias Validation**: Automated verification of alias accuracy
- **Real-time Updates**: Automated refresh of enrichment data

---

**See Also**: [ANNA Processing Details](crypto_anna_processing.md) | [Securities Manifest](securities.md)