using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Collections.Generic;

public class EdaSummary {
    public Dictionary<int,long> CmpdYearRows = new Dictionary<int,long>();
    public Dictionary<string,long> CmpdNpaYearRows = new Dictionary<string,long>();
    public Dictionary<string,long> CmpdMissing = new Dictionary<string,long>();
    public Dictionary<int,long> ViolentNpaYearRows = new Dictionary<int,long>();
    public Dictionary<string,long> ViolentOffenseGroupCount = new Dictionary<string,long>();
    public long CmpdRows, CmpdExcludedNpaQuality, ViolentNpaRows;
    public string CmpdMinReported = null, CmpdMaxReported = null, ViolentMinPeriod = null, ViolentMaxPeriod = null;
}

public static class EdaData {
    static string[] Parse(string line) {
        var cells=new List<string>(); var b=new StringBuilder(); bool quoted=false;
        for(int i=0;i<line.Length;i++){char c=line[i];if(quoted){if(c=='"' && i+1<line.Length && line[i+1]=='"'){b.Append('"');i++;}else if(c=='"')quoted=false;else b.Append(c);}else if(c=='"')quoted=true;else if(c==','){cells.Add(b.ToString());b.Clear();}else b.Append(c);}
        if(quoted)throw new Exception("Unclosed quoted CSV field");cells.Add(b.ToString());return cells.ToArray();
    }
    static int Ix(string[] h,string name){int i=Array.IndexOf(h,name);if(i<0)throw new Exception("Missing prepared field: "+name);return i;}
    static void Inc<TKey>(Dictionary<TKey,long> d,TKey key,long n=1){long old;d.TryGetValue(key,out old);d[key]=old+n;}
    public static EdaSummary Load(string cmpdPath,string violentPath){var s=new EdaSummary();
        using(var r=new StreamReader(cmpdPath,Encoding.UTF8,true,1<<20)){var h=Parse(r.ReadLine());int y=Ix(h,"YEAR"),npa=Ix(h,"NPA"),npaQuality=Ix(h,"NPA_QUALITY"),reported=Ix(h,"REPORTED_DATE_ISO");
            var missingNames=new[]{"ZIP","STATE","DATE_INCIDENT_END","CLEARANCE_DATE","DATE_INCIDENT_BEGAN","DATE_REPORTED"};var missingIdx=missingNames.Select(n=>Ix(h,n)).ToArray();string line;
            while((line=r.ReadLine())!=null){var f=Parse(line);if(f.Length!=h.Length)throw new Exception("CMPD prepared field count mismatch");s.CmpdRows++;int year=Int32.Parse(f[y]);Inc(s.CmpdYearRows,year);
                for(int i=0;i<missingNames.Length;i++)if(f[missingIdx[i]].Length==0)Inc(s.CmpdMissing,missingNames[i]);
                if(s.CmpdMinReported==null || String.CompareOrdinal(f[reported],s.CmpdMinReported)<0)s.CmpdMinReported=f[reported];if(s.CmpdMaxReported==null || String.CompareOrdinal(f[reported],s.CmpdMaxReported)>0)s.CmpdMaxReported=f[reported];
                if(year>=2023 && year<=2025){if(f[npaQuality]=="positive_numeric")Inc(s.CmpdNpaYearRows,year+"|"+f[npa]);else s.CmpdExcludedNpaQuality++;}
            }
        }
        using(var r=new StreamReader(violentPath,Encoding.UTF8,true,1<<20)){var h=Parse(r.ReadLine());int y=Ix(h,"CALENDAR_YEAR"),offense=Ix(h,"OFFENSE_DESCRIPTION"),count=Ix(h,"OFFENSE_COUNT"),level=Ix(h,"OFFENSE_LEVEL"),period=Ix(h,"CALENDAR_PERIOD"),rowtype=Ix(h,"ROW_TYPE");string line;
            while((line=r.ReadLine())!=null){var f=Parse(line);if(f.Length!=h.Length)throw new Exception("Violent prepared field count mismatch");if(f[rowtype]!="Neighborhood Profile Area")throw new Exception("Non-NPA row in prepared NPA file");s.ViolentNpaRows++;int year=Int32.Parse(f[y]);Inc(s.ViolentNpaYearRows,year);
                if(s.ViolentMinPeriod==null || String.CompareOrdinal(f[period],s.ViolentMinPeriod)<0)s.ViolentMinPeriod=f[period];if(s.ViolentMaxPeriod==null || String.CompareOrdinal(f[period],s.ViolentMaxPeriod)>0)s.ViolentMaxPeriod=f[period];
                if(year>2025 || f[level]!="specific_offense")continue;
                string group;var o=f[offense];if(o.StartsWith("Aggravated Assault-",StringComparison.Ordinal))group="Aggravated assault";else if(o=="Armed Robbery" || o=="Strong Arm Robbery")group="Robbery";else if(o=="Rape" || o=="Attempted Rape")group="Rape / attempted rape";else if(o=="Homicide")group="Homicide";else throw new Exception("Unexpected specific offense in prepared NPA file: "+o);
                Inc(s.ViolentOffenseGroupCount,year+"|"+group,Int64.Parse(f[count]));
            }
        }
        return s;
    }
}
