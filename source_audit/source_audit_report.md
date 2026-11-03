# Source audit: Rated for Whom? Auditing Neighborhood Safety Scores in Charlotte

Generated (UTC): 2026-11-03T01:04:03.1703447Z

## Reproduction and scope

Run from the project root with `powershell -ExecutionPolicy Bypass -File .\source_audit\audit_sources.ps1`. The script reads the raw CSV files under `Datasets` and writes `audit_results.json`; it does not edit or combine source files. The requested `upload` directory was absent, so the matching files in `Datasets` were used.

Empty CSV fields are counted as missing; text such as `Unknown`, `N/A`, and zero is retained as a value. Numeric inference requires all nonempty field values to parse as numbers. Numeric-looking codes can therefore appear numeric and must be treated as categorical identifiers where appropriate. Date parsing/ranges apply to fields with `DATE` or `TIME` in their names.

## CMPD_Incidents.csv

Rows: 880471; columns: 29.

| Field | Inferred type | Missing | Unique | Observed range |
|---|---|---:|---:|---|
| X | numeric | 0 (0%) | 22433 | 1384868.00003931 to 1535394.99983773 |
| Y | numeric | 0 (0%) | 22923 | 465419.000129312 to 645111.999994561 |
| YEAR | numeric | 0 (0%) | 10 | 2017 to 2026 |
| INCIDENT_REPORT_ID | string/category | 0 (0%) | 880471 |  |
| LOCATION | string/category | 0 (0%) | 39777 |  |
| CITY | string/category | 0 (0%) | 93 |  |
| STATE | string/category | 262 (0.0298%) | 5 |  |
| ZIP | string/category | 306381 (34.7974%) | 710 |  |
| X_COORD_PUBLIC | numeric | 0 (0%) | 22433 | 1384868 to 1535395 |
| Y_COORD_PUBLIC | numeric | 0 (0%) | 22923 | 465419 to 645112 |
| LATITUDE_PUBLIC | numeric | 0 (0%) | 24513 | -80.963592 to 35.508584 |
| LONGITUDE_PUBLIC | numeric | 0 (0%) | 24680 | -81.055885 to -80.555399 |
| DIVISION_ID | string/category | 0 (0%) | 25 |  |
| CMPD_PATROL_DIVISION | string/category | 0 (0%) | 18 |  |
| NPA | numeric | 0 (0%) | 451 | 0 to 476 |
| DATE_REPORTED | datetime | 0 (0%) | 3590 | 01/01/2017 00:00:00 to 10/30/2026 00:00:00 |
| DATE_INCIDENT_BEGAN | datetime | 0 (0%) | 5116 | 01/30/0200 00:00:00 to 10/30/2026 00:00:00 |
| DATE_INCIDENT_END | datetime | 207195 (23.5323%) | 4424 | 03/19/0201 23:00:00 to 10/30/2026 00:00:00 |
| ADDRESS_DESCRIPTION | string/category | 3 (0.0003%) | 2 |  |
| LOCATION_TYPE_DESCRIPTION | string/category | 0 (0%) | 5 |  |
| PLACE_TYPE_DESCRIPTION | string/category | 0 (0%) | 5 |  |
| PLACE_DETAIL_DESCRIPTION | string/category | 0 (0%) | 82 |  |
| CLEARANCE_STATUS | string/category | 0 (0%) | 5 |  |
| CLEARANCE_DETAIL_STATUS | string/category | 0 (0%) | 12 |  |
| CLEARANCE_DATE | datetime | 522198 (59.3089%) | 3598 | 01/05/0202 00:00:00 to 10/30/2026 00:00:00 |
| HIGHEST_NIBRS_CODE | string/category | 0 (0%) | 72 |  |
| HIGHEST_NIBRS_DESCRIPTION | string/category | 0 (0%) | 72 |  |
| OBJECTID | numeric | 0 (0%) | 880471 | 1 to 880471 |
| GlobalID | string/category | 0 (0%) | 880471 |  |

### Duplicate identifier and key checks

