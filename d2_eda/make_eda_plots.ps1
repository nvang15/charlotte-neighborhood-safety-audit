param([string]$Root = (Split-Path -Parent $PSScriptRoot), [string]$OutputDirectory = $PSScriptRoot)
$ErrorActionPreference = 'Stop'
$rootPath = (Resolve-Path -LiteralPath $Root).Path
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms.DataVisualization
Add-Type -Path (Join-Path $PSScriptRoot 'EdaData.cs')
$cmpdPath = Join-Path $rootPath 'data_preparation\cmpd_incidents_clean.csv'
$violentPath = Join-Path $rootPath 'data_preparation\violent_crime_npa_clean.csv'
foreach($p in @($cmpdPath,$violentPath)){if(!(Test-Path -LiteralPath $p)){throw "Missing prepared input: $p"}}
Write-Host 'Summarizing prepared sources for EDA...'
$s=[EdaData]::Load($cmpdPath,$violentPath)

function New-Chart($width,$height,$title){
    $ch=New-Object System.Windows.Forms.DataVisualization.Charting.Chart
    $ch.Width=$width;$ch.Height=$height;$ch.BackColor=[Drawing.Color]::White
    $t=$ch.Titles.Add($title);$t.Font=New-Object Drawing.Font('Segoe UI',18,[Drawing.FontStyle]::Bold);$t.ForeColor=[Drawing.Color]::FromArgb(35,44,58)
    return $ch
}
function New-Area($name,$x,$y,$width,$height,$xTitle,$yTitle){
    $a=New-Object System.Windows.Forms.DataVisualization.Charting.ChartArea($name)
    $a.Position=New-Object System.Windows.Forms.DataVisualization.Charting.ElementPosition($x,$y,$width,$height)
    $a.BackColor=[Drawing.Color]::White
    $a.AxisX.Title=$xTitle;$a.AxisY.Title=$yTitle
    $a.AxisX.TitleFont=New-Object Drawing.Font('Segoe UI',11)
    $a.AxisY.TitleFont=New-Object Drawing.Font('Segoe UI',11)
    $a.AxisX.LabelStyle.Font=New-Object Drawing.Font('Segoe UI',10)
    $a.AxisY.LabelStyle.Font=New-Object Drawing.Font('Segoe UI',10)
    $a.AxisX.MajorGrid.Enabled=$false
    $a.AxisY.MajorGrid.LineColor=[Drawing.Color]::FromArgb(225,230,235)
    return $a
}
function Add-PanelTitle($chart,$areaName,$text){
    $t=New-Object System.Windows.Forms.DataVisualization.Charting.Title
    $t.Text=$text;$t.DockedToChartArea=$areaName;$t.Docking='Top';$t.IsDockedInsideChartArea=$false
    $t.Font=New-Object Drawing.Font('Segoe UI',13,[Drawing.FontStyle]::Bold)
    [void]$chart.Titles.Add($t)
}
function Add-Series($chart,$name,$area,$type,$color){
    $series=New-Object System.Windows.Forms.DataVisualization.Charting.Series($name)
    $series.ChartArea=$area;$series.ChartType=$type;$series.Color=$color;$series.BorderWidth=3
    [void]$chart.Series.Add($series)
    return $series
}
function Save-Chart($chart,$name){
    $path=Join-Path $OutputDirectory $name
    $chart.SaveImage($path,[System.Windows.Forms.DataVisualization.Charting.ChartImageFormat]::Png)
    $chart.Dispose()
    return $path
}

