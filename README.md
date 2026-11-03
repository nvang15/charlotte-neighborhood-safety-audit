# Rated for Whom? Auditing Neighborhood Safety Scores in Charlotte

This D2 project examines how reported incident data, geographic assignment, time windows, and offense definitions can affect what a neighborhood safety score appears to show. It keeps the Charlotte-Mecklenburg Police Department incident records and the published violent-crime summary separate because their geography, time basis, and offense definitions have not been verified as comparable.

The project reports descriptive counts. It does not create safety grades, label areas safe or unsafe, estimate unobserved population values, or claim that reported counts measure all crime.

## D2 deliverables

- [Data note (PDF)](D2_data_note.pdf) and [editable Markdown source](D2_data_note.md)
- [Data-preparation code and documentation](data_preparation/)
- [Source-audit code and report](source_audit/)
- [Exploratory plots and interpretations](d2_eda/D2_EDA_report.md)
- [Supabase-backed Streamlit dashboard](dashboard/)
- Live Modal dashboard: https://nvang15--charlotte-d2-descriptive-dashboard-serve.us-east.modal.run

## Data access

The raw and cleaned incident-level CSV files are excluded from Git because they are large and may contain location-level fields. To reproduce preparation, obtain the project source files and place them at:

```text
Datasets/CMPD_Incidents.csv
Datasets/Violent_Crime_Data.csv
```

The preparation scripts preserve the raw files and verify their SHA-256 hashes before and after processing. The repository includes the data dictionary, cleaning log, audit results, preparation results, and the small NPA/year aggregate CSVs used to populate Supabase.

The provenance, extraction dates, formal source dictionaries, and Neighborhood Profile Area boundary vintage remain unresolved and are documented as limitations rather than inferred.

## Reproduce data preparation

From the repository root in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\source_audit\audit_sources.ps1
powershell -ExecutionPolicy Bypass -File .\data_preparation\prepare_sources.ps1
powershell -ExecutionPolicy Bypass -File .\dashboard\prepare_dashboard_data.ps1
```

The main preparation implementation is in `data_preparation/PrepareData.cs`. The dashboard aggregation implementation is in `dashboard/AggregateDashboard.cs`.

The scripts generate or refresh:

- `data_preparation/cmpd_incidents_clean.csv` — excluded from Git because of size
- `data_preparation/violent_crime_npa_clean.csv` — excluded from Git because it is derived from the raw source
- `data_preparation/data_dictionary.csv`
- `data_preparation/cleaning_log.csv`
- `data_preparation/preparation_results.json`
- `data_preparation/preparation_report.md`
- `dashboard/data/cmpd_npa_year_counts.csv`
- `dashboard/data/violent_npa_year_offense_counts.csv`

## Dashboard

The dashboard reads only two NPA/year aggregate tables from Supabase. It does not read the raw or cleaned incident-level files at runtime.

See [dashboard/README.md](dashboard/README.md) for the schema, table imports, environment variables, local Streamlit command, and Modal deployment instructions. Keep real credentials out of the repository. The application requires `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY`; it must never use a service-role key.

## Analysis boundaries

- Calendar year 2025 is reserved as the temporal test period for future modeling. Its use in D2 is descriptive only.
- Incomplete 2026 data are excluded from future modeling and from the dashboard aggregates.
- Counts are not population-adjusted rates and are not safety ratings.
- The two sources are not compared or summed.
- Missing summary groups are not assumed to be zero.

## AI assistance

OpenAI Codex assisted with code organization, documentation, quality checks, dashboard presentation, and repository setup. The student remains responsible for verifying the analysis, explaining the code and analytical choices, and complying with the course AI policy.
