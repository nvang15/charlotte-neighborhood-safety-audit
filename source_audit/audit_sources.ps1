param([string]$Root = (Split-Path -Parent $PSScriptRoot), [string]$OutputDirectory = $PSScriptRoot)
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

Add-Type -TypeDefinition @'
using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Globalization;
using System.Collections.Generic;

public static class CsvAudit {
  static string[] Parse(string line) {
    var cells = new List<string>(); var b = new StringBuilder(); bool quoted = false;
    for (int i=0;i<line.Length;i++) { char c=line[i];
      if (quoted) { if (c=='"' && i+1<line.Length && line[i+1]=='"') { b.Append('"'); i++; } else if(c=='"') quoted=false; else b.Append(c); }
      else if(c=='"') quoted=true; else if(c==',') { cells.Add(b.ToString()); b.Clear(); } else b.Append(c);
    }
    cells.Add(b.ToString()); return cells.ToArray();
  }
  static Dictionary<string,object> Col(string name) { return new Dictionary<string,object>{{"field",name},{"nonmissing",0L},{"missing",0L},{"values",new HashSet<string>(StringComparer.Ordinal)},{"numeric",true},{"date",true},{"minNumeric",null},{"maxNumeric",null},{"minDate",null},{"maxDate",null}}; }
  public static Dictionary<string,object> Run(string path, string[] freqFields, string[][] keyFields) {
    using(var rd=new StreamReader(path, Encoding.UTF8, true, 1<<20)) {
      var header=Parse(rd.ReadLine()); var stats=header.Select(h=>Col(h)).ToArray();
      var freq=new Dictionary<string,Dictionary<string,long>>(); foreach(var f in freqFields) freq[f]=new Dictionary<string,long>(StringComparer.Ordinal);
      var keys=new List<HashSet<string>>(); var keyCounts=new long[keyFields.Length]; var missCounts=new long[keyFields.Length]; var keyIdx=keyFields.Select(k=>k.Select(n=>Array.IndexOf(header,n)).ToArray()).ToArray();
      for(int k=0;k<keyIdx.Length;k++){ if(keyIdx[k].Any(i=>i<0)) throw new Exception("Configured key field is absent: "+String.Join(",",keyFields[k])); keys.Add(new HashSet<string>(StringComparer.Ordinal)); }
      var coverage=new Dictionary<string,long>(StringComparer.Ordinal);
      int reportDateIdx=Array.IndexOf(header,"DATE_REPORTED"), calYearIdx=Array.IndexOf(header,"CALENDAR_YEAR"), calMonthIdx=Array.IndexOf(header,"CALENDAR_MONTH");
      long rows=0; string line;
      while((line=rd.ReadLine())!=null) {
        var f=Parse(line); if(f.Length!=header.Length) throw new Exception("Wrong field count at data row "+(rows+1)+": "+f.Length+" instead of "+header.Length); rows++;
        for(int i=0;i<f.Length;i++) { var s=stats[i]; var v=f[i]; if(v.Length==0){s["missing"]=(long)s["missing"]+1;continue;} s["nonmissing"]=(long)s["nonmissing"]+1; ((HashSet<string>)s["values"]).Add(v);
          double d; if(Double.TryParse(v,NumberStyles.Float,CultureInfo.InvariantCulture,out d)){if(s["minNumeric"]==null || d<(double)s["minNumeric"])s["minNumeric"]=d;if(s["maxNumeric"]==null || d>(double)s["maxNumeric"])s["maxNumeric"]=d;} else s["numeric"]=false;
          if(header[i].IndexOf("DATE",StringComparison.OrdinalIgnoreCase)>=0 || header[i].IndexOf("TIME",StringComparison.OrdinalIgnoreCase)>=0) { DateTime dt; string normalized=v.EndsWith("+00",StringComparison.Ordinal)?v.Substring(0,v.Length-3):v; bool ok=DateTime.TryParseExact(normalized,new[]{"yyyy/MM/dd HH:mm:ss","yyyy-MM-dd HH:mm:ss","yyyy/MM/dd","yyyy-MM-dd"},CultureInfo.InvariantCulture,DateTimeStyles.AssumeUniversal,out dt); if(!ok)ok=DateTime.TryParse(normalized,CultureInfo.InvariantCulture,DateTimeStyles.AssumeUniversal,out dt); if(ok){if(s["minDate"]==null || dt<(DateTime)s["minDate"])s["minDate"]=dt;if(s["maxDate"]==null || dt>(DateTime)s["maxDate"])s["maxDate"]=dt;}else s["date"]=false; }
        }
        foreach(var name in freqFields){string v=f[Array.IndexOf(header,name)];long n;freq[name].TryGetValue(v,out n);freq[name][v]=n+1;}
        string period=null;
        if(reportDateIdx>=0 && f[reportDateIdx].Length>=7)period=f[reportDateIdx].Substring(0,7).Replace('/','-');
        else if(calYearIdx>=0 && calMonthIdx>=0)period=f[calYearIdx]+"-"+f[calMonthIdx].PadLeft(2,'0');
        if(period!=null){long n;coverage.TryGetValue(period,out n);coverage[period]=n+1;}
        for(int k=0;k<keyIdx.Length;k++){var vals=keyIdx[k].Select(i=>f[i]).ToArray();if(vals.Any(String.IsNullOrEmpty)){missCounts[k]++;continue;}if(!keys[k].Add(String.Join("\u001f",vals)))keyCounts[k]++;}
      }
      var columns=new List<Dictionary<string,object>>();
      for(int i=0;i<header.Length;i++){var s=stats[i];bool empty=(long)s["nonmissing"]==0;string type=empty?"all_missing":(bool)s["numeric"]?"numeric":(header[i].IndexOf("DATE",StringComparison.OrdinalIgnoreCase)>=0 || header[i].IndexOf("TIME",StringComparison.OrdinalIgnoreCase)>=0) && (bool)s["date"]?"datetime":"string/category";
        columns.Add(new Dictionary<string,object>{{"field",header[i]},{"inferred_type",type},{"missing",s["missing"]},{"missing_pct",Math.Round(100.0*(long)s["missing"]/Math.Max(1,rows),4)},{"unique_count",((HashSet<string>)s["values"]).Count},{"min_numeric",s["minNumeric"]},{"max_numeric",s["maxNumeric"]},{"min_date",s["minDate"]},{"max_date",s["maxDate"]}});}
      var freqOut=new Dictionary<string,object>();foreach(var name in freqFields)freqOut[name]=freq[name].OrderByDescending(x=>x.Value).ThenBy(x=>x.Key).Take(25).Select(x=>new Dictionary<string,object>{{"value",x.Key},{"count",x.Value}}).ToArray();
      var keyOut=new List<Dictionary<string,object>>();for(int k=0;k<keyIdx.Length;k++)keyOut.Add(new Dictionary<string,object>{{"fields",keyFields[k]},{"duplicate_rows",keyCounts[k]},{"distinct_nonmissing_keys",keys[k].Count},{"rows_with_missing_key",missCounts[k]}});
      return new Dictionary<string,object>{{"rows",rows},{"columns_count",header.Length},{"columns",columns},{"key_checks",keyOut},{"frequencies",freqOut},{"temporal_coverage",coverage.OrderBy(x=>x.Key).Select(x=>new Dictionary<string,object>{{"period",x.Key},{"rows",x.Value}}).ToArray()}};
    }
  }
}
'@