- `INCIDENT_REPORT_ID`: 0 repeated nonmissing keys; 880471 distinct nonmissing keys; 0 rows with a missing key component.
- `GlobalID`: 0 repeated nonmissing keys; 880471 distinct nonmissing keys; 0 rows with a missing key component.
- `OBJECTID`: 0 repeated nonmissing keys; 880471 distinct nonmissing keys; 0 rows with a missing key component.

### Latest-year month coverage

Observed rows by month for 2026 (CMPD uses DATE_REPORTED; summary uses CALENDAR_YEAR/CALENDAR_MONTH):

| Month | Rows |
|---|---:|
| 01 | 6960 |
| 02 | 6216 |
| 03 | 7415 |
| 04 | 7373 |
| 05 | 7695 |
| 06 | 7678 |
| 07 | 7882 |
| 08 | 7726 |
| 09 | 7587 |
| 10 | 7379 |

### Important category frequencies (top 25)

**YEAR**

| Value | Rows |
|---|---:|
| 2023 | 95525 |
| 2024 | 92217 |
| 2019 | 92096 |
| 2025 | 91226 |
| 2022 | 89557 |
| 2017 | 89004 |
| 2018 | 88395 |
| 2021 | 84921 |
| 2020 | 83619 |
| 2026 | 73911 |

**CITY**

| Value | Rows |
|---|---:|
| CHARLOTTE | 878658 |
| MECKLENBURG | 596 |
| MATTHEWS | 336 |
| PINEVILLE | 318 |
| HUNTERSVILLE | 200 |
| MINT HILL | 135 |
| CHARLOTE | 34 |
| CORNELIUS | 19 |
| CHARLOTTE - NC | 13 |
| CHARLOTTE, NC | 11 |
| CHARLOTTTE | 10 |
| MIDLAND | 10 |
| DAVIDSON | 8 |
| MATHEWS | 8 |
| CHARLOTTE, NC  28273 | 5 |
| CHARLTOTE | 5 |
| CHAROLETTE | 5 |
| CHARLOTTLE | 4 |
| CHAROLTTE | 4 |
| CHARLOTTE, | 3 |
| CHRLOTTE | 3 |
| OTHER/NOT LISTED | 3 |
| 110 | 2 |
| 28226 | 2 |
| CAHRLOTTE | 2 |

**STATE**

| Value | Rows |
|---|---:|
| NC | 880199 |
|  | 262 |
| ND | 5 |
| SC | 3 |
| IN | 1 |
| NY | 1 |

**CMPD_PATROL_DIVISION**

| Value | Rows |
|---|---:|
| University City | 103247 |
| Steele Creek | 94479 |
| North | 81276 |
| Westover | 68741 |
| Metro | 67592 |
| North Tryon | 64975 |
| Central | 63090 |
| Freedom | 62700 |
| Hickory Grove | 53938 |
| Eastway | 53631 |
| Providence | 53337 |
| Independence | 50542 |
| South | 48543 |
| Airport | 13027 |
| NA | 773 |
| Huntersville | 564 |
| Davidson | 15 |
| Unknown | 1 |

**NPA**

| Value | Rows |
|---|---:|
| 476 | 43850 |
| 371 | 15645 |
| 3 | 14666 |
| 331 | 13833 |
| 122 | 12371 |
| 124 | 11403 |
| 387 | 10430 |
| 290 | 10357 |
| 219 | 9873 |
| 72 | 9566 |
| 370 | 8199 |
| 385 | 7966 |
| 164 | 7507 |
| 358 | 7339 |
| 393 | 7216 |
| 363 | 6829 |
| 374 | 6510 |
| 367 | 6500 |
| 389 | 6275 |
| 60 | 6069 |
| 96 | 6061 |
| 53 | 5744 |
| 142 | 5732 |
| 66 | 5687 |
| 157 | 5679 |

**CLEARANCE_STATUS**

| Value | Rows |
|---|---:|
| Open | 531712 |
| Exceptionally Cleared | 172813 |
| Cleared by Arrest | 137027 |
| Unfounded | 30714 |
| Cleared by Arrest by Another Agency | 8205 |

