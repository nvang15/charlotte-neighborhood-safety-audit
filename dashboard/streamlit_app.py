"""Read only NPA/year aggregate tables; never reads incident-level files."""
import os
import pandas as pd
import streamlit as st
import altair as alt
from supabase import create_client

st.set_page_config(page_title="Charlotte D2: reported counts", layout="wide")


def setting(name):
    if os.environ.get(name):
        return os.environ[name]
    try:
        return st.secrets.get(name)
    except Exception:
        return None


@st.cache_resource
def client(url, key):
    return create_client(url, key)


@st.cache_data(ttl=3600)
def read_year(url, key, table, year, columns):
    db = client(url, key)
    rows = []
    page_size = 1000
    start = 0
    while True:
        query = db.table(table).select(columns).eq("year", year).order("npa_id")
        if table == "d2_violent_npa_year_offense":
            query = query.order("offense_description")
        page = query.range(start, start + page_size - 1).execute().data
        rows.extend(page)
        if len(page) < page_size:
            break
        start += page_size
    return pd.DataFrame(rows)


def reset_npa_selection(selection_key):
    st.session_state[selection_key] = []


def npa_bar_chart(chart_data, count_column, count_title, selected_npas):
    display_data = chart_data.copy()
    display_data["npa_label"] = display_data["npa_id"].map(lambda value: f"NPA {value}")
    display_data["is_selected"] = display_data["npa_id"].isin(selected_npas)
    count_max = max(float(display_data[count_column].max()) * 1.05, 1)
    npa_order = display_data["npa_label"].tolist()
    return (
        alt.Chart(display_data)
        .mark_bar()
        .encode(
            x=alt.X(
                f"{count_column}:Q",
                title=count_title,
                scale=alt.Scale(domain=[0, count_max], zero=True, nice=False),
            ),
            y=alt.Y(
                "npa_label:N",
                title="Neighborhood Profile Area ID",
                sort=npa_order,
            ),
            color=alt.condition(
                "datum.is_selected",
                alt.value("#d95f02"),
                alt.value("#4c78a8"),
            ),
            opacity=alt.condition(
                "datum.is_selected",
                alt.value(1.0),
                alt.value(0.45 if selected_npas else 1.0),
            ),
            tooltip=[
                alt.Tooltip("npa_label:N", title="Neighborhood Profile Area"),
                alt.Tooltip(f"{count_column}:Q", title=count_title, format=","),
            ],
        )
        .properties(height=600)
    )


def npa_selection_control(chart_data, selection_key):
    selected_npas = st.multiselect(
        "Select up to two Neighborhood Profile Areas shown in the chart",
        options=chart_data["npa_id"].tolist(),
        max_selections=2,
        key=selection_key,
        format_func=lambda value: f"NPA {value}",
        placeholder="Choose one or two NPAs",
    )
    st.caption("Select an NPA to highlight its bar and show details. Remove it from the box to deselect it.")
    st.button(
        "Reset view",
        key=f"reset_{selection_key}",
        on_click=reset_npa_selection,
        args=(selection_key,),
        help="Clear the NPA selection and restore the chart's full count range.",
    )
    return selected_npas


def show_npa_details(frame, selected_npas, count_column, count_label, year, source_label):
    if not selected_npas:
        st.caption("No NPA selected. The chart shows the full count range for all 25 displayed NPAs.")
        return

    selected_rows = []
    for npa_id in selected_npas:
        match = frame[frame["npa_id"] == npa_id]
        if not match.empty:
            selected_rows.append(match.iloc[0])

    if not selected_rows:
        return

    st.markdown("#### Selected NPA details" if len(selected_rows) == 1 else "#### Selected NPA comparison")
    detail_columns = st.columns(len(selected_rows))
    for column, row in zip(detail_columns, selected_rows):
        with column:
            st.metric(f"NPA {row['npa_id']}", f"{int(row[count_column]):,}")
            st.caption(f"{count_label} · {year} · {source_label}")

    comparison = pd.DataFrame(
        [
            {
                "Neighborhood Profile Area ID": row["npa_id"],
                "Selected year": year,
                "Data source": source_label,
                "Measure": count_label,
                "Reported count": int(row[count_column]),
            }
            for row in selected_rows
        ]
    )
    st.dataframe(comparison, hide_index=True, use_container_width=True)

    if len(selected_rows) == 2:
        difference = abs(int(selected_rows[0][count_column]) - int(selected_rows[1][count_column]))
        st.metric("Absolute difference in displayed reported counts", f"{difference:,}")
        st.caption("This difference is a subtraction of the two displayed counts. It is not adjusted for population or exposure and is not a safety comparison.")