# 1. Coverage by source. Panel scales and units are separate.
$coverage=New-Chart 1700 1000 'Record coverage by year and source (2026 incomplete)'
$a1=New-Area 'cmpd' 7 10 88 38 'Report year' 'CMPD report records'
$a1.AxisX.Minimum=2016.5;$a1.AxisX.Maximum=2026.5;$a1.AxisX.Interval=1;$a1.AxisX.IntervalOffset=0.5;$a1.AxisY.Minimum=0
[void]$coverage.ChartAreas.Add($a1)
$a2=New-Area 'violent' 7 54 88 38 'Calendar year' 'NPA summary rows'
$a2.AxisX.Minimum=2014.5;$a2.AxisX.Maximum=2026.5;$a2.AxisX.Interval=1;$a2.AxisX.IntervalOffset=0.5;$a2.AxisY.Minimum=0
[void]$coverage.ChartAreas.Add($a2)
Add-PanelTitle $coverage 'cmpd' 'CMPD incident report file, 2017–2026'
Add-PanelTitle $coverage 'violent' 'Violent Crime NPA summary file, 2015–2026'
$sc=Add-Series $coverage 'CMPD rows' 'cmpd' 'Column' ([Drawing.Color]::FromArgb(31,102,154))
foreach($year in @($s.CmpdYearRows.Keys|Sort-Object)){ $i=$sc.Points.AddXY($year,$s.CmpdYearRows[$year]);if($year -eq 2026){$sc.Points[$i].Color=[Drawing.Color]::FromArgb(150,150,150)} }
$sv=Add-Series $coverage 'NPA summary rows' 'violent' 'Column' ([Drawing.Color]::FromArgb(54,126,96))
foreach($year in @($s.ViolentNpaYearRows.Keys|Sort-Object)){ $i=$sv.Points.AddXY($year,$s.ViolentNpaYearRows[$year]);if($year -eq 2026){$sv.Points[$i].Color=[Drawing.Color]::FromArgb(150,150,150)} }
$coverageFile=Save-Chart $coverage '01_source_coverage.png'

# 2. NPA distribution. Each year is ranked independently; only positive numeric NPA values are plotted.
$rank=New-Chart 1700 900 'CMPD report counts by NPA rank, 2023–2025'
$ar=New-Area 'rank' 7 12 87 78 'NPA rank within year (highest count first)' 'Report records per NPA (log scale)'
$ar.AxisX.Minimum=1;$ar.AxisX.Interval=50;$ar.AxisY.IsLogarithmic=$true;$ar.AxisY.Minimum=1
[void]$rank.ChartAreas.Add($ar)
$legend=New-Object System.Windows.Forms.DataVisualization.Charting.Legend('year');$legend.Docking='Bottom';$legend.Font=New-Object Drawing.Font('Segoe UI',11);[void]$rank.Legends.Add($legend)
$colors=@{2023=[Drawing.Color]::FromArgb(31,102,154);2024=[Drawing.Color]::FromArgb(217,119,6);2025=[Drawing.Color]::FromArgb(132,77,150)}
$npaStats=[ordered]@{}
foreach($year in @(2023,2024,2025)){
    $vals=@($s.CmpdNpaYearRows.Keys|Where-Object { $_.StartsWith("$year|",[StringComparison]::Ordinal) }|ForEach-Object { [long]$s.CmpdNpaYearRows[$_] }|Sort-Object -Descending)
    if($vals.Count -eq 0){throw "No positive-NPA CMPD rows in $year"}
    $sr=Add-Series $rank "$year" 'rank' 'FastLine' $colors[$year]
    for($i=0;$i -lt $vals.Count;$i++){[void]$sr.Points.AddXY(($i+1),$vals[$i])}
    $topN=[math]::Ceiling($vals.Count/10.0)
    $total=($vals|Measure-Object -Sum).Sum
    $top=($vals|Select-Object -First $topN|Measure-Object -Sum).Sum
    $medianIndex=[int][math]::Floor(($vals.Count-1)/2)
    $lastIndex=$vals.Count-1
    $npaStats["$year"]=[ordered]@{observed_npas=$vals.Count;total_records=$total;top_decile_share_pct=[math]::Round(100*$top/$total,1);median_npa_records=$vals[$medianIndex];max_npa_records=$vals[0];min_npa_records=$vals[$lastIndex]}
}
$rankFile=Save-Chart $rank '02_cmpd_npa_rank.png'