**CLEARANCE_DETAIL_STATUS**

| Value | Rows |
|---|---:|
| Open | 522179 |
| Cleared by Arrest | 137027 |
| Cleared by Other Means | 96130 |
| Victim Chose not to Prosecute | 51205 |
| Unfounded | 28144 |
| Located (Missing Persons and Runaways only) | 23321 |
| Cleared, Pending Arrest Validation | 9533 |
| Cleared by Arrest by Another Agency | 8205 |
| Unfounded-Referred to Other Agency | 2570 |
| Prosecution Declined by DA | 1649 |
| By Death of Offender | 487 |
| Extradition Declined | 21 |

**HIGHEST_NIBRS_CODE**

| Value | Rows |
|---|---:|
| 23F | 87101 |
| 90Z | 86025 |
| 899 | 84239 |
| 13B | 76825 |
| 23H | 76218 |
| 23C | 53685 |
| 290 | 50429 |
| 240 | 43925 |
| 220 | 40806 |
| 35A | 33464 |
| 13C | 28364 |
| 13A | 26494 |
| 800 | 23740 |
| 26A | 16516 |
| 120 | 14380 |
| 23G | 14124 |
| 26B | 9737 |
| 23D | 9578 |
| 26F | 9444 |
| 802 | 8777 |
| 520 | 7693 |
| 280 | 6509 |
| 90J | 6343 |
| 26C | 5695 |
| 250 | 5205 |

**HIGHEST_NIBRS_DESCRIPTION**

| Value | Rows |
|---|---:|
| Theft From Motor Vehicle | 87101 |
| All Other Offenses | 86025 |
| Other Unlisted Non-Criminal | 84239 |
| Simple Assault | 76825 |
| All Other Thefts | 76218 |
| Shoplifting | 53685 |
| Damage/Vandalism Of Property | 50429 |
| Motor Vehicle Theft | 43925 |
| Burglary/B&E | 40806 |
| Drug/Narcotic Violations | 33464 |
| Intimidation | 28364 |
| Aggravated Assault | 26494 |
| Missing Person | 23740 |
| False Pretenses/Swindle | 16516 |
| Robbery | 14380 |
| Theft of Motor Vehicle Parts from Vehicle | 14124 |
| Credit Card/Teller Fraud | 9737 |
| Theft From Building | 9578 |
| Identity Theft | 9444 |
| Sudden/Natural Death Investigation | 8777 |
| Weapon Law Violations | 7693 |
| Stolen Property Offenses | 6509 |
| Trespass Of Real Property | 6343 |
| Impersonation | 5695 |
| Counterfeiting/Forgery | 5205 |

**LOCATION_TYPE_DESCRIPTION**

| Value | Rows |
|---|---:|
| Indoors | 386329 |
| Outdoors | 316780 |
| Parking Lot | 136869 |
| Other | 26306 |
| Parking Deck | 14187 |

**PLACE_TYPE_DESCRIPTION**

| Value | Rows |
|---|---:|
| Residential | 411511 |
| Open Area | 141751 |
| Commercial Place | 139803 |
| Retail | 132624 |
| Public/Non-Residential | 54782 |


## Violent_Crime_Data.csv

Rows: 80098; columns: 8.

| Field | Inferred type | Missing | Unique | Observed range |
|---|---|---:|---:|---|
| ROW_TYPE | string/category | 0 (0%) | 4 |  |
| GEOGRAPHY | string/category | 0 (0%) | 429 |  |
| GEOGRAPHY_ID | numeric | 0 (0%) | 418 | 0 to 476 |
| CALENDAR_YEAR | numeric | 0 (0%) | 12 | 2015 to 2026 |
| CALENDAR_MONTH | numeric | 0 (0%) | 12 | 1 to 12 |
| OFFENSE_DESCRIPTION | string/category | 0 (0%) | 11 |  |
| OFFENSE_COUNT | numeric | 0 (0%) | 341 | 1 to 891 |
| OBJECTID | numeric | 0 (0%) | 80098 | 1 to 80098 |

