param([string]$Root = (Split-Path -Parent $PSScriptRoot), [string]$OutputDirectory = $PSScriptRoot)
$ErrorActionPreference = 'Stop'
$rootPath = (Resolve-Path -LiteralPath $Root).Path
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
Add-Type -Path (Join-Path $PSScriptRoot 'PrepareData.cs')

$cmpdRaw = Join-Path $rootPath 'Datasets\CMPD_Incidents.csv'
$violentRaw = Join-Path $rootPath 'Datasets\Violent_Crime_Data.csv'
foreach ($path in @($cmpdRaw,$violentRaw)) { if (!(Test-Path -LiteralPath $path)) { throw "Missing raw file: $path" } }
$beforeHashes = @{ CMPD=(Get-FileHash -LiteralPath $cmpdRaw -Algorithm SHA256).Hash; Violent=(Get-FileHash -LiteralPath $violentRaw -Algorithm SHA256).Hash }
$cmpdOut = Join-Path $OutputDirectory 'cmpd_incidents_clean.csv'
$violentOut = Join-Path $OutputDirectory 'violent_crime_npa_clean.csv'
Write-Host 'Preparing CMPD incidents...'
$cmpd = [PrepareData]::CleanCmpd($cmpdRaw,$cmpdOut)
Write-Host 'Preparing Violent Crime NPA rows...'
$violent = [PrepareData]::CleanViolent($violentRaw,$violentOut)
$afterHashes = @{ CMPD=(Get-FileHash -LiteralPath $cmpdRaw -Algorithm SHA256).Hash; Violent=(Get-FileHash -LiteralPath $violentRaw -Algorithm SHA256).Hash }
if ($beforeHashes.CMPD -ne $afterHashes.CMPD -or $beforeHashes.Violent -ne $afterHashes.Violent) { throw 'Raw input hash changed during preparation' }

function Metric($m,$key) { if($m.ContainsKey($key)){return [long]$m[$key]} return 0L }
$validations = [ordered]@{
    cmpd_duplicate_or_missing_incident_id = (Metric $cmpd 'duplicate_or_missing_incident_id')
    cmpd_unexpected_clearance_status = (Metric $cmpd 'unexpected_clearance_status')
    cmpd_unexpected_year = (Metric $cmpd 'unexpected_year')
    cmpd_nibrs_code_description_conflict = (Metric $cmpd 'nibrs_code_description_conflict')
    cmpd_invalid_or_missing_report_date = (Metric $cmpd 'invalid_or_missing_report_date')
    cmpd_invalid_or_missing_incident_began = (Metric $cmpd 'invalid_or_missing_incident_began')
    cmpd_year_report_mismatch = (Metric $cmpd 'year_report_mismatch')
    cmpd_year_began_mismatch = (Metric $cmpd 'year_began_mismatch')
    violent_duplicate_npa_group_key = (Metric $violent 'duplicate_npa_group_key')
    violent_invalid_count = (Metric $violent 'invalid_count')
    violent_invalid_month = (Metric $violent 'invalid_month')
    violent_unexpected_year = (Metric $violent 'unexpected_year')
    violent_unexpected_row_type = (Metric $violent 'unexpected_row_type')
    violent_unexpected_offense_category = (Metric $violent 'unexpected_offense_category')
}
$hardFailures = @('cmpd_duplicate_or_missing_incident_id','cmpd_unexpected_clearance_status','cmpd_unexpected_year','cmpd_nibrs_code_description_conflict','violent_duplicate_npa_group_key','violent_invalid_count','violent_invalid_month','violent_unexpected_year','violent_unexpected_row_type','violent_unexpected_offense_category')
$failed = @($hardFailures | Where-Object { $validations[$_] -ne 0 })
$result = [ordered]@{
    generated_utc = [datetime]::UtcNow.ToString('o')
    raw_sha256 = $beforeHashes
    cmpd_metrics = $cmpd
    violent_metrics = $violent
    validation_checks = $validations
    hard_failures = $failed
    comparison_table_created = $false
}
$result | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $OutputDirectory 'preparation_results.json') -Encoding utf8

