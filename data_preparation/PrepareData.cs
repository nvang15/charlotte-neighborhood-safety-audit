using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Globalization;
using System.Collections.Generic;

public static class PrepareData {
    static readonly CultureInfo CI = CultureInfo.InvariantCulture;
    public static string[] Parse(string line) {
        var cells = new List<string>(); var b = new StringBuilder(); bool quoted = false;
        for (int i = 0; i < line.Length; i++) { char c = line[i];
            if (quoted) { if (c == '"' && i + 1 < line.Length && line[i + 1] == '"') { b.Append('"'); i++; } else if (c == '"') quoted = false; else b.Append(c); }
            else if (c == '"') quoted = true; else if (c == ',') { cells.Add(b.ToString()); b.Clear(); } else b.Append(c);
        }
        if (quoted) throw new Exception("Unclosed quoted CSV field");
        cells.Add(b.ToString()); return cells.ToArray();
    }
    static string Escape(string value) { if (value == null) value = ""; return value.IndexOfAny(new[]{',','"','\r','\n'}) < 0 ? value : "\"" + value.Replace("\"", "\"\"") + "\""; }
    static void WriteRow(StreamWriter w, IEnumerable<string> values) { w.WriteLine(String.Join(",", values.Select(Escape))); }
    static int Ix(string[] header, string name) { int i = Array.IndexOf(header, name); if (i < 0) throw new Exception("Missing expected field: " + name); return i; }
    static void Inc(Dictionary<string,long> m, string name) { long n; m.TryGetValue(name, out n); m[name] = n + 1; }
    static string IsoDate(string raw, out int year, out bool valid) {
        year = 0; valid = true; if (String.IsNullOrEmpty(raw)) return "";
        string v = raw.EndsWith("+00", StringComparison.Ordinal) ? raw.Substring(0,raw.Length-3) : raw;
        DateTime dt; valid = DateTime.TryParseExact(v, new[]{"yyyy/MM/dd HH:mm:ss","yyyy-MM-dd HH:mm:ss","yyyy/MM/dd","yyyy-MM-dd"}, CI, DateTimeStyles.AssumeUniversal, out dt);
        if (!valid) return ""; year = dt.Year; return dt.ToString("yyyy-MM-dd", CI);
    }
    static Dictionary<string,long> NewMetrics() { return new Dictionary<string,long>(StringComparer.Ordinal); }
    public static Dictionary<string,long> CleanCmpd(string input, string output) {
        var m = NewMetrics(); var idSeen = new HashSet<string>(StringComparer.Ordinal); var codeDescriptions = new Dictionary<string,string>(StringComparer.Ordinal);
        var statusSet = new HashSet<string>(new[]{"Open","Exceptionally Cleared","Cleared by Arrest","Unfounded","Cleared by Arrest by Another Agency"}, StringComparer.Ordinal);
        using (var r = new StreamReader(input, Encoding.UTF8, true, 1 << 20))
        using (var w = new StreamWriter(output, false, new UTF8Encoding(false), 1 << 20)) {
            var h = Parse(r.ReadLine()); int id=Ix(h,"INCIDENT_REPORT_ID"), yr=Ix(h,"YEAR"), npa=Ix(h,"NPA"), report=Ix(h,"DATE_REPORTED"), began=Ix(h,"DATE_INCIDENT_BEGAN"), ended=Ix(h,"DATE_INCIDENT_END"), clearDate=Ix(h,"CLEARANCE_DATE"), status=Ix(h,"CLEARANCE_STATUS"), code=Ix(h,"HIGHEST_NIBRS_CODE"), description=Ix(h,"HIGHEST_NIBRS_DESCRIPTION");
            WriteRow(w,h.Concat(new[]{"REPORTED_DATE_ISO","INCIDENT_BEGAN_DATE_ISO","INCIDENT_END_DATE_ISO","CLEARANCE_DATE_ISO","YEAR_EQUALS_REPORTED_YEAR","YEAR_EQUALS_INCIDENT_BEGAN_YEAR","DATE_QUALITY_FLAGS","NPA_QUALITY","IS_UNFOUNDED","IS_NONCRIMINAL_HIGHEST"}));
            string line; while ((line = r.ReadLine()) != null) {
                var f = Parse(line); if (f.Length != h.Length) throw new Exception("CMPD field count error at row " + (m.ContainsKey("raw_rows") ? m["raw_rows"]+1 : 1)); Inc(m,"raw_rows");
                if (String.IsNullOrEmpty(f[id]) || !idSeen.Add(f[id])) Inc(m,"duplicate_or_missing_incident_id");
                if (!statusSet.Contains(f[status])) Inc(m,"unexpected_clearance_status");
                int dataYear; bool dataYearOk = Int32.TryParse(f[yr], NumberStyles.None, CI, out dataYear); if (!dataYearOk || dataYear < 1900 || dataYear > 2100) Inc(m,"unexpected_year");
                int npaNum; string npaQuality = !Int32.TryParse(f[npa], NumberStyles.Integer, CI, out npaNum) ? "non_numeric" : npaNum <= 0 ? "zero_or_negative" : "positive_numeric";
                if (npaQuality != "positive_numeric") Inc(m,"npa_not_positive_numeric");
                int ry,by,ey,cy; bool rv,bv,ev,cv;
                string reportIso=IsoDate(f[report],out ry,out rv), beginIso=IsoDate(f[began],out by,out bv), endIso=IsoDate(f[ended],out ey,out ev), clearIso=IsoDate(f[clearDate],out cy,out cv);
                var flags = new List<string>();
                if (!rv || reportIso.Length == 0) { flags.Add("invalid_or_missing_report_date"); Inc(m,"invalid_or_missing_report_date"); }
                if (!bv || beginIso.Length == 0) { flags.Add("invalid_or_missing_incident_began"); Inc(m,"invalid_or_missing_incident_began"); }
                if (!ev) { flags.Add("invalid_incident_end"); Inc(m,"invalid_incident_end"); }
                if (!cv) { flags.Add("invalid_clearance_date"); Inc(m,"invalid_clearance_date"); }
                if (by > 0 && by < 1900) { flags.Add("implausible_incident_began_year"); Inc(m,"implausible_incident_began_year"); }
                if (ey > 0 && ey < 1900) { flags.Add("implausible_incident_end_year"); Inc(m,"implausible_incident_end_year"); }
                if (cy > 0 && cy < 1900) { flags.Add("implausible_clearance_year"); Inc(m,"implausible_clearance_year"); }
                if (by > 0 && ey > 0 && ey < by) { flags.Add("end_before_begin"); Inc(m,"end_before_begin"); }
                string yrReport = !dataYearOk || ry == 0 ? "unknown" : (dataYear == ry ? "true" : "false");
                string yrBegin = !dataYearOk || by == 0 ? "unknown" : (dataYear == by ? "true" : "false");
                if (yrReport == "false") Inc(m,"year_report_mismatch"); if (yrBegin == "false") Inc(m,"year_began_mismatch");
                bool unfounded = f[status] == "Unfounded", noncriminal = f[description] == "Other Unlisted Non-Criminal";
                if (unfounded) Inc(m,"unfounded_flagged"); if (noncriminal) Inc(m,"noncriminal_highest_flagged"); if (unfounded && noncriminal) Inc(m,"unfounded_and_noncriminal_overlap");
                if (String.IsNullOrEmpty(f[code]) || String.IsNullOrEmpty(f[description])) Inc(m,"missing_nibrs_pair");
                else { string known; if (codeDescriptions.TryGetValue(f[code],out known)) { if (known != f[description]) Inc(m,"nibrs_code_description_conflict"); } else codeDescriptions[f[code]]=f[description]; }
                WriteRow(w,f.Concat(new[]{reportIso,beginIso,endIso,clearIso,yrReport,yrBegin,flags.Count==0?"none":String.Join(";",flags),npaQuality,unfounded?"true":"false",noncriminal?"true":"false"})); Inc(m,"output_rows");
            }
        }
        m["distinct_incident_ids"] = idSeen.Count; m["distinct_nibrs_codes"] = codeDescriptions.Count; return m;
    }
    class OffenseGroup { public long Broad; public long Specific; public long SpecificWithoutGunshotInjury; public bool HasBroad; public bool HasSpecific; }
    public static Dictionary<string,long> CleanViolent(string input, string output) {
        var m=NewMetrics(); var keys=new HashSet<string>(StringComparer.Ordinal); var groups=new Dictionary<string,OffenseGroup>(StringComparer.Ordinal); var npaIds=new HashSet<string>(StringComparer.Ordinal);
        var rowTypes=new HashSet<string>(new[]{"Neighborhood Profile Area","Corridor of Opportunity","Violent Crime Hotspot","CMPD Jurisdiction"},StringComparer.Ordinal);
        var offenses=new HashSet<string>(new[]{"Violent Crime","Aggravated Assault-Gun","Armed Robbery","Aggravated Assault-Other Weapon","Aggravated Assault-Knife","Strong Arm Robbery","Non-Fatal Gunshot Injury","Rape","Aggravated Assault-Fists,Feet, etc.","Homicide","Attempted Rape"},StringComparer.Ordinal);
        using (var r=new StreamReader(input,Encoding.UTF8,true,1<<20))
        using (var w=new StreamWriter(output,false,new UTF8Encoding(false),1<<20)) {
            var h=Parse(r.ReadLine()); int rowType=Ix(h,"ROW_TYPE"),geo=Ix(h,"GEOGRAPHY"),geoId=Ix(h,"GEOGRAPHY_ID"),year=Ix(h,"CALENDAR_YEAR"),month=Ix(h,"CALENDAR_MONTH"),offense=Ix(h,"OFFENSE_DESCRIPTION"),count=Ix(h,"OFFENSE_COUNT");
            WriteRow(w,h.Concat(new[]{"CALENDAR_PERIOD","OFFENSE_LEVEL"})); string line;
            while((line=r.ReadLine())!=null) { var f=Parse(line); if(f.Length!=h.Length) throw new Exception("Violent Crime field count error at row "+(m.ContainsKey("raw_rows")?m["raw_rows"]+1:1)); Inc(m,"raw_rows");
                if(!rowTypes.Contains(f[rowType])) Inc(m,"unexpected_row_type"); if(!offenses.Contains(f[offense])) Inc(m,"unexpected_offense_category");
                int c; if(!Int32.TryParse(f[count],NumberStyles.None,CI,out c) || c<0) Inc(m,"invalid_count");
                int y,mo; if(!Int32.TryParse(f[year],NumberStyles.None,CI,out y) || y<1900 || y>2100) Inc(m,"unexpected_year");
                if(!Int32.TryParse(f[month],NumberStyles.None,CI,out mo) || mo<1 || mo>12) Inc(m,"invalid_month");
                if(f[rowType]!="Neighborhood Profile Area") { Inc(m,"non_npa_rows_excluded"); continue; }
                npaIds.Add(f[geoId]);
                if(f[geo]!=f[geoId]) Inc(m,"npa_label_id_mismatch");
                string key=String.Join("\u001f",new[]{f[rowType],f[geo],f[geoId],f[year],f[month],f[offense]}); if(!keys.Add(key)) Inc(m,"duplicate_npa_group_key");
                bool broad=f[offense]=="Violent Crime"; string groupKey=String.Join("\u001f",new[]{f[geoId],f[year],f[month]}); OffenseGroup g; if(!groups.TryGetValue(groupKey,out g)){g=new OffenseGroup();groups[groupKey]=g;}
                if(broad){g.HasBroad=true;g.Broad+=c;Inc(m,"broad_category_rows");}else{g.HasSpecific=true;g.Specific+=c;if(f[offense]!="Non-Fatal Gunshot Injury")g.SpecificWithoutGunshotInjury+=c;Inc(m,"specific_category_rows");}
                string level=broad?"broad_category":f[offense]=="Non-Fatal Gunshot Injury"?"injury_indicator":"specific_offense";
                WriteRow(w,f.Concat(new[]{f[year]+"-"+mo.ToString("D2",CI),level})); Inc(m,"output_rows");
            }
        }
        foreach(var g in groups.Values){if(g.HasBroad && g.HasSpecific){Inc(m,"groups_with_broad_and_specific");if(g.Broad==g.Specific)Inc(m,"broad_equals_specific_sum");else if(g.Broad<g.Specific)Inc(m,"broad_less_than_specific_sum");else Inc(m,"broad_greater_than_specific_sum");if(g.Broad==g.SpecificWithoutGunshotInjury)Inc(m,"broad_equals_specific_without_gunshot_injury");else if(g.Broad<g.SpecificWithoutGunshotInjury)Inc(m,"broad_less_than_specific_without_gunshot_injury");else Inc(m,"broad_greater_than_specific_without_gunshot_injury");}}
        m["distinct_npa_ids"]=npaIds.Count; m["distinct_npa_month_groups"]=groups.Count; return m;
    }
}