### Duplicate identifier and key checks

- `OBJECTID`: 0 repeated nonmissing keys; 80098 distinct nonmissing keys; 0 rows with a missing key component.
- `ROW_TYPE, GEOGRAPHY, GEOGRAPHY_ID, CALENDAR_YEAR, CALENDAR_MONTH, OFFENSE_DESCRIPTION`: 0 repeated nonmissing keys; 80098 distinct nonmissing keys; 0 rows with a missing key component.

### Latest-year month coverage

Observed rows by month for 2026 (CMPD uses DATE_REPORTED; summary uses CALENDAR_YEAR/CALENDAR_MONTH):

| Month | Rows |
|---|---:|
| 01 | 459 |
| 02 | 455 |
| 03 | 475 |

### Important category frequencies (top 25)

**ROW_TYPE**

| Value | Rows |
|---|---:|
| Neighborhood Profile Area | 68705 |
| Corridor of Opportunity | 6475 |
| Violent Crime Hotspot | 3463 |
| CMPD Jurisdiction | 1455 |

**GEOGRAPHY**

| Value | Rows |
|---|---:|
| CMPD | 1455 |
| Central/Albemarle | 1190 |
| Freedom Drive/Wilkinson | 1184 |
| Sugar Creek/I-85 | 1134 |
| Beatties Ford/Rozzelles Ferry | 1060 |
| 476 | 1025 |
| Graham Street/North Tryon | 1011 |
| Sugar Creek/I-85 Area | 1011 |
| West Boulevard | 896 |
| Nations Ford/Arrowood Area | 889 |
| Beatties Ford Area | 819 |
| 371 | 810 |
| Central/Sharon Amity Area | 744 |
| 385 | 693 |
| 124 | 630 |
| 374 | 622 |
| 363 | 616 |
| 290 | 603 |
| 53 | 580 |
| 164 | 576 |
| 157 | 560 |
| 370 | 554 |
| 387 | 549 |
| 6 | 543 |
| 219 | 530 |

**OFFENSE_DESCRIPTION**

| Value | Rows |
|---|---:|
| Violent Crime | 25640 |
| Aggravated Assault-Gun | 13559 |
| Armed Robbery | 10343 |
| Aggravated Assault-Other Weapon | 7098 |
| Aggravated Assault-Knife | 5977 |
| Strong Arm Robbery | 5794 |
| Non-Fatal Gunshot Injury | 4406 |
| Rape | 3506 |
| Aggravated Assault-Fists,Feet, etc. | 1924 |
| Homicide | 1478 |
| Attempted Rape | 373 |

**CALENDAR_YEAR**

| Value | Rows |
|---|---:|
| 2020 | 7811 |
| 2019 | 7448 |
| 2021 | 7387 |
| 2022 | 7341 |
| 2023 | 7194 |
| 2016 | 7160 |
| 2017 | 7116 |
| 2024 | 7105 |
| 2018 | 6963 |
| 2015 | 6807 |
| 2025 | 6377 |
| 2026 | 1389 |

**CALENDAR_MONTH**

| Value | Rows |
|---|---:|
| 07 | 7188 |
| 01 | 6866 |
| 08 | 6864 |
| 06 | 6840 |
| 05 | 6831 |
| 03 | 6678 |
| 10 | 6671 |
| 09 | 6602 |
| 12 | 6581 |
| 11 | 6423 |
| 02 | 6407 |
| 04 | 6147 |

## Verified source facts