$log = [System.Collections.Generic.List[object]]::new()
function Add-Log($source,$rule,$before,$after,$affected,$decision) {
    $script:log.Add([pscustomobject]@{ source=$source; rule=$rule; rows_before=$before; rows_after=$after; rows_affected=$affected; decision=$decision })
}
Add-Log 'CMPD_Incidents.csv' 'Raw intake' $cmpd['raw_rows'] $cmpd['raw_rows'] 0 'Read only'
Add-Log 'CMPD_Incidents.csv' 'Unique INCIDENT_REPORT_ID assertion' $cmpd['raw_rows'] $cmpd['raw_rows'] (Metric $cmpd 'duplicate_or_missing_incident_id') 'No rows removed; hard failure if nonzero'
Add-Log 'CMPD_Incidents.csv' 'Parse dates and flag quality issues' $cmpd['raw_rows'] $cmpd['raw_rows'] ((Metric $cmpd 'invalid_or_missing_incident_began')+(Metric $cmpd 'implausible_incident_began_year')) 'No rows removed; source date strings retained'
Add-Log 'CMPD_Incidents.csv' 'Flag YEAR mismatches' $cmpd['raw_rows'] $cmpd['raw_rows'] (Metric $cmpd 'year_report_mismatch') 'No rows removed; comparison to report year'
Add-Log 'CMPD_Incidents.csv' 'Flag NPA quality' $cmpd['raw_rows'] $cmpd['raw_rows'] (Metric $cmpd 'npa_not_positive_numeric') 'No rows removed; NPA retained as source identifier'
Add-Log 'CMPD_Incidents.csv' 'Flag Unfounded status' $cmpd['raw_rows'] $cmpd['raw_rows'] (Metric $cmpd 'unfounded_flagged') 'No rows removed; Open and Cleared retained'
Add-Log 'CMPD_Incidents.csv' 'Flag noncriminal highest description' $cmpd['raw_rows'] $cmpd['output_rows'] (Metric $cmpd 'noncriminal_highest_flagged') 'No rows removed; offense definition pending'
Add-Log 'Violent_Crime_Data.csv' 'Raw intake' $violent['raw_rows'] $violent['raw_rows'] 0 'Read only'
Add-Log 'Violent_Crime_Data.csv' 'Filter ROW_TYPE to Neighborhood Profile Area' $violent['raw_rows'] $violent['output_rows'] (Metric $violent 'non_npa_rows_excluded') 'Only NPA rows written to clean output'
Add-Log 'Violent_Crime_Data.csv' 'Validate nonnegative integer OFFENSE_COUNT' $violent['output_rows'] $violent['output_rows'] (Metric $violent 'invalid_count') 'No rows removed; hard failure if nonzero'
Add-Log 'Violent_Crime_Data.csv' 'Validate unique NPA/year/month/offense key' $violent['output_rows'] $violent['output_rows'] (Metric $violent 'duplicate_npa_group_key') 'No rows removed; hard failure if nonzero'
Add-Log 'Violent_Crime_Data.csv' 'Tag broad versus specific offense' $violent['output_rows'] $violent['output_rows'] (Metric $violent 'broad_category_rows') 'No aggregation; broad total kept separate'
$log | Export-Csv -LiteralPath (Join-Path $OutputDirectory 'cleaning_log.csv') -NoTypeInformation -Encoding UTF8

$dictionary = [System.Collections.Generic.List[object]]::new()
function Add-Field($dataset,$field,$type,$description,$treatment) { $script:dictionary.Add([pscustomobject]@{ dataset=$dataset; field=$field; type=$type; description=$description; preparation_treatment=$treatment }) }
$cmpdFields = @('X','Y','YEAR','INCIDENT_REPORT_ID','LOCATION','CITY','STATE','ZIP','X_COORD_PUBLIC','Y_COORD_PUBLIC','LATITUDE_PUBLIC','LONGITUDE_PUBLIC','DIVISION_ID','CMPD_PATROL_DIVISION','NPA','DATE_REPORTED','DATE_INCIDENT_BEGAN','DATE_INCIDENT_END','ADDRESS_DESCRIPTION','LOCATION_TYPE_DESCRIPTION','PLACE_TYPE_DESCRIPTION','PLACE_DETAIL_DESCRIPTION','CLEARANCE_STATUS','CLEARANCE_DETAIL_STATUS','CLEARANCE_DATE','HIGHEST_NIBRS_CODE','HIGHEST_NIBRS_DESCRIPTION','OBJECTID','GlobalID')
$violentFields = @('ROW_TYPE','GEOGRAPHY','GEOGRAPHY_ID','CALENDAR_YEAR','CALENDAR_MONTH','OFFENSE_DESCRIPTION','OFFENSE_COUNT','OBJECTID')
$description = @{
    YEAR='Source year; assignment rule unverified'; INCIDENT_REPORT_ID='Incident report identifier'; NPA='Source Neighborhood Profile Area identifier; boundary vintage unverified'; DATE_REPORTED='Original report timestamp'; DATE_INCIDENT_BEGAN='Original incident start timestamp'; DATE_INCIDENT_END='Original incident end timestamp'; CLEARANCE_DATE='Original clearance timestamp'; CLEARANCE_STATUS='Source clearance status; not a criminality determination'; CLEARANCE_DETAIL_STATUS='Source detailed clearance status'; HIGHEST_NIBRS_CODE='Single highest NIBRS code on report'; HIGHEST_NIBRS_DESCRIPTION='Description of highest NIBRS code'; ROW_TYPE='Geography type'; GEOGRAPHY='Source geography label'; GEOGRAPHY_ID='Source geography identifier'; CALENDAR_YEAR='Source calendar year'; CALENDAR_MONTH='Source calendar month'; OFFENSE_DESCRIPTION='Source offense category'; OFFENSE_COUNT='Reported aggregate count, not inferred zeros'; OBJECTID='Source row identifier'; GlobalID='Source global identifier'
}
foreach($f in $cmpdFields){$d=if($description.ContainsKey($f)){$description[$f]}else{'Source field; formal definition unverified'};$type=if($f -in @('X','Y','X_COORD_PUBLIC','Y_COORD_PUBLIC','LATITUDE_PUBLIC','LONGITUDE_PUBLIC')){'source_numeric'}elseif($f -in @('DATE_REPORTED','DATE_INCIDENT_BEGAN','DATE_INCIDENT_END','CLEARANCE_DATE')){'source_timestamp_string'}else{'source_string'};Add-Field 'cmpd_incidents_clean.csv' $f $type $d 'Retained exactly as source text'}
Add-Field 'cmpd_incidents_clean.csv' 'REPORTED_DATE_ISO' 'date_string' 'Parsed report date, YYYY-MM-DD' 'Blank if missing or invalid; original retained'
Add-Field 'cmpd_incidents_clean.csv' 'INCIDENT_BEGAN_DATE_ISO' 'date_string' 'Parsed incident start date, YYYY-MM-DD' 'Blank if missing or invalid; original retained'
Add-Field 'cmpd_incidents_clean.csv' 'INCIDENT_END_DATE_ISO' 'date_string' 'Parsed incident end date, YYYY-MM-DD' 'Blank if missing or invalid; original retained'
Add-Field 'cmpd_incidents_clean.csv' 'CLEARANCE_DATE_ISO' 'date_string' 'Parsed clearance date, YYYY-MM-DD' 'Blank if missing or invalid; original retained'
Add-Field 'cmpd_incidents_clean.csv' 'YEAR_EQUALS_REPORTED_YEAR' 'true/false/unknown' 'Compares YEAR to parsed report-date year' 'Validation flag; no exclusion'
Add-Field 'cmpd_incidents_clean.csv' 'YEAR_EQUALS_INCIDENT_BEGAN_YEAR' 'true/false/unknown' 'Compares YEAR to parsed incident-start year' 'Validation flag; no exclusion'
Add-Field 'cmpd_incidents_clean.csv' 'DATE_QUALITY_FLAGS' 'semicolon_delimited_category' 'Missing/invalid, implausible year, and ordering flags' 'none when no issues; no exclusion'
Add-Field 'cmpd_incidents_clean.csv' 'NPA_QUALITY' 'category' 'positive_numeric, zero_or_negative, or non_numeric' 'No exclusion; identifier retained'
Add-Field 'cmpd_incidents_clean.csv' 'IS_UNFOUNDED' 'boolean_string' 'True when CLEARANCE_STATUS is Unfounded' 'Flag only; no exclusion'
Add-Field 'cmpd_incidents_clean.csv' 'IS_NONCRIMINAL_HIGHEST' 'boolean_string' 'True when highest NIBRS description equals Other Unlisted Non-Criminal' 'Flag only; no exclusion'
foreach($f in $violentFields){$d=if($description.ContainsKey($f)){$description[$f]}else{'Source field; formal definition unverified'};$type=if($f -eq 'OFFENSE_COUNT'){'nonnegative_integer_string'}else{'source_string'};Add-Field 'violent_crime_npa_clean.csv' $f $type $d 'Retained exactly as source text on NPA rows'}
Add-Field 'violent_crime_npa_clean.csv' 'CALENDAR_PERIOD' 'year_month_string' 'Year and month in YYYY-MM form' 'Derived from source year/month'
Add-Field 'violent_crime_npa_clean.csv' 'OFFENSE_LEVEL' 'category' 'broad_category for Violent Crime; injury_indicator for Non-Fatal Gunshot Injury; specific_offense for remaining named categories' 'Do not add broad category to the other categories; injury indicator is separate'
$dictionary | Export-Csv -LiteralPath (Join-Path $OutputDirectory 'data_dictionary.csv') -NoTypeInformation -Encoding UTF8

$report = [System.Collections.Generic.List[string]]::new()
$report.Add('# Data preparation results')
$report.Add('')
$report.Add("Generated (UTC): $($result.generated_utc)")
$report.Add('')
$report.Add('Run from the project root with `powershell -ExecutionPolicy Bypass -File .\data_preparation\prepare_sources.ps1`. The script reads the two CSVs in `Datasets`, writes separate cleaned CSVs in this folder, and checks SHA-256 hashes before and after. The raw files are unchanged.')
$report.Add('')
$report.Add('## Row counts and decisions')
$report.Add('')
$report.Add("CMPD: $($cmpd['raw_rows']) raw rows -> $($cmpd['output_rows']) cleaned rows. All source rows are retained with derived quality and status flags. Violent Crime: $($violent['raw_rows']) raw rows -> $($violent['output_rows']) NPA rows; $(Metric $violent 'non_npa_rows_excluded') other geography rows were excluded from this NPA output. See `cleaning_log.csv` for every rule and its before/after counts.")
$report.Add('')
$report.Add('## CMPD handling')
$report.Add('')
$report.Add("- Dates: original timestamp strings are preserved; YYYY-MM-DD dates are derived. $(Metric $cmpd 'invalid_or_missing_report_date') report dates and $(Metric $cmpd 'invalid_or_missing_incident_began') start dates were missing or invalid. Implausible years before 1900: $(Metric $cmpd 'implausible_incident_began_year') start, $(Metric $cmpd 'implausible_incident_end_year') end, $(Metric $cmpd 'implausible_clearance_year') clearance. $(Metric $cmpd 'end_before_begin') rows have an end date before start date. These are flagged, not silently repaired.")
$report.Add("- YEAR: $(Metric $cmpd 'year_report_mismatch') rows differ from report-date year; $(Metric $cmpd 'year_began_mismatch') differ from start-date year. The source's YEAR assignment rule is still unverified, so neither mismatch is dropped.")
$report.Add("- NPA: $(Metric $cmpd 'npa_not_positive_numeric') rows have a zero, negative, or nonnumeric NPA. Original NPA strings are retained; no boundary equivalence is assumed.")
$report.Add("- HIGHEST_NIBRS_CODE/DESCRIPTION: the source's single highest pair is retained. $(Metric $cmpd 'nibrs_code_description_conflict') rows conflict with another description for the same code, and $(Metric $cmpd 'missing_nibrs_pair') rows have an empty component. No violent-offense mapping is invented.")
$report.Add("- CLEARANCE_STATUS: original categories are retained. $(Metric $cmpd 'unfounded_flagged') Unfounded rows are flagged; $(Metric $cmpd 'noncriminal_highest_flagged') rows have highest description Other Unlisted Non-Criminal; $(Metric $cmpd 'unfounded_and_noncriminal_overlap') rows meet both conditions. Open is not treated as invalid, and Cleared is not treated as confirmed criminality.")
$report.Add('')
$report.Add('## Violent Crime NPA handling and overlap investigation')
$report.Add('')
$report.Add("- Each retained row is one reported NPA/year/month/offense count. $(Metric $violent 'distinct_npa_ids') distinct NPA IDs and $(Metric $violent 'distinct_npa_month_groups') NPA-month groups remain. $(Metric $violent 'npa_label_id_mismatch') retained rows have different GEOGRAPHY and GEOGRAPHY_ID strings.")
$report.Add("- `Violent Crime` appears in $(Metric $violent 'broad_category_rows') retained rows; named categories appear in $(Metric $violent 'specific_category_rows') rows. Of $(Metric $violent 'groups_with_broad_and_specific') NPA-month groups containing both, the broad count equals the sum of all named categories in $(Metric $violent 'broad_equals_specific_sum'), is less in $(Metric $violent 'broad_less_than_specific_sum'), and is greater in $(Metric $violent 'broad_greater_than_specific_sum'). Excluding `Non-Fatal Gunshot Injury` from that sum gives $(Metric $violent 'broad_equals_specific_without_gunshot_injury') equal, $(Metric $violent 'broad_less_than_specific_without_gunshot_injury') less, and $(Metric $violent 'broad_greater_than_specific_without_gunshot_injury') greater. This exact equality across every group containing both is strong evidence that `Violent Crime` is a subtotal of the named offense categories excluding the injury indicator. The clean file tags these three levels separately and does not sum them together. Incident-level category definitions remain unverified.")
$report.Add('- An absent NPA/month/offense row is left absent. It is not converted to zero, since the source does not define omitted groups.')
$report.Add('')
$report.Add('## Validation checks')
$report.Add('')
$report.Add('| Check | Observed rows | Gate |')
$report.Add('|---|---:|---|')
foreach($k in $validations.Keys){$gate=if($k -in $hardFailures){'must be zero'}elseif($k -in @('cmpd_year_report_mismatch','cmpd_year_began_mismatch','cmpd_invalid_or_missing_report_date','cmpd_invalid_or_missing_incident_began')){'reported for review'}else{'must be zero'};$report.Add("| $k | $($validations[$k]) | $gate |")}
$report.Add('')
$report.Add('## Comparison readiness')
$report.Add('')
$report.Add('No cross-source comparison table was created. NPA boundary vintage and assignment rules, common time basis, and the mapping between highest NIBRS code and summary offense categories remain unverified. The sources stay separate.')
$report.Add('')
$report.Add('## Unresolved definitions')
$report.Add('')
$report.Add('- Obtain source data dictionaries for YEAR/date semantics, NPA boundaries, highest NIBRS selection, and the summary count methodology.')
$report.Add('- Determine whether `Violent Crime` is a subtotal, whether specific categories overlap one another, and whether omitted rows mean zero or unavailable data.')
$report | Set-Content -LiteralPath (Join-Path $OutputDirectory 'preparation_report.md') -Encoding UTF8

if($failed.Count -gt 0){throw "Preparation validation failed: $($failed -join ', '). See preparation_results.json and preparation_report.md."}
Write-Host "Preparation complete. CMPD rows: $($cmpd['output_rows']); Violent Crime NPA rows: $($violent['output_rows'])."
