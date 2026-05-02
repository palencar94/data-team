# Naming Conventions

## General
- Use snake_case for dataset and field names
- Use explicit names over abbreviations
- Avoid reserved keywords

## Layer Prefixes
- bronze_<domain>_<entity>
- silver_<domain>_<entity>
- gold_<domain>_<subject>

## Key Fields
- Primary keys: <entity>_id
- Foreign keys: <parent_entity>_id
- Timestamps: created_at, updated_at, event_at

## KPI Naming
- kpi_<business_term>
- Ratio metrics end with _rate or _pct