- CMPD has one unique `INCIDENT_REPORT_ID` per row and incident dates, location, clearance, and one highest NIBRS code/description. It is an incident-report table. The summary has one unique geography/year/month/offense combination per row and an `OFFENSE_COUNT` field, so it is already aggregated.
- CMPD offers public coordinates, ZIP, patrol division, and `NPA`; the summary has four `ROW_TYPE` values, including `Neighborhood Profile Area`, plus `GEOGRAPHY` and `GEOGRAPHY_ID`. The incident file contains 451 distinct NPA values; the summary has 418 distinct IDs in its NPA row type.
- CMPD offers report, incident began/end, and clearance dates; the summary uses calendar year and month. CMPD reported dates cover 2017-01-01 through 2026-10-30. The summary spans 2015 through 2026, with 2026 rows only in January through March. The latest-year month tables above make this difference explicit.
- CMPD has 30,714 `CLEARANCE_STATUS = Unfounded` rows and 84,239 `HIGHEST_NIBRS_DESCRIPTION = Other Unlisted Non-Criminal` rows. These counts should not be added because the groups may overlap. Some incident begin/end and clearance values have implausible years such as 0200â€“0202; the date ranges above show them.
- The summary contains both `Violent Crime` and named offense categories. Its `OFFENSE_COUNT` values range from 1 to 891, with no explicit zero-count rows.

## Assumptions and analytical risks

- A shared numeric NPA identifier does not establish matching boundaries or vintages. The two sources may use different NPA coverage or assignment rules. Confirm the crosswalk and geography versions before comparing neighborhood values.
- CMPD `YEAR` may follow report year or incident year; the CSV does not define it. Report date and occurrence date are different concepts. The timestamp suffix `+00` suggests a UTC offset, but timezone and date assignment rules require documentation.
- CMPD records only a highest NIBRS code on each row, while the summary uses broader named categories. A highest code can omit secondary offenses. The summary `Violent Crime` category may overlap its named categories; category exclusivity and whether counts represent incidents or offense occurrences are unverified.
- `Unfounded` and noncriminal labels require an explicit inclusion rule. The observed counts alone do not show the overlap between those groups or which categories the summary excludes. Excluding every record with a broad label could change the target population.
- The two 2026 windows differ, and a year with observed rows is not proof of complete coverage. Missing geography/month/offense groups may mean zero, suppression, or absent data; the file does not say which.

## Recommended cleaning decisions

- Preserve originals. Parse dates into derived typed columns while retaining source strings. Flag implausible years and decide their handling with a documented rule. Choose an occurrence-date convention only after confirming source semantics.
- Treat report IDs and aggregate dimensions as keys. If future extracts have repeats, investigate before deduplication. Keep numeric-looking ZIP, NPA, and geography codes as identifiers.
- Normalize whitespace and category spelling only in derived columns. Keep zero distinct from missing; do not fill absent summary groups with zero without source confirmation.
- Before a score comparison, document an offense inclusion list, complete common time window, geography boundary vintage/crosswalk, and denominator. Keep both sources separate until those definitions are settled.

## Unresolved questions

- What are the provenance, extraction dates, and data dictionaries for the two files? The project root has no README or `AGENTS.md`.
- Does CMPD `YEAR` mean incident year or report year? What timezone/date rules govern incident began/end, and how should malformed years be handled?
- Which noncriminal and unfounded records belong in the analysis population? Does the summary exclude them?
- Are summary offense categories mutually exclusive? What does `OFFENSE_COUNT` count? Does an absent group mean zero or missing?
- Which boundary vintage defines each summary NPA and CMPD NPA? Why do the files contain different numbers of distinct NPA identifiers?
- Were the intended inputs expected in `upload`? That folder was absent; confirm that `Datasets` contains the intended D2 copies.

## Repository inspection

The project root contains `Datasets/` and `DTSC 3602 Project.pdf`; no Git repository, README, or `AGENTS.md` was found. No raw source file was changed.

## Preparation follow-up

The [data preparation report](../data_preparation/preparation_report.md) records the cleaning rules and actual results. It retains 880471 CMPD rows with quality flags and produces 68705 NPA summary rows from 80098 source rows. CMPD YEAR matches parsed report-date year on every row in this extract; 22859 rows differ from incident-start year. Of 24155 NPA-month groups containing both the broad category and named categories, the broad count equals the sum of named categories excluding Non-Fatal Gunshot Injury in 24155 groups. These counts support treating Violent Crime as a subtotal and keeping the injury indicator separate. No cross-source comparison table was created.