# 3. Composition from named offense categories only; broad subtotal and injury indicator are excluded.
$composition=New-Chart 1700 900 'Composition of reported NPA violent-offense counts, 2015–2025'
$ac=New-Area 'composition' 7 12 87 76 'Calendar year' 'Share of named-offense counts (%)'
$ac.AxisX.Minimum=2014.5;$ac.AxisX.Maximum=2025.5;$ac.AxisX.Interval=1;$ac.AxisX.IntervalOffset=0.5;$ac.AxisY.Minimum=0;$ac.AxisY.Maximum=100;$ac.AxisY.Interval=20
[void]$composition.ChartAreas.Add($ac)
$cl=New-Object System.Windows.Forms.DataVisualization.Charting.Legend('offenses');$cl.Docking='Bottom';$cl.Font=New-Object Drawing.Font('Segoe UI',10);[void]$composition.Legends.Add($cl)
$groups=@('Aggravated assault','Robbery','Rape / attempted rape','Homicide')
$groupColors=@([Drawing.Color]::FromArgb(40,103,166),[Drawing.Color]::FromArgb(213,113,43),[Drawing.Color]::FromArgb(117,78,153),[Drawing.Color]::FromArgb(61,145,114))
$offenseTotals=[ordered]@{}
for($j=0;$j -lt $groups.Count;$j++){
    $group=$groups[$j];$sr=Add-Series $composition $group 'composition' 'StackedColumn100' $groupColors[$j]
    foreach($year in 2015..2025){$key="$year|$group";$value=if($s.ViolentOffenseGroupCount.ContainsKey($key)){$s.ViolentOffenseGroupCount[$key]}else{0};[void]$sr.Points.AddXY($year,$value);if(!$offenseTotals.Contains("$year")){$offenseTotals["$year"]=0L};$offenseTotals["$year"]+=$value}
}
$compositionFile=Save-Chart $composition '03_npa_offense_composition.png'

# 4. Source-field missingness (empty CSV fields only).
$missing=New-Chart 1700 900 'CMPD source-field missingness, 2017–2026'
$am=New-Area 'missing' 7 12 87 78 'Source field' 'Records with empty field (%)'
$am.AxisY.Minimum=0;$am.AxisY.Maximum=70;$am.AxisY.Interval=10;$am.AxisX.LabelStyle.Angle=-25
[void]$missing.ChartAreas.Add($am)
$sm=Add-Series $missing 'Missing' 'missing' 'Column' ([Drawing.Color]::FromArgb(31,102,154))
$sm.IsValueShownAsLabel=$true;$sm.LabelFormat='0.00';$sm.Font=New-Object Drawing.Font('Segoe UI',10)
$missingFields=[ordered]@{'ZIP'='ZIP';'Incident end date'='DATE_INCIDENT_END';'Clearance date'='CLEARANCE_DATE';'State'='STATE';'Incident start date'='DATE_INCIDENT_BEGAN';'Report date'='DATE_REPORTED'}
$missingPct=[ordered]@{}
foreach($label in $missingFields.Keys){$field=$missingFields[$label];$num=if($s.CmpdMissing.ContainsKey($field)){$s.CmpdMissing[$field]}else{0L};$pct=100.0*$num/$s.CmpdRows;$missingPct[$label]=[math]::Round($pct,4);[void]$sm.Points.AddXY($label,$pct)}
$missingFile=Save-Chart $missing '04_cmpd_missingness.png'

$cmpdYears=[ordered]@{};foreach($year in @($s.CmpdYearRows.Keys|Sort-Object)){$cmpdYears["$year"]=$s.CmpdYearRows[$year]}
$violentYears=[ordered]@{};foreach($year in @($s.ViolentNpaYearRows.Keys|Sort-Object)){$violentYears["$year"]=$s.ViolentNpaYearRows[$year]}
$plotData=[ordered]@{cmpd_report_date_range=@($s.CmpdMinReported,$s.CmpdMaxReported);violent_npa_period_range=@($s.ViolentMinPeriod,$s.ViolentMaxPeriod);cmpd_year_rows=$cmpdYears;violent_npa_year_rows=$violentYears;cmpd_npa_rank_summary=$npaStats;cmpd_npa_rows_excluded_for_rank=$s.CmpdExcludedNpaQuality;violent_named_offense_year_totals=$offenseTotals;cmpd_missing_pct=$missingPct}
$plotData|ConvertTo-Json -Depth 10|Set-Content -LiteralPath (Join-Path $OutputDirectory 'plot_data.json') -Encoding UTF8

$topShare=$npaStats['2025'].top_decile_share_pct
$report=@"
# D2 exploratory data analysis

