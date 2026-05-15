# Product Overview

**RiskMX Intelligence** is a data product that analyzes official crime incidence data in Mexico and combines it with socioeconomic and business indicators to generate municipal-level risk and opportunity intelligence.

The goal is to create a monetizable data product for entrepreneurs, local businesses, analysts, consultants and recruiters evaluating data engineering and analytics skills.

## Purpose
- Ingest, transform, and score crime incidence data from Mexico's SESNSP (Secretariado Ejecutivo del Sistema Nacional de Seguridad Pública) open datasets.
- Produce a municipal risk mart used for commercial risk assessment in insurance, real estate, logistics, and HR domains.
- Provide interactive dashboards and EDA notebooks for stakeholders.

Primary use cases:
- Identify municipalities with high business opportunity and controlled crime risk.
- Analyze crime trends by municipality, state and crime type.
- Generate risk indicators for commercial decision-making.
- Produce dashboards, reports and reusable datasets.

## Data Domain
- Source: SESNSP municipal crime statistics (CSV, latin-1 encoded, Spanish column names).
- Granularity: monthly crime counts per municipality, by crime type/subtype/modality.
- Geographic keys: `clave_entidad` (2-digit state code), `cvegeo` (5-digit municipal INEGI code).

## Language
- Code comments, variable names in transformation logic, and notebook narratives are written in **Spanish**.
- Python identifiers (function names, module names) use **English** or **snake_case Spanish** where domain terms have no clean English equivalent.


The project must be professional, reproducible and suitable for GitHub portfolio and Gumroad monetization.