using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;

public static class AggregateDashboard {
    static string[] Parse(string line) {
        var parts = new List<string>(); var field = new StringBuilder(); bool quote = false;
        for (int i = 0; i < line.Length; i++) {
            char c = line[i];
            if (quote) { if (c == '"' && i + 1 < line.Length && line[i + 1] == '"') { field.Append('"'); i++; } else if (c == '"') quote = false; else field.Append(c); }
            else if (c == '"') quote = true; else if (c == ',') { parts.Add(field.ToString()); field.Clear(); } else field.Append(c);
        }
        if (quote) throw new Exception("Unclosed CSV quote"); parts.Add(field.ToString()); return parts.ToArray();
    }
    static int Col(string[] header, string name) { int n = Array.IndexOf(header, name); if (n < 0) throw new Exception("Missing field: " + name); return n; }
    static string Q(string s) { return "\"" + s.Replace("\"", "\"\"") + "\""; }
    static void Add(Dictionary<string,long> counts, string key, long count) { long old; counts.TryGetValue(key, out old); counts[key] = checked(old + count); }
    public static string Run(string cmpdPath, string violentPath, string outDir) {
        Directory.CreateDirectory(outDir);
        var cmpd = new Dictionary<string,long>(); var violent = new Dictionary<string,long>();
        long cmpdInput = 0, cmpdBadNpa = 0, cmpdPartial = 0, violentInput = 0, violentPartial = 0, violentBadNpa = 0;
        using (var r = new StreamReader(cmpdPath, Encoding.UTF8, true, 1 << 20)) {
            var h = Parse(r.ReadLine()); int n = Col(h, "NPA"), y = Col(h, "YEAR"), date = Col(h, "REPORTED_DATE_ISO"), quality = Col(h, "NPA_QUALITY"); string line;
            while ((line = r.ReadLine()) != null) {
                var f = Parse(line); if (f.Length != h.Length) throw new Exception("CMPD field count mismatch"); cmpdInput++;
                int year = Int32.Parse(f[y], CultureInfo.InvariantCulture), npa;
                if (f[date].Length < 4 || f[date].Substring(0,4) != f[y]) throw new Exception("CMPD date/year mismatch");
                if (year > 2025) { cmpdPartial++; continue; }
                if (year < 2017) throw new Exception("Unexpected CMPD year");
                if (f[quality] != "positive_numeric" || !Int32.TryParse(f[n], out npa) || npa <= 0) { cmpdBadNpa++; continue; }
                Add(cmpd, npa + "|" + year, 1);
            }
        }
        using (var r = new StreamReader(violentPath, Encoding.UTF8, true, 1 << 20)) {
            var h = Parse(r.ReadLine()); int n = Col(h, "GEOGRAPHY_ID"), y = Col(h, "CALENDAR_YEAR"), offense = Col(h, "OFFENSE_DESCRIPTION"), level = Col(h, "OFFENSE_LEVEL"), count = Col(h, "OFFENSE_COUNT"), type = Col(h, "ROW_TYPE"); string line;
            while ((line = r.ReadLine()) != null) {
                var f = Parse(line); if (f.Length != h.Length) throw new Exception("Violent field count mismatch"); violentInput++;
                if (f[type] != "Neighborhood Profile Area") throw new Exception("Unexpected geography row type");
                int year = Int32.Parse(f[y], CultureInfo.InvariantCulture), npa;
                long value;
                if (!Int64.TryParse(f[count], NumberStyles.None, CultureInfo.InvariantCulture, out value) || value < 0) throw new Exception("Invalid offense count");
                if (year > 2025) { violentPartial++; continue; }
                if (year < 2015) throw new Exception("Unexpected summary year");
                if (!Int32.TryParse(f[n], out npa) || npa <= 0) { violentBadNpa++; continue; }
                if (f[level] != "broad_category" && f[level] != "specific_offense" && f[level] != "injury_indicator") throw new Exception("Unexpected offense level");
                Add(violent, npa + "|" + year + "|" + f[offense] + "|" + f[level], value);
            }
        }
        var broad = new Dictionary<string,long>(); var named = new Dictionary<string,long>();
        foreach (var entry in violent) { var p = entry.Key.Split('|'); string group = p[0] + "|" + p[1]; if (p[3] == "broad_category") Add(broad, group, entry.Value); else if (p[3] == "specific_offense") Add(named, group, entry.Value); }
        foreach (var entry in broad) { long total; if (named.TryGetValue(entry.Key, out total) && total != entry.Value) throw new Exception("Broad/named subtotal disagreement: " + entry.Key); }
        using (var w = new StreamWriter(Path.Combine(outDir, "cmpd_npa_year_counts.csv"), false, new UTF8Encoding(false))) {
            w.WriteLine("npa_id,year,report_count");
            foreach (var entry in cmpd.OrderBy(x => Int32.Parse(x.Key.Split('|')[1])).ThenBy(x => Int32.Parse(x.Key.Split('|')[0]))) { var p = entry.Key.Split('|'); w.WriteLine(p[0] + "," + p[1] + "," + entry.Value); }
        }
        using (var w = new StreamWriter(Path.Combine(outDir, "violent_npa_year_offense_counts.csv"), false, new UTF8Encoding(false))) {
            w.WriteLine("npa_id,year,offense_description,offense_level,offense_count");
            foreach (var entry in violent.OrderBy(x => Int32.Parse(x.Key.Split('|')[1])).ThenBy(x => Int32.Parse(x.Key.Split('|')[0])).ThenBy(x => x.Key)) { var p = entry.Key.Split('|'); w.WriteLine(p[0] + "," + p[1] + "," + Q(p[2]) + "," + p[3] + "," + entry.Value); }
        }
        return "CMPD input=" + cmpdInput + ", 2026 omitted=" + cmpdPartial + ", invalid NPA omitted=" + cmpdBadNpa + ", aggregate rows=" + cmpd.Count + "; Violent NPA input=" + violentInput + ", 2026 omitted=" + violentPartial + ", invalid NPA omitted=" + violentBadNpa + ", aggregate rows=" + violent.Count + "; broad/named year-NPA checks=" + broad.Count;
    }
}
