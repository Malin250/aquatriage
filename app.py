"""AquaTriage: local decision support for candidate water-network events."""

from __future__ import annotations

import hashlib
from datetime import datetime
from io import BytesIO

import pandas as pd
import streamlit as st

from src.anomaly import screen_batch
from src.demo_data import make_demo_data
from src.schema import EXPECTED_COLUMNS, validate_records
from src.scoring import COMPONENT_COLUMNS, LABELS, WEIGHTS, score_candidates


st.set_page_config(
    page_title="AquaTriage",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Keep the main task and its controls in one compact workspace.
title_col, source_col, template_col, ai_col = st.columns(
    [2.8, 1.25, 1.0, 1.45],
    vertical_alignment="center",
)
with title_col:
    st.title("AquaTriage")
    st.caption("Inspection queue for candidate water-network events")
with source_col:
    data_mode = st.selectbox(
        "Data source",
        ["Synthetic demo", "Upload CSV"],
        key="data_mode",
    )
with template_col:
    st.download_button(
        "CSV template",
        data=pd.DataFrame(columns=EXPECTED_COLUMNS).to_csv(index=False).encode("utf-8"),
        file_name="aquatriage_template.csv",
        mime="text/csv",
        width="stretch",
    )
with ai_col:
    run_ai = st.checkbox(
        "Experimental AI screen",
        value=True,
        key="run_ai",
        help=(
            "Isolation Forest flags records that look unusual within this batch. "
            "It does not estimate leak probability and does not affect priority."
        ),
    )

st.info(
    "Decision-support prototype. Scores help prioritize human review; they are not "
    "leak diagnoses or probabilities, and no operational action is automated."
)

if data_mode == "Synthetic demo":
    source_frame = make_demo_data()
    source_name = "Synthetic demonstration records"
    dataset_key = "demo-v1"
    source_badge = "SYNTHETIC DATA — FICTIONAL EXAMPLES"
else:
    uploaded_file = st.file_uploader(
        "Choose an anonymized candidate CSV",
        type=["csv"],
        key="uploaded_csv",
    )
    st.caption("Uploads are processed in this app session and are not sent to an external service.")
    if uploaded_file is None:
        st.info("Upload a CSV to build the inspection queue.")
        st.stop()

    file_bytes = uploaded_file.getvalue()
    dataset_key = hashlib.sha256(file_bytes).hexdigest()[:16]
    source_name = uploaded_file.name
    source_badge = "USER-PROVIDED CSV"
    try:
        source_frame = pd.read_csv(BytesIO(file_bytes))
    except Exception as exc:
        st.error(f"Could not read this CSV: {exc}")
        st.stop()

clean, validation_warnings, invalid_counts, ignored_columns = validate_records(source_frame)
missing_headers = [name for name in EXPECTED_COLUMNS if name not in source_frame.columns]
if missing_headers:
    st.error("CSV is missing required headers: " + ", ".join(missing_headers))
    st.stop()
if clean.empty:
    st.warning("This file has headers but no candidate rows.")
    st.stop()

invalid_cell_count = sum(invalid_counts.values())
if validation_warnings or invalid_cell_count:
    st.warning("Import needs review. Open Data quality below for warnings and invalid-cell counts.")

if st.session_state.get("active_dataset_key") != dataset_key:
    st.session_state["active_dataset_key"] = dataset_key
    st.session_state["review_statuses"] = {}

scored = score_candidates(clean)
if run_ai:
    with st.spinner("Running exploratory anomaly screen..."):
        scored, ai_message = screen_batch(scored)
else:
    scored["ai_anomaly_flag"] = "Not run"
    scored["ai_anomaly_index"] = pd.NA
    ai_message = "AI screen is off. The transparent baseline queue still works."

scored["row_key"] = [f"{dataset_key}:{row_number}" for row_number in range(len(scored))]
review_statuses = st.session_state.get("review_statuses", {})
scored["review_status"] = scored["row_key"].map(review_statuses).fillna("Needs review")

st.caption(f"**{source_badge}** · {source_name} · {len(scored)} candidate rows")

# Global queue filters stay together directly above the results.
districts = sorted(scored["district"].fillna("Unknown").astype(str).unique().tolist())
bands = ["High", "Review", "Routine", "Unranked"]
statuses = ["Needs review", "Reviewed", "Assigned", "Closed"]
filter_cols = st.columns([1.5, 1.35, 1.0, 1.25])
with filter_cols[0]:
    search_text = st.text_input(
        "Search candidates",
        placeholder="Candidate ID, district, or zone",
        key=f"search_{dataset_key}",
    )
with filter_cols[1]:
    selected_districts = st.multiselect(
        "District",
        districts,
        default=districts,
        key=f"district_{dataset_key}",
    )
with filter_cols[2]:
    selected_bands = st.multiselect(
        "Priority",
        bands,
        default=bands,
        key=f"bands_{dataset_key}",
    )
with filter_cols[3]:
    selected_statuses = st.multiselect(
        "Review status",
        statuses,
        default=statuses,
        key=f"statuses_{dataset_key}",
    )

search_query = search_text.strip()
search_mask = pd.Series(True, index=scored.index)
if search_query:
    search_mask = (
        scored["candidate_id"].astype("string").str.contains(search_query, case=False, regex=False, na=False)
        | scored["district"].astype("string").str.contains(search_query, case=False, regex=False, na=False)
        | scored["zone_id"].astype("string").str.contains(search_query, case=False, regex=False, na=False)
    )

filtered = scored[
    scored["district"].astype(str).isin(selected_districts)
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

high_count = int(filtered["priority_band"].eq("High").sum())
review_count = int(filtered["priority_band"].eq("Review").sum())
ai_count = int(filtered["ai_anomaly_flag"].eq("Outlier review").sum())
coverage_avg = (
    f"{filtered['input_coverage_pct'].mean():.0f}%"
    if not filtered.empty
    else "—"
)

with st.container(horizontal=True, gap="small"):
    st.metric("Candidates in view", len(filtered), border=True)
    st.metric("High priority", high_count, border=True)
    st.metric("Review priority", review_count, border=True)
    st.metric("Average input coverage", coverage_avg, border=True)
    st.metric("AI outlier flags", ai_count if run_ai else "Off", border=True)

st.subheader("Inspection queue")
st.caption("Select a row to see its score breakdown and review controls.")

if filtered.empty:
    st.info("No candidates match these filters. Clear a search term or widen the selected filters.")
else:
    filter_signature = repr(
        (
            search_query.casefold(),
            tuple(selected_districts),
            tuple(selected_bands),
            tuple(selected_statuses),
        )
    )
    queue_key = (
        f"queue_{dataset_key}_"
        f"{hashlib.sha256(filter_signature.encode('utf-8')).hexdigest()[:8]}"
    )

    queue_col, detail_col = st.columns([1.6, 1.0], gap="large")
    with queue_col:
        queue_header, export_col = st.columns([3.2, 1.0], vertical_alignment="center")
        with queue_header:
            st.markdown("**Ranked candidates**")
        export_columns = [
            *EXPECTED_COLUMNS,
            *COMPONENT_COLUMNS,
            "priority_score",
            "priority_band",
            "input_coverage_pct",
            "reason_codes",
            "ai_anomaly_flag",
            "ai_anomaly_index",
            "review_status",
        ]
        with export_col:
            st.download_button(
                "Export queue",
                data=filtered[export_columns].to_csv(index=False).encode("utf-8"),
                file_name="aquatriage_ranked_queue.csv",
                mime="text/csv",
                width="stretch",
                key=f"export_{dataset_key}_{queue_key}",
            )

        queue_table = filtered[
            [
                "rank",
                "candidate_id",
                "district",
                "priority_score",
                "priority_band",
                "input_coverage_pct",
                "review_status",
            ]
        ]
        selection = st.dataframe(
            queue_table,
            hide_index=True,
            width="stretch",
            height=500,
            on_select="rerun",
            selection_mode="single-row",
            key=queue_key,
            column_config={
                "rank": st.column_config.NumberColumn("Rank", format="%d", width="small"),
                "candidate_id": st.column_config.TextColumn("Candidate", width="medium"),
                "priority_score": st.column_config.NumberColumn(
                    "Score",
                    format="%.1f",
                    help="Explainable triage score, not a leak probability.",
                ),
                "input_coverage_pct": st.column_config.ProgressColumn(
                    "Coverage",
                    min_value=0,
                    max_value=100,
                    format="%.0f%%",
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
            st.subheader("Selected candidate")
            st.markdown(f"**{selected['candidate_id']}**")
            st.caption(
                f"{selected['district']} · {selected['zone_id'] or 'Zone not provided'}"
            )
            score_value = (
                f"{selected['priority_score']:.1f} / 100"
                if pd.notna(selected["priority_score"])
                else "Unranked"
            )
            score_col, band_col = st.columns(2)
            score_col.metric("Baseline score", score_value, border=True)
            band_col.metric("Priority band", selected["priority_band"], border=True)
            st.caption(
                f"Input coverage: {selected['input_coverage_pct']:.0f}% · "
                "coverage is not confidence."
            )

            st.markdown("**Why it is ranked here**")
            st.write(selected["reason_codes"])

            component_rows = [
                {
                    "Signal": LABELS[name],
                    "Component score": selected[f"{name}_score"],
                    "Weight": f"{WEIGHTS[name] * 100:.0f}%",
                }
                for name in WEIGHTS
            ]
            st.dataframe(
                pd.DataFrame(component_rows),
                hide_index=True,
                width="stretch",
                height=230,
                column_config={
                    "Component score": st.column_config.NumberColumn(format="%.1f"),
                },
            )

            st.markdown("**Experimental AI screen**")
            ai_index = (
                f"{selected['ai_anomaly_index']:.1f}"
                if pd.notna(selected["ai_anomaly_index"])
                else "—"
            )
            st.write(f"{selected['ai_anomaly_flag']} · relative index: {ai_index}")
            st.caption("Batch-relative only; it does not change the baseline rank or predict leaks.")

            reported_at = selected["reported_at"]
            report_label = (
                reported_at.strftime("%d %b %Y, %H:%M %Z")
                if pd.notna(reported_at)
                else "Not provided"
            )
            st.caption(f"Reported: {report_label}")

            st.markdown("**Human review status**")
            current_status = review_statuses.get(selected_key, "Needs review")
            status_key = f"status_{dataset_key}_{selected_key}"
            new_status = st.selectbox(
                "Status",
                statuses,
                index=statuses.index(current_status) if current_status in statuses else 0,
                key=status_key,
            )
            if st.button("Save status", type="primary", key=f"save_{status_key}", width="stretch"):
                review_statuses[selected_key] = new_status
                st.session_state["review_statuses"] = review_statuses
                st.rerun()
            st.caption("Status is temporary and lasts for this app session.")

with st.expander("Data quality", expanded=False):
    quality_cols = st.columns(3)
    quality_cols[0].metric(
        "Rows with incomplete score inputs",
        int(scored["input_coverage_pct"].lt(100).sum()),
        border=True,
    )
    quality_cols[1].metric(
        "Rows not rankable",
        int(scored["priority_score"].isna().sum()),
        border=True,
    )
    quality_cols[2].metric("Invalid cells", invalid_cell_count, border=True)

    quality_rows = []
    text_columns = {"candidate_id", "district", "zone_id"}
    for column in EXPECTED_COLUMNS:
        missing_mask = clean[column].isna()
        if column in text_columns:
            blank_mask = clean[column].astype("string").str.strip().eq("").fillna(True)
            missing_mask = missing_mask | blank_mask
        missing_count = int(missing_mask.sum())
        quality_rows.append(
            {
                "Field": column,
                "Valid cells": len(clean) - missing_count,
                "Missing after validation": missing_count,
                "Invalid cells": invalid_counts.get(column, 0),
            }
        )
    st.dataframe(pd.DataFrame(quality_rows), hide_index=True, width="stretch")

    if validation_warnings:
        with st.expander("Import warnings", expanded=True):
            for warning in validation_warnings:
                st.write(f"- {warning}")
    if ignored_columns:
        st.info("Ignored upload fields were discarded before scoring and export.")

with st.expander("Scoring and method", expanded=False):
    method_col, ai_col = st.columns([1, 1])
    with method_col:
        st.markdown("**Explainable baseline score**")
        weights_table = pd.DataFrame(
            [
                {"Component": LABELS[name], "Weight": f"{weight * 100:.0f}%"}
                for name, weight in WEIGHTS.items()
            ]
        )
        st.dataframe(weights_table, hide_index=True, width="stretch")
        st.caption(
            "Available components are reweighted when inputs are missing. "
            "Input coverage is not confidence. Scaling thresholds need utility review."
        )
    with ai_col:
        st.markdown("**Experimental Isolation Forest**")
        st.write(ai_message)
        st.caption(
            "The model is fit on this loaded batch. Its relative index and outlier flag "
            "do not change the baseline score and are not leak predictions."
        )
        st.caption(
            "Use utility data only with written owner approval and agreed privacy, "
            "access, retention, and deletion rules."
        )

st.caption(
    f"Local prototype · generated {datetime.now().strftime('%Y-%m-%d %H:%M')} · "
    "no live utility connection"
)