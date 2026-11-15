"""AquaTriage: preliminary screening and human review for erosion-site observations."""

from __future__ import annotations

import hashlib
from datetime import datetime
from io import BytesIO

import pandas as pd
import streamlit as st

from src.demo_data import make_demo_data
from src.schema import EXPECTED_COLUMNS, validate_records
from src.scoring import COMPONENT_COLUMNS, LABELS, WEIGHTS, score_candidates

SITE_TYPES = [
    "Roadside drain",
    "Hillside",
    "Stream bank",
    "Cultivated land",
    "Construction area",
    "Other",
]
REVIEW_STATUSES = [
    "Needs review",
    "Site visit planned",
    "Specialist review",
    "Mitigation underway",
    "Monitoring",
    "Closed",
]
ORDINAL_FIELDS = [
    ("drainage_concern_0_5", "Drainage concern"),
    ("erosion_evidence_0_5", "Visible erosion evidence"),
    ("runoff_concentration_0_5", "Concentrated runoff"),
    ("exposed_asset_0_5", "People, assets, or receiving areas exposed"),
]


def _read_uploaded_csv(file_bytes: bytes) -> tuple[pd.DataFrame, str | None]:
    try:
        uploaded = pd.read_csv(BytesIO(file_bytes))
    except (
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
        UnicodeDecodeError,
        ValueError,
        OSError,
    ) as exc:
        return pd.DataFrame(columns=EXPECTED_COLUMNS), f"Could not read this CSV: {exc}"

    missing = [column for column in EXPECTED_COLUMNS if column not in uploaded.columns]
    if missing:
        return (
            pd.DataFrame(columns=EXPECTED_COLUMNS),
            "CSV not used: missing required headers: " + ", ".join(missing),
        )
    return uploaded, None


def _field_observation_form(dataset_key: str, existing: pd.DataFrame) -> None:
    with st.expander("Add a field observation", expanded=False):
        st.caption(
            "Record what was observed, not an assumed cause or treatment. "
            "Leave measurements blank if they were not assessed."
        )
        with st.form(f"field_observation_{dataset_key}", clear_on_submit=True):
            identity_cols = st.columns(3)
            with identity_cols[0]:
                site_id = st.text_input("Pseudonymous site ID", max_chars=64)
            with identity_cols[1]:
                district = st.text_input("District / approved area label", max_chars=80)
            with identity_cols[2]:
                site_type = st.selectbox("Site type", SITE_TYPES)

            measured_cols = st.columns(2)
            with measured_cols[0]:
                slope_percent = st.number_input(
                    "Slope (%) · blank if not assessed",
                    min_value=0.0,
                    max_value=100.0,
                    value=None,
                    step=0.5,
                    placeholder="Not assessed",
                )
            with measured_cols[1]:
                bare_soil_percent = st.number_input(
                    "Bare soil (%) · blank if not assessed",
                    min_value=0.0,
                    max_value=100.0,
                    value=None,
                    step=1.0,
                    placeholder="Not assessed",
                )

            def format_ordinal(value: int | None) -> str:
                if value is None:
                    return "Not assessed"
                if value == 0:
                    return "0 · None observed"
                return f"{value} · increasing observed concern"

            ordinal_cols = st.columns(2)
            ordinal_values: dict[str, int | None] = {}
            for index, (field, label) in enumerate(ORDINAL_FIELDS):
                with ordinal_cols[index % 2]:
                    ordinal_values[field] = st.selectbox(
                        f"{label} (0–5)",
                        [None, 0, 1, 2, 3, 4, 5],
                        format_func=format_ordinal,
                        key=f"{dataset_key}_{field}",
                        help=(
                            "An unvalidated, assessor-entered ordinal observation; "
                            "use a consistent local rubric. Do not enter 0 for an "
                            "unassessed factor."
                        ),
                    )

            submitted = st.form_submit_button("Add observation", type="primary")

        if submitted:
            clean_site_id = site_id.strip()
            if not clean_site_id:
                st.error("Enter a pseudonymous site ID before adding the observation.")
                return

            existing_ids = set(existing["site_id"].dropna().astype(str))
            if clean_site_id in existing_ids:
                st.error("That site ID already exists in this queue. Use a distinct ID.")
                return

            assessed_at = pd.Timestamp(datetime.now().astimezone()).isoformat()
            observation = {
                "site_id": clean_site_id,
                "assessed_at": assessed_at,
                "district": district.strip() or "Unknown",
                "site_type": site_type,
                "slope_percent": slope_percent,
                "bare_soil_percent": bare_soil_percent,
                **ordinal_values,
            }
            all_observations = st.session_state.setdefault("field_observations", {})
            all_observations.setdefault(dataset_key, []).append(observation)
            st.session_state["field_observations"] = all_observations
            st.rerun()


st.set_page_config(
    page_title="AquaTriage | Erosion site screening",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

with st.sidebar:
    st.markdown("## AquaTriage")
    st.caption("Erosion site screening")
    data_mode = st.selectbox(
        "Observation source",
        ["Field register", "Synthetic sample", "Upload CSV"],
        help="Field observations and review statuses remain only in this app session.",
    )
    uploaded_file = None
    upload_error = None
    if data_mode == "Upload CSV":
        uploaded_file = st.file_uploader(
            "Anonymized site-observation CSV",
            type=["csv"],
            help="Use pseudonymous site IDs and approved coarse location labels only.",
        )
        if uploaded_file is not None:
            st.caption("Uploads are processed in this app session; they are not persisted.")

    st.download_button(
        "Download CSV template",
        data=pd.DataFrame(columns=EXPECTED_COLUMNS).to_csv(index=False).encode("utf-8"),
        file_name="aquatriage_erosion_template.csv",
        mime="text/csv",
        width="stretch",
    )
    st.divider()
    st.caption(
        "This prototype has no live field sensor, GIS, weather, or agency-system "
        "connection."
    )

source_frame: pd.DataFrame
if data_mode == "Synthetic sample":
    source_frame = make_demo_data()
    source_name = "Synthetic demonstration records — fictional"
    dataset_key = "demo-erosion-v1"
elif data_mode == "Upload CSV" and uploaded_file is not None:
    file_bytes = uploaded_file.getvalue()
    dataset_key = hashlib.sha256(file_bytes).hexdigest()[:16]
    source_frame, upload_error = _read_uploaded_csv(file_bytes)
    source_name = uploaded_file.name
else:
    source_frame = pd.DataFrame(columns=EXPECTED_COLUMNS)
    dataset_key = "field-register-v1"
    source_name = "Field register · session only"

if st.session_state.get("active_dataset_key") != dataset_key:
    st.session_state["active_dataset_key"] = dataset_key
    st.session_state["review_statuses"] = {}
    st.session_state.setdefault("field_observations", {})

if upload_error:
    st.error(upload_error)
elif data_mode == "Upload CSV" and uploaded_file is None:
    st.info("Upload a CSV, or add field observations below to start a session register.")

st.title("Erosion site screening")
st.caption(
    "A preliminary, explainable queue for human follow-up · "
    f"**{source_name}**"
)
st.warning(
    "Screening priority is not a probability, engineering assessment, hazard rating, "
    "or treatment recommendation. If a site appears immediately unsafe, follow local "
    "emergency and safeguarding procedures without waiting for this tool."
)

observations_by_source = st.session_state.setdefault("field_observations", {})
session_records = observations_by_source.get(dataset_key, [])
if source_frame.empty:
    combined = (
        pd.DataFrame.from_records(session_records, columns=EXPECTED_COLUMNS)
        if session_records
        else source_frame.copy()
    )
elif session_records:
    combined = pd.concat(
        [
            source_frame,
            pd.DataFrame.from_records(session_records, columns=EXPECTED_COLUMNS),
        ],
        ignore_index=True,
    )
else:
    combined = source_frame.copy()
clean, validation_warnings, invalid_counts, ignored_columns = validate_records(combined)
_field_observation_form(dataset_key, clean)

if clean.empty:
    st.title("AquaTriage")
    st.caption("A practical field register for preliminary erosion-site review.")
    st.warning(
        "This tool does not predict slope failure, diagnose causes, or prescribe "
        "erosion-control treatments. It is not an emergency service."
    )
    st.subheader("Start an observation register")
    st.write(
        "Add an anonymized field observation above, upload a completed template, or "
        "switch to the fictional sample. No records are saved beyond this app session."
    )
    st.stop()

if st.session_state.get("active_dataset_key") != dataset_key:
    st.session_state["active_dataset_key"] = dataset_key
    st.session_state["review_statuses"] = {}

invalid_cell_count = sum(invalid_counts.values())
if validation_warnings or invalid_cell_count:
    st.warning(
        "Some observations need attention. See Data quality for invalid and missing "
        "values; invalid measurements are excluded, never changed to zero."
    )

scored = score_candidates(clean)
scored["row_key"] = [f"{dataset_key}:{row_number}" for row_number in range(len(scored))]
review_statuses = st.session_state.setdefault("review_statuses", {})
scored["review_status"] = scored["row_key"].map(review_statuses).fillna("Needs review")

districts = sorted(scored["district"].fillna("Unknown").astype(str).unique().tolist())
site_types = sorted(scored["site_type"].fillna("Not specified").astype(str).unique().tolist())
bands = ["Higher review priority", "Review", "Routine review", "Unranked"]
search_col, district_col, site_type_col, band_col, status_col = st.columns(
    [1.5, 1.1, 1.2, 1.25, 1.25]
)
with search_col:
    search_text = st.text_input(
        "Search sites",
        placeholder="Site ID, district, or type",
        key=f"search_{dataset_key}",
    )
with district_col:
    selected_districts = st.multiselect(
        "District",
        districts,
        default=districts,
        key=f"district_{dataset_key}",
    )
with site_type_col:
    selected_site_types = st.multiselect(
        "Site type",
        site_types,
        default=site_types,
        key=f"site_type_{dataset_key}",
    )
with band_col:
    selected_bands = st.multiselect(
        "Screening band",
        bands,
        default=bands,
        key=f"bands_{dataset_key}",
    )
with status_col:
    selected_statuses = st.multiselect(
        "Review status",
        REVIEW_STATUSES,
        default=REVIEW_STATUSES,
        key=f"statuses_{dataset_key}",
    )

search_query = search_text.strip()
search_mask = pd.Series(True, index=scored.index)
if search_query:
    search_mask = (
        scored["site_id"].astype("string").str.contains(
            search_query, case=False, regex=False, na=False
        )
        | scored["district"].astype("string").str.contains(
            search_query, case=False, regex=False, na=False
        )
        | scored["site_type"].astype("string").str.contains(
            search_query, case=False, regex=False, na=False
        )
    )

filtered = scored[
    scored["district"].astype(str).isin(selected_districts)
    & scored["site_type"].astype(str).isin(selected_site_types)
    & scored["priority_band"].isin(selected_bands)
    & scored["review_status"].isin(selected_statuses)
    & search_mask
].copy()
filtered = filtered.sort_values(
    ["priority_score", "input_coverage_pct"],
    ascending=[False, False],
    na_position="last",
).reset_index(drop=True)
filtered["rank"] = range(1, len(filtered) + 1)

higher_count = int(filtered["priority_band"].eq("Higher review priority").sum())
review_count = int(filtered["priority_band"].eq("Review").sum())
coverage_average = (
    f"{filtered['input_coverage_pct'].mean():.0f}%"
    if not filtered.empty
    else "—"
)
with st.container(horizontal=True, gap="small"):
    st.metric("Sites in view", len(filtered), border=True)
    st.metric("Higher review priority", higher_count, border=True)
    st.metric("Review band", review_count, border=True)
    st.metric("Average input coverage", coverage_average, border=True)

st.subheader("Field follow-up queue")
st.caption(
    "Queue order reflects provisional, unvalidated weights and thresholds. "
    "Confirm observations on site before making decisions."
)

if filtered.empty:
    st.info("No sites match these filters. Clear the search or widen the selected filters.")
else:
    filter_signature = repr(
        (
            search_query.casefold(),
            tuple(selected_districts),
            tuple(selected_site_types),
            tuple(selected_bands),
            tuple(selected_statuses),
        )
    )
    queue_key = (
        f"queue_{dataset_key}_"
        f"{hashlib.sha256(filter_signature.encode('utf-8')).hexdigest()[:8]}"
    )
    queue_col, detail_col = st.columns([1.55, 1.0], gap="large")
    with queue_col:
        header_col, export_col = st.columns([2.5, 1.0], vertical_alignment="center")
        with header_col:
            st.markdown("**Sites to review**")
        export_columns = [
            *EXPECTED_COLUMNS,
            *COMPONENT_COLUMNS,
            "priority_score",
            "priority_band",
            "input_coverage_pct",
            "reason_codes",
            "review_status",
        ]
        with export_col:
            st.download_button(
                "Export filtered queue",
                data=filtered[export_columns].to_csv(index=False).encode("utf-8"),
                file_name="aquatriage_erosion_review_queue.csv",
                mime="text/csv",
                width="stretch",
                key=f"export_{queue_key}",
            )

        selection = st.dataframe(
            filtered[
                [
                    "rank",
                    "site_id",
                    "district",
                    "site_type",
                    "priority_score",
                    "priority_band",
                    "input_coverage_pct",
                    "review_status",
                ]
            ],
            hide_index=True,
            width="stretch",
            height=460,
            alt="Filtered erosion-site screening queue ranked by provisional score",
            on_select="rerun",
            selection_mode="single-row",
            key=queue_key,
            column_config={
                "rank": st.column_config.NumberColumn("Rank", format="%d", width="small"),
                "site_id": st.column_config.TextColumn("Site", width="medium"),
                "priority_score": st.column_config.NumberColumn(
                    "Screening score",
                    format="%.1f",
                    help="Provisional comparison score; not a hazard or failure probability.",
                ),
                "input_coverage_pct": st.column_config.ProgressColumn(
                    "Input coverage",
                    min_value=0,
                    max_value=100,
                    format="%.0f%%",
                    help="Fraction of the provisional scoring weight backed by valid data; not confidence.",
                ),
            },
        )

    selected_rows = selection.selection.rows
    selected_position = selected_rows[0] if selected_rows else 0
    if selected_position >= len(filtered):
        selected_position = 0
    selected_key = str(filtered.iloc[selected_position]["row_key"])
    selected = scored.loc[scored["row_key"].eq(selected_key)].iloc[0]

    with detail_col:
        with st.container(border=True):
            st.subheader("Observation detail")
            st.markdown(f"**{selected['site_id']}**")
            st.caption(f"{selected['district']} · {selected['site_type']}")
            score_text = (
                f"{selected['priority_score']:.1f} / 100"
                if pd.notna(selected["priority_score"])
                else "Unranked"
            )
            score_cols = st.columns(2)
            score_cols[0].metric("Screening score", score_text, border=True)
            score_cols[1].metric("Queue band", selected["priority_band"], border=True)
            st.caption(
                f"Input coverage: {selected['input_coverage_pct']:.0f}% · "
                "coverage is not confidence."
            )

            st.markdown("**Recorded indicators**")
            st.write(selected["reason_codes"])
            component_rows = [
                {
                    "Indicator": LABELS[name],
                    "Observed scale": selected[f"{name}_score"],
                    "Provisional weight": f"{WEIGHTS[name] * 100:.0f}%",
                }
                for name in WEIGHTS
            ]
            st.dataframe(
                pd.DataFrame(component_rows),
                hide_index=True,
                width="stretch",
                alt="Observed indicator scores and provisional weights for the selected site",
                column_config={
                    "Observed scale": st.column_config.NumberColumn(format="%.1f"),
                },
            )

            assessed_at = selected["assessed_at"]
            date_label = (
                assessed_at.strftime("%d %b %Y, %H:%M %Z")
                if pd.notna(assessed_at)
                else "Not provided"
            )
            st.caption(f"Observed: {date_label}")
            st.markdown("**Human follow-up**")
            current_status = review_statuses.get(selected_key, "Needs review")
            status_widget_key = f"status_{selected_key}"
            new_status = st.selectbox(
                "Status",
                REVIEW_STATUSES,
                index=(
                    REVIEW_STATUSES.index(current_status)
                    if current_status in REVIEW_STATUSES
                    else 0
                ),
                key=status_widget_key,
            )
            if st.button(
                "Save review status",
                type="primary",
                key=f"save_{status_widget_key}",
                width="stretch",
            ):
                review_statuses[selected_key] = new_status
                st.session_state["review_statuses"] = review_statuses
                st.rerun()
            st.caption("Review status is temporary and lasts for this app session.")
            st.info(
                "Have a competent erosion-control or geotechnical professional assess "
                "site causes, downstream exposure, permits, and suitable treatments. "
                "This tool does not prescribe a fix."
            )

with st.expander("Data quality", expanded=False):
    quality_cols = st.columns(3)
    quality_cols[0].metric(
        "Rows with incomplete indicators",
        int(scored["input_coverage_pct"].lt(100).sum()),
        border=True,
    )
    quality_cols[1].metric(
        "Unranked rows",
        int(scored["priority_score"].isna().sum()),
        border=True,
    )
    quality_cols[2].metric("Invalid cells excluded", invalid_cell_count, border=True)

    quality_rows = []
    for column in EXPECTED_COLUMNS:
        missing_mask = clean[column].isna()
        if column in ["site_id", "district", "site_type"]:
            missing_mask = missing_mask | clean[column].astype("string").str.strip().eq("").fillna(True)
        quality_rows.append(
            {
                "Field": column,
                "Valid cells": len(clean) - int(missing_mask.sum()),
                "Missing after validation": int(missing_mask.sum()),
                "Invalid cells": invalid_counts.get(column, 0),
            }
        )
    st.dataframe(
        pd.DataFrame(quality_rows),
        hide_index=True,
        width="stretch",
        alt="Valid, missing, and invalid values by observation field",
    )
    if validation_warnings:
        st.markdown("**Import notes**")
        for warning in validation_warnings:
            st.write(f"- {warning}")
    if ignored_columns:
        st.info("Unrecognized CSV columns were discarded before scoring and export.")

with st.expander("Scoring, rubric, and limitations", expanded=False):
    st.markdown("**Provisional screening model**")
    weights_table = pd.DataFrame(
        [
            {"Observed indicator": LABELS[name], "Provisional weight": f"{weight * 100:.0f}%"}
            for name, weight in WEIGHTS.items()
        ]
    )
    st.dataframe(
        weights_table,
        hide_index=True,
        width="stretch",
        alt="Provisional indicator weights used in screening",
    )
    st.markdown(
        """
        - Ordinal observations use 0 for “none observed” and 1–5 for an assessor's
          increasing concern rating; use a consistent local rubric and leave a factor
          unassessed rather than entering 0.
        - Slope is scaled against a **provisional 30% reference**; bare-soil coverage
          uses the entered percentage. Scores and bands (70/40) are unvalidated
          project assumptions, not engineering thresholds or hazard classes.
        - Available factors are reweighted when values are missing. Input coverage
          shows how much of the provisional scoring weight was present; it is not
          confidence. A missing-data record can still receive a score.
        - A qualified local specialist must validate the factors, scales, weights,
          thresholds, and field workflow against local conditions and reviewed
          outcomes before operational use.
        """
    )

st.caption(
    f"Session-only prototype · refreshed {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %Z')} · "
    "no live GIS, rainfall, sensor, or agency connection"
)