st.title("Reported police data by Neighborhood Profile Area (NPA)")
st.info("These are descriptive counts from Charlotte-Mecklenburg Police Department (CMPD) incident reports or a published violent-crime summary. Reported counts do not measure all crime, do not account for population or exposure, and are not a safety rating.")

with st.expander("Glossary and help"):
    st.markdown(
        """
- **Neighborhood Profile Area (NPA):** the geographic unit used to group these data. An NPA boundary may not match a reader's everyday idea of a neighborhood, and the boundary vintage and assignment rules are unverified.
- **Incident-report record:** one CMPD report record counted in the prepared incident data. It is not interchangeable with an offense count or a count of all crime.
- **Published aggregate offense count:** a count reported in the violent-crime summary for an NPA, year, and offense category. Monthly published counts are summed; missing groups are not assumed to be zero.
"""
    )

source_labels = {
    "CMPD incident reports": "Charlotte-Mecklenburg Police Department (CMPD) incident reports",
    "Violent Crime NPA summary": "Published violent-crime summary",
}
source = st.selectbox("Data source", list(source_labels), format_func=source_labels.get)
if source == "CMPD incident reports":
    year = st.selectbox("Year reported", list(range(2025, 2016, -1)))
    table, cols = "d2_cmpd_npa_year", "npa_id,year,report_count"
    st.caption("Source: prepared Charlotte-Mecklenburg Police Department incident reports · report-date year · 2017–2025 in this dashboard. 2026 is omitted because the extract ends October 30. Completeness of other calendar years is unverified.")
else:
    year = st.selectbox("Calendar year", list(range(2025, 2014, -1)))
    table, cols = "d2_violent_npa_year_offense", "npa_id,year,offense_description,offense_level,offense_count"
    st.caption("Source: prepared published violent-crime summary · Neighborhood Profile Area rows · calendar year · 2015–2025 in this dashboard. 2026 is omitted because the extract has January–March only.")

url, key = setting("SUPABASE_URL"), setting("SUPABASE_PUBLISHABLE_KEY")
if not url or not key:
    st.error("Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY in the environment or Streamlit secrets.")
    st.stop()

try:
    data = read_year(url, key, table, year, cols)
except Exception as exc:
    st.error(f"Could not read the aggregate table: {type(exc).__name__}. Check Supabase table access and configuration.")
    st.stop()
if data.empty:
    st.warning("No rows returned for this source and year. This does not establish a count of zero.")
    st.stop()

if source == "CMPD incident reports":
    data["report_count"] = pd.to_numeric(data["report_count"])
    if data.duplicated(["npa_id", "year"]).any() or (data["report_count"] < 0).any():
        st.error("Aggregate key or count validation failed.")
        st.stop()
    ranked = data.sort_values("report_count", ascending=False)
    chart_data = ranked.head(25).copy()
    selection_key = f"cmpd_npa_selection_{year}"
    selected_npas = st.session_state.get(selection_key, [])
    st.subheader("Reported incident records by area")
    st.markdown(f"**Selected year:** {year} · **Source:** Charlotte-Mecklenburg Police Department incident reports · **Geography:** Neighborhood Profile Area · **Measure:** incident-report records")
    st.altair_chart(
        npa_bar_chart(chart_data, "report_count", "Reported incident records", selected_npas),
        use_container_width=True,
    )
    selected_npas = npa_selection_control(chart_data, selection_key)
    show_npa_details(
        chart_data,
        selected_npas,
        "report_count",
        "Reported incident records",
        year,
        "Charlotte-Mecklenburg Police Department incident reports",
    )
    st.caption("How to read this chart: Each bar shows the number of CMPD incident-report records assigned to one NPA in the selected report year. The chart displays the 25 NPAs with the highest counts for that year.")
    st.caption("Limitation: These are reported records, not a measure of all crime or a safety rating. Counts are not adjusted for population or exposure, and NPA boundaries may not match familiar neighborhood boundaries.")
    st.dataframe(ranked.rename(columns={"npa_id": "Neighborhood Profile Area ID", "year": "Report year", "report_count": "Reported incident records"}), hide_index=True)
    st.caption("All highest-NIBRS classifications remain in these report counts, including records flagged Unfounded or Other Unlisted Non-Criminal. Open and Cleared are retained; neither status establishes validity or confirmed criminality. CMPD offenses are not broken out because the crosswalk to the summary offense categories is unverified.")
