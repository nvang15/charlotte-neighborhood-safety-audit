"""Offense grouping by how reliably victims report (NCVS-informed, approximate).
Edit the dicts to run sensitivity checks; everything downstream reads from here."""
import re

# Crimes victims (or insurers/owners) almost always report: vehicle theft, burglary, robbery.
RELIABLE_PATTERNS = [r"motor vehicle theft", r"burglary", r"breaking", r"robbery"]
# Offenses driven largely by patrol and enforcement activity rather than victim reports.
DISCRETIONARY_PATTERNS = [r"drug", r"narcotic", r"driving under", r"weapon", r"disorderly", r"liquor",
                          r"trespass", r"all other offenses", r"curfew", r"drunkenness", r"prostitution",
                          r"gambling", r"pornography", r"loitering"]
# Records that are not crimes against a victim; filtered out of every score (per the proposal).
NONCRIMINAL_PATTERNS = [r"non-criminal", r"noncriminal", r"missing person", r"sudden/natural", r"overdose", r"suicide",
                        r"vehicle recovery", r"public accident", r"fire \(accidental", r"gas leak", r"dog bite"]
VIOLENT_PATTERNS = [r"assault", r"homicide", r"murder", r"rape", r"sex", r"kidnap", r"intimidation", r"manslaughter",
                    r"fondling", r"sodomy", r"incest", r"trafficking", r"peeping", r"indecent exposure", r"affray"]


def _match(desc, pats):
    d = (desc or "").lower()
    return any(re.search(p, d) for p in pats)


def offense_group(desc):
    if _match(desc, NONCRIMINAL_PATTERNS):
        return "noncriminal"
    if _match(desc, RELIABLE_PATTERNS):
        return "reliable"
    if _match(desc, DISCRETIONARY_PATTERNS):
        return "discretionary"
    if _match(desc, VIOLENT_PATTERNS):
        return "violent_other"
    return "property_other"
