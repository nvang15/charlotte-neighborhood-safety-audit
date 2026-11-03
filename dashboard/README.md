# D2 descriptive dashboard

This Streamlit app reads **only two Neighborhood Profile Area (NPA)/year aggregate tables from Supabase**. It never reads incident addresses, coordinates, IDs, or person-level records. The source selector keeps Charlotte-Mecklenburg Police Department (CMPD) report counts separate from the published violent-crime summary. The app does not create a grade, rate, model, or cross-source comparison.

## What is displayed

| Source | Unit and years | Measure |
|---|---|---|
| Charlotte-Mecklenburg Police Department incident reports | NPA × report-date year, 2017–2025 | Number of reported incident records, all highest-NIBRS classifications retained |
| Published violent-crime summary | NPA × calendar year × offense, 2015–2025 | Reported aggregate offense counts; `Violent Crime` is a subtotal, named offenses are a breakdown, and `Non-Fatal Gunshot Injury` is an indicator |

The two exports are built from [prepared sources](../data_preparation/preparation_report.md). The source audit found that `Violent Crime` equals the named-offense sum **excluding** the injury indicator in every NPA/month group where both appear. The dashboard does not add levels together. Both 2026 extracts are partial, so they are omitted. A missing NPA/offense row is not imputed as zero. The 2025 data are displayed descriptively; they remain reserved as the temporal test period for any future modeling per the [D2 note](../D2_data_note.md).

The dashboard defines NPA in a glossary and notes that its boundaries may not match a reader's everyday idea of a neighborhood. Each chart identifies its selected year, source, geography, and measure, followed by a short reading guide and a chart-specific limitation. Incident-report records and aggregate offense counts are labeled separately and are not treated as interchangeable.

The NPA charts use a fixed count scale that begins at zero; mouse-wheel and pointer zoom are disabled. A control below each chart selects and highlights up to two displayed NPAs. One selection shows its reported count and context. Two selections add a side-by-side table and the absolute difference between the displayed counts. **Reset view** clears the current NPA selections and returns the chart to its full fixed range. These comparisons remain descriptive reported counts, not population-adjusted rates or safety ratings.

## Rebuild the aggregate CSVs

From the project root, in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\dashboard\prepare_dashboard_data.ps1
```

This reads `data_preparation/cmpd_incidents_clean.csv` and `data_preparation/violent_crime_npa_clean.csv` and writes only `dashboard/data/cmpd_npa_year_counts.csv` and `dashboard/data/violent_npa_year_offense_counts.csv`. Source files are never modified. The current run read 880,471 CMPD rows and 68,705 prepared NPA summary rows. It omitted 73,911 CMPD rows and 1,168 summary rows from partial 2026, then omitted 21 CMPD rows with unusable NPA and 2 summary rows with NPA ID 0. The outputs have **3,779** CMPD NPA/year rows and **21,367** summary NPA/year/offense rows. The script checks date/year agreement, count validity, geography type, offense levels, and the broad/named subtotal relationship. Rebuilding replaces these two derived exports only.

### Aggregate data dictionary

| File/table | Column | Meaning |
|---|---|---|
| `cmpd_npa_year_counts.csv` / `d2_cmpd_npa_year` | `npa_id` | Positive numeric CMPD NPA identifier; boundary vintage unverified |
| | `year` | CMPD `YEAR`, verified equal to report-date year in this extract |
| | `report_count` | Count of incident-report records, including Unfounded and noncriminal highest classifications |
| `violent_npa_year_offense_counts.csv` / `d2_violent_npa_year_offense` | `npa_id` | Positive numeric NPA summary geography ID; boundary vintage unverified |
| | `year` | Published `CALENDAR_YEAR` |
| | `offense_description` | Source offense category |
| | `offense_level` | `broad_category`, `specific_offense`, or `injury_indicator` |
| | `offense_count` | Sum of published monthly counts for that NPA/year/category; missing months are not filled |

The field-level source dictionary is [data_dictionary.csv](../data_preparation/data_dictionary.csv).

## Supabase setup

1. Create or choose a Supabase project and review [supabase_schema.sql](supabase_schema.sql). Run it **once** in that project's SQL Editor. It creates only the two aggregate tables, enables RLS, removes default client grants, and permits `anon` **SELECT only**. If the names already exist, inspect their schema and policies first; the policy statements are not intended to be rerun blindly.
2. Confirm the Data API exposes these tables. In the Table Editor, import `dashboard/data/cmpd_npa_year_counts.csv` into `d2_cmpd_npa_year` and `dashboard/data/violent_npa_year_offense_counts.csv` into `d2_violent_npa_year_offense`. Do not upload the raw or prepared incident-level CSV. These exports are below the dashboard CSV import size limit noted in [Supabase's import guide](https://supabase.com/docs/guides/database/import-data).
3. Check table row counts are 3,779 and 21,367. Verify the unique primary keys and that `anon` can SELECT but cannot write. Use a **publishable key**, never a service-role/secret key, for this dashboard. Supabase requires both RLS policies and table grants for access; see its [RLS guide](https://supabase.com/docs/guides/database/postgres/row-level-security) and [API key guide](https://supabase.com/docs/guides/getting-started/api-keys).

The CSVs are aggregate deliverables, not secrets. Table imports are external writes and are intentionally left for an authorized user.

## Environment variables

| Name | Required | Value |
|---|---|---|
| `SUPABASE_URL` | Yes | Project URL, such as `https://PROJECT.supabase.co` |
| `SUPABASE_PUBLISHABLE_KEY` | Yes | Project publishable key with aggregate table SELECT access through RLS |

