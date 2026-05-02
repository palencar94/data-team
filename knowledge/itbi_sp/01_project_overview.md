# ITBI SP Dashboard — Project Overview

**Request ID:** 2026-05-01-itbi-sp-dashboard
**Requester:** Paulo Guilherme Alencar
**Status:** Live (dashboard running, full pipeline operational)
**Delivery date:** 2026-05-02

---

## What Is ITBI?

ITBI is the Imposto de Transmissão de Bens Imóveis — the São Paulo municipal tax levied on real estate transfers. The Prefeitura de São Paulo publishes monthly XLSX workbooks listing every taxed transaction (property address, transaction value, area, use type, construction standard, neighborhood).

This dataset is a comprehensive record of **all real estate sales in the city of São Paulo**, making it the primary source for market price analysis.

---

## Business Objective

Understand real estate price evolution in São Paulo city across 2026 to support investment and market analysis decisions.

## Key Business Questions

1. How have median real estate prices evolved month over month across the city?
2. Which neighborhoods have seen the highest price appreciation?
3. How does price per m² vary across neighborhoods and property use types?

---

## Acceptance Criteria (from intake)

- At least 3 chart types
- Filterable neighborhood ranking table
- Price per m² broken down by area and month
- Adding a new monthly sheet requires zero code changes (auto-detected by name pattern `MMM-YYYY`)

---

## Scope Boundaries

**In scope:**
- ITBI transactions from JAN-2026 to present (loaded sheets: JAN, FEV, MAR 2026)
- São Paulo city only (all source data is SP city)
- Residential and commercial properties

**Out of scope:**
- Pre-2026 historical data (present in source but treated as outliers)
- Personal identifiers (Cartório de Registro, Matrícula do Imóvel excluded at ingest)
- Forecasting or predictive analytics

---

## Delivery Summary

- **49,164 transactions** ingested across 3 monthly sheets
- Full Bronze → Silver → Gold medallion pipeline
- **Streamlit dashboard** at `http://localhost:8501`
- 3 Gold tables: monthly summary, neighborhood ranking, price per m²
- Neighborhood coverage: 4,524 unique neighborhoods after CEP enrichment
- Pipeline runs from a single `make pipeline` command
