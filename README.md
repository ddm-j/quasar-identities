# Quasar Identities

A collection of canonical financial instrument manifests designed for unambiguous asset identification.

## Overview

In the world of quantitative finance and algorithmic trading, mapping ticker symbols to real-world assets is a non-trivial challenge. Ticker symbols are recycled, duplicated across exchanges, and change over time.

This repository provides **Identity Manifests**: highly-curated, deduplicated, and validated lists of financial instruments. Each "Identity" represents a unique financial asset, mapping its trading symbols to a global, immutable standard like **FIGI** (Financial Instrument Global Identifier) for securities or **DTI** (Digital Token Identifier) for crypto.

### Why use this?

- **Zero Ambiguity**: Ensures that a symbol like `AAPL` or `USDC` refers to exactly one unique financial identity in your system.
- **Cross-Source Consistency**: Map data from multiple providers (EODHD, ANNA, etc.) to a single internal identifier.
- **Matcher-Ready**: Cleaned and pre-processed to remove noise like delisted entities, technical bridge tokens, and secondary listings.

## Available Manifests

| Manifest | Source of Truth | Documentation |
| :--- | :--- | :--- |
| **Crypto** | ANNA Service Bureau & DTIF | [docs/crypto.md](docs/crypto.md) |
| **US Securities** | EODHD API | [docs/securities.md](docs/securities.md) |

## Identity Schema

All manifests follow a standardized JSON schema located in `schemas/identity.schema.json`.

```yaml
- figi: BBG000B9XRY4
  symbol: AAPL
  name: Apple Inc
  exchange: XNAS
```

- **figi**: The global FIGI identifier for the asset (securities).
- **symbol**: The primary ticker symbol (or semicolon-separated aliases).
- **name**: The official name of the instrument.
- **exchange**: The primary listing exchange (Market Identifier Code).

## Usage

While these manifests were built to power the `quasar` matching engine, they are standalone data files usable by any trading system or security master.

To regenerate or update the manifests from raw data, use the scripts provided in the `scripts/` directory. Note that some scripts require API credentials stored in a `.env` file.