$rootPath = (Resolve-Path -LiteralPath $Root).Path
$specs = @(
  @{ Name='CMPD_Incidents.csv'; Path=(Join-Path $rootPath 'Datasets\CMPD_Incidents.csv'); Keys=@(@('INCIDENT_REPORT_ID'),@('GlobalID'),@('OBJECTID')); Freq=@('YEAR','CITY','STATE','CMPD_PATROL_DIVISION','NPA','CLEARANCE_STATUS','CLEARANCE_DETAIL_STATUS','HIGHEST_NIBRS_CODE','HIGHEST_NIBRS_DESCRIPTION','LOCATION_TYPE_DESCRIPTION','PLACE_TYPE_DESCRIPTION') },
  @{ Name='Violent_Crime_Data.csv'; Path=(Join-Path $rootPath 'Datasets\Violent_Crime_Data.csv'); Keys=@(@('OBJECTID'),@('ROW_TYPE','GEOGRAPHY','GEOGRAPHY_ID','CALENDAR_YEAR','CALENDAR_MONTH','OFFENSE_DESCRIPTION')); Freq=@('ROW_TYPE','GEOGRAPHY','OFFENSE_DESCRIPTION','CALENDAR_YEAR','CALENDAR_MONTH') }
)
$audits = @()
foreach($s in $specs){if(!(Test-Path -LiteralPath $s.Path)){throw "Missing input: $($s.Path)"};Write-Host "Auditing $($s.Name)...";$a=[CsvAudit]::Run($s.Path,[string[]]$s.Freq,[string[][]]$s.Keys);$a.file=$s.Name;$a.source_path=$s.Path;$audits+=,$a}
$result=[ordered]@{generated_utc=[datetime]::UtcNow.ToString('o');audit_script='audit_sources.ps1';missingness_definition='Empty CSV fields only';inputs=$audits}
$jsonPath=Join-Path $OutputDirectory 'audit_results.json';$result|ConvertTo-Json -Depth 12|Set-Content -LiteralPath $jsonPath -Encoding utf8
$lines=[System.Collections.Generic.List[string]]::new()
$lines.Add('# Source audit: Rated for Whom? Auditing Neighborhood Safety Scores in Charlotte');$lines.Add('');$lines.Add("Generated (UTC): $($result.generated_utc)");$lines.Add('');$lines.Add('## Reproduction and scope');$lines.Add('');$lines.Add('Run from the project root with `powershell -ExecutionPolicy Bypass -File .\source_audit\audit_sources.ps1`. The script reads the raw CSV files under `Datasets` and writes `audit_results.json`; it does not edit or combine source files. The requested `upload` directory was absent, so the matching files in `Datasets` were used.');$lines.Add('');$lines.Add('Empty CSV fields are counted as missing; text such as `Unknown`, `N/A`, and zero is retained as a value. Numeric inference requires all nonempty field values to parse as numbers. Numeric-looking codes can therefore appear numeric and must be treated as categorical identifiers where appropriate. Date parsing/ranges apply to fields with `DATE` or `TIME` in their names.')
foreach($a in $audits){$lines.Add('');$lines.Add("## $($a.file)");$lines.Add('');$lines.Add("Rows: $($a.rows); columns: $($a.columns_count).");$lines.Add('');$lines.Add('| Field | Inferred type | Missing | Unique | Observed range |');$lines.Add('|---|---|---:|---:|---|');foreach($c in $a.columns){$range='';if($c.inferred_type -eq 'datetime' -and $null-ne$c.min_date){$range="$($c.min_date) to $($c.max_date)"}elseif($c.inferred_type -eq 'numeric' -and $null-ne$c.min_numeric){$range="$($c.min_numeric) to $($c.max_numeric)"};$lines.Add("| $($c.field) | $($c.inferred_type) | $($c.missing) ($($c.missing_pct)%) | $($c.unique_count) | $range |")};$lines.Add('');$lines.Add('### Duplicate identifier and key checks');$lines.Add('');foreach($k in $a.key_checks){$names=($k['fields'] -join ', ');$lines.Add("- ``$names``: $($k.duplicate_rows) repeated nonmissing keys; $($k.distinct_nonmissing_keys) distinct nonmissing keys; $($k.rows_with_missing_key) rows with a missing key component.")};$lines.Add('');$lines.Add('### Latest-year month coverage');$lines.Add('');$latest=($a.temporal_coverage|ForEach-Object{$_.period.Substring(0,4)}|Sort-Object -Unique|Select-Object -Last 1);$lines.Add("Observed rows by month for $latest (CMPD uses `DATE_REPORTED`; summary uses `CALENDAR_YEAR`/`CALENDAR_MONTH`):");$lines.Add('');$lines.Add('| Month | Rows |');$lines.Add('|---|---:|');foreach($p in $a.temporal_coverage){if($p.period.StartsWith($latest)){$lines.Add("| $($p.period.Substring(5,2)) | $($p.rows) |")}};$lines.Add('');$lines.Add('### Important category frequencies (top 25)');$lines.Add('');foreach($field in $a.frequencies.Keys){$lines.Add("**$field**");$lines.Add('');$lines.Add('| Value | Rows |');$lines.Add('|---|---:|');foreach($e in $a.frequencies[$field]){$lines.Add("| $($e.value) | $($e.count) |")};$lines.Add('')}}
$lines.Add('## Verified source facts')
$lines.Add('')
$lines.Add('- CMPD has one unique `INCIDENT_REPORT_ID` per row and incident dates, location, clearance, and one highest NIBRS code/description. It is an incident-report table. The summary has one unique geography/year/month/offense combination per row and an `OFFENSE_COUNT` field, so it is already aggregated.')
$lines.Add('- CMPD offers public coordinates, ZIP, patrol division, and `NPA`; the summary has four `ROW_TYPE` values, including `Neighborhood Profile Area`, plus `GEOGRAPHY` and `GEOGRAPHY_ID`. The incident file contains 451 distinct NPA values; the summary has 418 distinct IDs in its NPA row type.')
$lines.Add('- CMPD offers report, incident began/end, and clearance dates; the summary uses calendar year and month. CMPD reported dates cover 2017-01-01 through 2026-10-30. The summary spans 2015 through 2026, with 2026 rows only in January through March. The latest-year month tables above make this difference explicit.')
$lines.Add('- CMPD has 30,714 `CLEARANCE_STATUS = Unfounded` rows and 84,239 `HIGHEST_NIBRS_DESCRIPTION = Other Unlisted Non-Criminal` rows. These counts should not be added because the groups may overlap. Some incident begin/end and clearance values have implausible years such as 0200–0202; the date ranges above show them.')
$lines.Add('- The summary contains both `Violent Crime` and named offense categories. Its `OFFENSE_COUNT` values range from 1 to 891, with no explicit zero-count rows.')
$lines.Add('')
$lines.Add('## Assumptions and analytical risks')
$lines.Add('')
$lines.Add('- A shared numeric NPA identifier does not establish matching boundaries or vintages. The two sources may use different NPA coverage or assignment rules. Confirm the crosswalk and geography versions before comparing neighborhood values.')
$lines.Add('- CMPD `YEAR` may follow report year or incident year; the CSV does not define it. Report date and occurrence date are different concepts. The timestamp suffix `+00` suggests a UTC offset, but timezone and date assignment rules require documentation.')
$lines.Add('- CMPD records only a highest NIBRS code on each row, while the summary uses broader named categories. A highest code can omit secondary offenses. The summary `Violent Crime` category may overlap its named categories; category exclusivity and whether counts represent incidents or offense occurrences are unverified.')
$lines.Add('- `Unfounded` and noncriminal labels require an explicit inclusion rule. The observed counts alone do not show the overlap between those groups or which categories the summary excludes. Excluding every record with a broad label could change the target population.')
$lines.Add('- The two 2026 windows differ, and a year with observed rows is not proof of complete coverage. Missing geography/month/offense groups may mean zero, suppression, or absent data; the file does not say which.')
$lines.Add('')
$lines.Add('## Recommended cleaning decisions')
$lines.Add('')
$lines.Add('- Preserve originals. Parse dates into derived typed columns while retaining source strings. Flag implausible years and decide their handling with a documented rule. Choose an occurrence-date convention only after confirming source semantics.')
$lines.Add('- Treat report IDs and aggregate dimensions as keys. If future extracts have repeats, investigate before deduplication. Keep numeric-looking ZIP, NPA, and geography codes as identifiers.')
$lines.Add('- Normalize whitespace and category spelling only in derived columns. Keep zero distinct from missing; do not fill absent summary groups with zero without source confirmation.')
$lines.Add('- Before a score comparison, document an offense inclusion list, complete common time window, geography boundary vintage/crosswalk, and denominator. Keep both sources separate until those definitions are settled.')
$lines.Add('')
$lines.Add('## Unresolved questions')
$lines.Add('')
$lines.Add('- What are the provenance, extraction dates, and data dictionaries for the two files? The project root has no README or `AGENTS.md`.')
$lines.Add('- Does CMPD `YEAR` mean incident year or report year? What timezone/date rules govern incident began/end, and how should malformed years be handled?')
$lines.Add('- Which noncriminal and unfounded records belong in the analysis population? Does the summary exclude them?')
$lines.Add('- Are summary offense categories mutually exclusive? What does `OFFENSE_COUNT` count? Does an absent group mean zero or missing?')
$lines.Add('- Which boundary vintage defines each summary NPA and CMPD NPA? Why do the files contain different numbers of distinct NPA identifiers?')
$lines.Add('- Were the intended inputs expected in `upload`? That folder was absent; confirm that `Datasets` contains the intended D2 copies.')
$lines.Add('')
$lines.Add('## Repository inspection')
$lines.Add('')
$lines.Add('The project root contains `Datasets/` and `DTSC 3602 Project.pdf`; no Git repository, README, or `AGENTS.md` was found. No raw source file was changed.')
$prepPath = Join-Path $rootPath 'data_preparation\preparation_results.json'
if (Test-Path -LiteralPath $prepPath) {
    $prep = Get-Content -LiteralPath $prepPath -Raw | ConvertFrom-Json
    $lines.Add('')
    $lines.Add('## Preparation follow-up')
    $lines.Add('')
    $lines.Add("The [data preparation report](../data_preparation/preparation_report.md) records the cleaning rules and actual results. It retains $($prep.cmpd_metrics.output_rows) CMPD rows with quality flags and produces $($prep.violent_metrics.output_rows) NPA summary rows from $($prep.violent_metrics.raw_rows) source rows. CMPD `YEAR` matches parsed report-date year on every row in this extract; $($prep.cmpd_metrics.year_began_mismatch) rows differ from incident-start year. Of $($prep.violent_metrics.groups_with_broad_and_specific) NPA-month groups containing both the broad category and named categories, the broad count equals the sum of named categories excluding `Non-Fatal Gunshot Injury` in $($prep.violent_metrics.broad_equals_specific_without_gunshot_injury) groups. These counts support treating `Violent Crime` as a subtotal and keeping the injury indicator separate. No cross-source comparison table was created.")
}
$lines|Set-Content -LiteralPath (Join-Path $OutputDirectory 'source_audit_report.md') -Encoding utf8
Write-Host "Wrote $jsonPath and source_audit_report.md"
