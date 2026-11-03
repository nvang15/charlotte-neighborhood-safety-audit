$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$cmpd = Join-Path $project 'data_preparation/cmpd_incidents_clean.csv'
$violent = Join-Path $project 'data_preparation/violent_crime_npa_clean.csv'
if (-not (Test-Path -LiteralPath $cmpd) -or -not (Test-Path -LiteralPath $violent)) { throw 'Prepared source files are required. Run data_preparation/prepare_sources.ps1 first.' }
Add-Type -Path (Join-Path $PSScriptRoot 'AggregateDashboard.cs')
[AggregateDashboard]::Run($cmpd, $violent, (Join-Path $PSScriptRoot 'data'))