Copy [.env.example](.env.example) to a private location for reference. Environment variables take precedence over Streamlit secrets. `.env` and `.streamlit/secrets.toml` are ignored by [dashboard/.gitignore](.gitignore). Never commit real credentials. Do not use `SUPABASE_SECRET_KEY` or `SUPABASE_SERVICE_ROLE_KEY` in the app.

## Local run

Install Python 3.11+ first. The Windows Python launcher currently reports **no installed Pythons** on this machine. From the project root in PowerShell, run:

```powershell
py -0p
Set-Location .\dashboard
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:SUPABASE_URL = 'https://YOUR_PROJECT.supabase.co'
$env:SUPABASE_PUBLISHABLE_KEY = 'YOUR_PUBLISHABLE_KEY'
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

If you install a newer supported Python version instead, replace `-3.11` with that version. The app queries Supabase on demand and paginates past the default 1,000-row API limit described in the [Supabase Python select reference](https://supabase.com/docs/reference/python/select). It requires populated aggregate tables and network access. Local Python/Streamlit execution was not available in the repository environment used to prepare this deliverable.

## Modal deployment, when authorized

The [Modal entry point](modal_app.py) follows Modal's [Streamlit web-server pattern](https://modal.com/docs/examples/serve_streamlit). Once the Supabase tables are populated, install and authenticate Modal locally. In the [Modal Secrets dashboard](https://modal.com/docs/guide/secrets), create a Secret named `charlotte-d2-supabase` with `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY`. This keeps real values out of shell history. Then, from `dashboard/`, run only when authorized:

```powershell
.\.venv\Scripts\python.exe -m modal setup
.\.venv\Scripts\python.exe -m modal serve modal_app.py
.\.venv\Scripts\python.exe -m modal deploy modal_app.py
```

These Modal commands perform external actions; they are **instructions only** and have not been run. `modal serve` is an ephemeral preview; `modal deploy` publishes the app. Only run them with your authorization.

## Visible interpretation limits

The app states that counts are police-reported records or published summaries, not a safety grade or true-crime measure. Reporting, classification, enforcement, geocoding, and omitted summary groups affect the counts. There is no population or exposure denominator. NPA boundary vintage/assignment, CMPD-to-summary offense mapping, and common event-time definitions are unresolved, so cross-source totals and comparisons are not offered. CMPD `Open` is not treated as invalid and `Cleared` is not treated as confirmed criminality.