else:
    data["offense_count"] = pd.to_numeric(data["offense_count"])
    if data.duplicated(["npa_id", "year", "offense_description"]).any() or (data["offense_count"] < 0).any():
        st.error("Aggregate key or count validation failed.")
        st.stop()
    broad = data[(data.offense_level == "broad_category") & (data.offense_description == "Violent Crime")]
    if broad.empty:
        st.error("Expected Violent Crime subtotal is absent.")
        st.stop()
    st.subheader("Reported violent-crime counts by area")
    ranked = broad.sort_values("offense_count", ascending=False)
    chart_data = ranked.head(25).copy()
    selection_key = f"violent_npa_selection_{year}"
    selected_npas = st.session_state.get(selection_key, [])
    st.markdown(f"**Selected year:** {year} · **Source:** published violent-crime summary · **Geography:** Neighborhood Profile Area · **Measure:** reported aggregate offense count (broad violent-crime subtotal)")
    st.altair_chart(
        npa_bar_chart(chart_data, "offense_count", "Reported aggregate offense count", selected_npas),
        use_container_width=True,
    )
    selected_npas = npa_selection_control(chart_data, selection_key)
    show_npa_details(
        chart_data,
        selected_npas,
        "offense_count",
        "Reported aggregate violent-crime subtotal",
        year,
        "Published violent-crime summary",
    )
    st.caption("How to read this chart: Each bar shows the published broad violent-crime subtotal for one NPA in the selected calendar year. The chart displays the 25 NPAs with the highest subtotals for that year.")
    st.caption("Limitation: These are reported aggregate offense counts, not incident-report records, a measure of all crime, or a safety rating. Counts are not adjusted for population or exposure, and missing published groups are not assumed to be zero.")
    st.dataframe(ranked[["npa_id", "offense_count"]].rename(columns={"npa_id": "Neighborhood Profile Area ID", "offense_count": "Reported violent-crime subtotal"}), hide_index=True)
    npa = st.selectbox("Neighborhood Profile Area for offense detail", sorted(data.npa_id.unique()))
    specific = data[(data.npa_id == npa) & (data.offense_level == "specific_offense")].sort_values("offense_count", ascending=False)
    st.subheader("Reported violent-crime counts by offense")
    st.markdown(f"**Selected year:** {year} · **Source:** published violent-crime summary · **Geography:** Neighborhood Profile Area {npa} · **Measure:** reported aggregate count by named offense")
    if specific.empty:
        st.warning("No named-offense rows are published for this NPA and year; absence is not interpreted as zero.")
    else:
        offense_count_max = max(float(specific["offense_count"].max()) * 1.05, 1)
        chart = alt.Chart(specific).mark_bar().encode(
            x=alt.X(
                "offense_count:Q",
                title="Reported aggregate offense count",
                scale=alt.Scale(domain=[0, offense_count_max], zero=True, nice=False),
            ),
            y=alt.Y("offense_description:N", sort="-x", title="Offense category"),
            tooltip=[
                alt.Tooltip("offense_description:N", title="Offense category"),
                alt.Tooltip("offense_count:Q", title="Reported aggregate count"),
            ],
        )
        st.altair_chart(chart, use_container_width=True)
    st.caption("How to read this chart: Compare bar lengths to see how the published named-offense counts differ within the selected NPA and calendar year.")
    st.caption("Limitation: These are reported aggregate offense counts, not a measure of all crime or a safety rating. The broad Violent Crime subtotal and the separate Non-Fatal Gunshot Injury indicator are excluded from this breakdown; missing published groups are not filled with zero, and counts are not adjusted for population or exposure.")

st.divider()
st.subheader("Interpretation limits")
st.write("NPA boundary vintage and assignment rules are unverified, so NPA IDs may not represent stable or identical geography across sources or years. CMPD uses report-date year; the summary uses its calendar-year field. The highest CMPD NIBRS code has no verified crosswalk to the summary offenses. The two sources are shown separately and their counts should not be compared or summed.")
st.write("Reporting, classification, enforcement, and geocoding can vary. These data are not a probability sample of all events. No population or exposure denominator is supplied. Calendar year 2025 is reserved as a future temporal test period for modeling; its display here is descriptive only.")