These plots use the prepared source files, with no model or safety label. A "record" in the CMPD file is an incident report row; a row in the Violent Crime file is an already aggregated NPA/month/offense observation. The two sources are shown separately because NPA boundary vintage, common timing, and offense crosswalks have not been verified. Plot data and the script are in this folder.

Reproduce from the project root with: powershell -ExecutionPolicy Bypass -File .\d2_eda\make_eda_plots.ps1

## 1. Record coverage by year and source

![Record coverage by year and source](01_source_coverage.png)

**Title:** Record coverage by year and source (2026 incomplete). **Axes/units:** X = year; Y = CMPD report records (top panel) or Violent Crime NPA summary rows (bottom panel). **Source/date range:** cmpd_incidents_clean.csv, $($s.CmpdMinReported) to $($s.CmpdMaxReported); violent_crime_npa_clean.csv, $($s.ViolentMinPeriod) to $($s.ViolentMaxPeriod). Gray 2026 bars are incomplete: CMPD reports run through October 30, while the NPA summary has January–March only.

**Interpretation:** The files cover different starting years and have sharply different 2026 coverage. The bar heights show how many rows are available, not comparable offense volume.

**Limitation:** Row units differ across sources, and the summary may omit zero-count groups; the panels must not be read as a rate or cross-source comparison.

## 2. CMPD report-count distribution across NPAs

![CMPD report counts by NPA rank](02_cmpd_npa_rank.png)

**Title:** CMPD report counts by NPA rank, 2023–2025. **Axes/units:** X = rank of observed NPA within each year; Y = report records per NPA, logarithmic scale. **Source/date range:** cmpd_incidents_clean.csv, report years 2023–2025. Only positive numeric NPA identifiers are plotted; $($s.CmpdExcludedNpaQuality) rows with other NPA values in those years were excluded from this plot.

**Interpretation:** Counts are strongly uneven across NPAs. In 2025, the highest-count 10% of observed NPAs account for $topShare% of plotted report records; the median NPA has $($npaStats['2025'].median_npa_records) records.

**Limitation:** These are report counts without population or exposure denominators; they retain rows flagged as unfounded or noncriminal in the prepared file. NPA boundary comparability over time is unverified. The ranking changes independently each year and does not identify the same NPA across curves.

## 3. NPA violent-offense composition over time

![NPA offense composition by year](03_npa_offense_composition.png)

**Title:** Composition of reported NPA violent-offense counts, 2015–2025. **Axes/units:** X = calendar year; Y = percent of summed named-offense counts. **Source/date range:** violent_crime_npa_clean.csv, NPA rows for 2015–2025. The broad Violent Crime subtotal and Non-Fatal Gunshot Injury indicator are excluded; 2026 is omitted because it contains January–March only.

**Interpretation:** Aggravated assault makes up the largest share of reported named-offense counts across these years. The chart shows category mix rather than the overall count level.

**Limitation:** Summing reported NPA counts assumes their geographic coverage is suitable for this description; boundary vintage, omitted zero groups, and official category definitions are not yet documented. It does not establish a population-adjusted rate.

## 4. CMPD source-field missingness

![CMPD source-field missingness](04_cmpd_missingness.png)

**Title:** CMPD source-field missingness, 2017–2026. **Axes/units:** X = source field; Y = percent of report records with an empty CSV field. **Source/date range:** cmpd_incidents_clean.csv, report dates $($s.CmpdMinReported) to $($s.CmpdMaxReported), including incomplete 2026.

**Interpretation:** Clearance date is empty in $($missingPct['Clearance date'])% of records, ZIP in $($missingPct['ZIP'])%, and incident end date in $($missingPct['Incident end date'])%. The prepared file retains these blanks and records separate date-quality flags.

**Limitation:** An empty clearance or end date may be structurally inapplicable for some reports; this chart does not treat missingness as evidence of an invalid record.

## Comparison decision

No CMPD-versus-summary comparison plot was produced. The source audit and preparation report still list unresolved NPA boundary, time-basis, and offense-definition questions. The files remain separate, and no absent group was filled with an invented zero.
"@
$report|Set-Content -LiteralPath (Join-Path $OutputDirectory 'D2_EDA_report.md') -Encoding UTF8
Write-Host 'Saved four PNG plots and D2_EDA_report.md'

