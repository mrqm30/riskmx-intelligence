# Data Vault 2.0 Model - SESNSP Municipal Crime Incidence

## Source

Silver layer:

`silver/sesnsp/incidencia_delictiva_municipal`

The silver dataset contains one row per:

```text
municipality +  crime classification + month

Grain

The analytical grain for the core Raw Vault event is:

municipio + delito + periodo

Hubs
hub_entidad

Business key:

clave_entidad_str

Hash key:


