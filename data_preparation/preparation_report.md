# Data preparation results

Generated (UTC): 2026-11-03T01:02:27.1777561Z

Run from the project root with `powershell -ExecutionPolicy Bypass -File .\data_preparation\prepare_sources.ps1`. The script reads the two CSVs in `Datasets`, writes separate cleaned CSVs in this folder, and checks SHA-256 hashes before and after. The raw files are unchanged.

## Row counts and decisions

CMPD: 880471 raw rows -> 880471 cleaned rows. All source rows are retained with derived quality and status flags. Violent Crime: 80098 raw rows -> 68705 NPA rows; 11393 other geography rows were excluded from this NPA output. See cleaning_log.csv for every rule and its before/after counts.

## CMPD handling

- Dates: original timestamp strings are preserved; YYYY-MM-DD dates are derived. 0 report dates and 0 start dates were missing or invalid. Implausible years before 1900: 63 start, 9 end, 4 clearance. 9 rows have an end date before start date. These are flagged, not silently repaired.
- YEAR: 0 rows differ from report-date year; 22859 differ from start-date year. The source's YEAR assignment rule is still unverified, so neither mismatch is dropped.
- NPA: 24 rows have a zero, negative, or nonnumeric NPA. Original NPA strings are retained; no boundary equivalence is assumed.
- HIGHEST_NIBRS_CODE/DESCRIPTION: the source's single highest pair is retained. 0 rows conflict with another description for the same code, and 0 rows have an empty component. No violent-offense mapping is invented.
- CLEARANCE_STATUS: original categories are retained. 30714 Unfounded rows are flagged; 84239 rows have highest description Other Unlisted Non-Criminal; 7758 rows meet both conditions. Open is not treated as invalid, and Cleared is not treated as confirmed criminality.

## Violent Crime NPA handling and overlap investigation

- Each retained row is one reported NPA/year/month/offense count. 418 distinct NPA IDs and 24160 NPA-month groups remain. 0 retained rows have different GEOGRAPHY and GEOGRAPHY_ID strings.
- Violent Crime appears in 24155 retained rows; named categories appear in 44550 rows. Of 24155 NPA-month groups containing both, the broad count equals the sum of all named categories in 20893, is less in 3262, and is greater in 0. Excluding Non-Fatal Gunshot Injury from that sum gives 24155 equal, 0 less, and 0 greater. This exact equality across every group containing both is strong evidence that Violent Crime is a subtotal of the named offense categories excluding the injury indicator. The clean file tags these three levels separately and does not sum them together. Incident-level category definitions remain unverified.
- An absent NPA/month/offense row is left absent. It is not converted to zero, since the source does not define omitted groups.

## Validation checks

| Check | Observed rows | Gate |
|---|---:|---|
| cmpd_duplicate_or_missing_incident_id | 0 | must be zero |
| cmpd_unexpected_clearance_status | 0 | must be zero |
| cmpd_unexpected_year | 0 | must be zero |
| cmpd_nibrs_code_description_conflict | 0 | must be zero |
| cmpd_invalid_or_missing_report_date | 0 | reported for review |
| cmpd_invalid_or_missing_incident_began | 0 | reported for review |
| cmpd_year_report_mismatch | 0 | reported for review |
| cmpd_year_began_mismatch | 22859 | reported for review |
| violent_duplicate_npa_group_key | 0 | must be zero |
| violent_invalid_count | 0 | must be zero |
| violent_invalid_month | 0 | must be zero |
| violent_unexpected_year | 0 | must be zero |
| violent_unexpected_row_type | 0 | must be zero |
| violent_unexpected_offense_category | 0 | must be zero |

## Comparison readiness

No cross-source comparison table was created. NPA boundary vintage and assignment rules, common time basis, and the mapping between highest NIBRS code and summary offense categories remain unverified. The sources stay separate.

## Temporal cutoff for future modeling

The project reserves **2025-01-01 through 2025-12-31 as a temporal test period**. Development data end on **2024-12-31**. CMPD periods use report-date year (which equals source `YEAR` for every row in this extract); the NPA summary uses `CALENDAR_YEAR`. The prepared CSVs retain 2025 because preparation and descriptive EDA are not model tuning. Any future model selection, fitting, or tuning must use only periods through 2024-12-31 and must leave 2025 untouched until final evaluation. Both sources have incomplete 2026 coverage, so 2026 is excluded from that split. The split is a project decision; source completeness and NPA boundary stability remain unresolved.

## Unresolved definitions

- Obtain source data dictionaries for YEAR/date semantics, NPA boundaries, highest NIBRS selection, and the summary count methodology.
- Determine whether `Violent Crime` is a subtotal, whether specific categories overlap one another, and whether omitted rows mean zero or unavailable data.
