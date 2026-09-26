"""WASAC Triage: local decision support for candidate water-network events."""

from __future__ import annotations

import hashlib
from io import BytesIO
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from src.anomaly import screen_batch
from src.demo_data import make_demo_data
from src.schema import EXPECTED_COLUMNS, NUMERIC_COLUMNS, validate_records
from src.scoring import COMPONENT_COLUMNS, LABELS, WEIGHTS, score_candidates


st.set_page_config(
    page_title="WASAC Triage",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.35rem; padding-bottom: 2.5rem;}
      .hero {padding: 1.3rem 1.5rem; border-radius: 16px;
             background: linear-gradient(115deg, #092f42, #126b78); color: white;
             margin-bottom: .75rem;}
      .hero h1 {margin: 0 0 .25rem 0; font-size: 2rem;}
      .hero p {margin: 0; color: #d5f1ed;}
      .scope {padding: .75rem 1rem; border-left: 4px solid #e3a52f;
              background: #fff7e4; border-radius: 6px; margin: .7rem 0 1rem 0;}
      [data-testid="stMetric"] {background: #f4f8f8; padding: .7rem;
                                border-radius: 12px;}
      .small-note {color: #52666c; font-size: .9rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <h1>WASAC Triage</h1>
      <p>Make the next inspection decision easier to explain.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="scope"><strong>Decision-support prototype.</strong> '
    "This app ranks candidate events for human review. A score is not a leak "
    "diagnosis or probability. The experimental AI flag is not a diagnosis. "
    "No operational action is automated.</div>",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Data source")
    data_mode = st.radio("Choose records", ["Synthetic demo", "Upload CSV"])
    uploaded_file = None
    if data_mode == "Upload CSV":
        uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])
        st.caption("Required fields are listed in docs/02_DATA_SPEC.md.")
    st.divider()
    run_ai = st.checkbox(
        "Run experimental AI anomaly screen",
        value=True,
        help=(
            "Isolation Forest finds relative outliers in this loaded batch. "
            "It does not estimate leak probability and does not affect priority score."
        ),
    )
    st.divider()
    st.caption(
        "Uploads stay in this app session. Do not use personal or unauthorized "
        "utility records."
    )
    st.download_button(
        "Download blank CSV template",
        data=pd.DataFrame(columns=EXPECTED_COLUMNS).to_csv(index=False).encode("utf-8"),
        file_name="wasac_triage_template.csv",
        mime="text/csv",
    )

if data_mode == "Synthetic demo":
    source_frame = make_demo_data()
    source_name = "Synthetic demonstration records"
    dataset_key = "demo-v1"
    source_badge = "SYNTHETIC DATA — FICTIONAL EXAMPLES"
else:
    if uploaded_file is None:
        st.info("Upload a CSV to build a review queue. No file is sent to an external service.")
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

clean, validation_warnings, invalid_counts, ignored_columns = validate_records(
    source_frame
)
missing_headers = [name for name in EXPECTED_COLUMNS if name not in source_frame.columns]
if missing_headers:
    st.error("CSV is missing required headers: " + ", ".join(missing_headers))
    st.stop()
if clean.empty:
    st.warning("This file has headers but no candidate rows.")
    st.stop()

for warning in validation_warnings:
    st.warning(warning)

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

districts = sorted(scored["district"].fillna("Unknown").astype(str).unique().tolist())
bands = ["High", "Review", "Routine", "Unranked"]
with st.sidebar:
    st.header("Queue filters")
    selected_districts = st.multiselect("District", districts, default=districts)
    selected_bands = st.multiselect("Priority band", bands, default=bands)

filtered = scored[
    scored["district"].astype(str).isin(selected_districts)
    & scored["priority_band"].isin(selected_bands)
].copy()
filtered = filtered.sort_values(
    ["priority_score", "input_coverage_pct"],
    ascending=[False, False],
    na_position="last",
)

high_count = int(filtered["priority_band"].eq("High").sum())
review_count = int(filtered["priority_band"].eq("Review").sum())
ai_count = int(filtered["ai_anomaly_flag"].eq("Outlier review").sum())
coverage_avg = (
    f"{filtered['input_coverage_pct'].mean():.0f}%"
    if not filtered.empty
    else "—"
)

st.markdown(f"**{source_badge}**  ·  {source_name}  ·  {len(scored)} candidate rows")
metric_cols = st.columns(4)
metric_cols[0].metric("Candidates in view", len(filtered))
metric_cols[1].metric("High priority", high_count)
metric_cols[2].metric("AI outlier flags", ai_count if run_ai else "Off")
metric_cols[3].metric("Average input coverage", coverage_avg)

queue_tab, review_tab, quality_tab = st.tabs(
    ["Priority queue", "Review a candidate", "Data quality and method"]
)

with queue_tab:
    st.subheader("Inspection-priority queue")
    st.caption(
        "Sorted by the explainable baseline score. AI outlier results are separate "
        "and never change this rank."
    )
    if filtered.empty:
        st.info("No records match the current filters.")
    else:
        chart_data = filtered.dropna(subset=["priority_score"]).head(15).copy()
        if not chart_data.empty:
            chart_data = chart_data.sort_values("priority_score")
            chart = px.bar(
                chart_data,
                x="priority_score",
                y="candidate_id",
                color="priority_band",
                orientation="h",
                range_x=[0, 100],
                color_discrete_map={
                    "High": "#c75146",
                    "Review": "#e3a52f",
                    "Routine": "#328b79",
                    "Unranked": "#8b969b",
                },
                labels={
                    "priority_score": "Baseline priority score (not probability)",
                    "candidate_id": "Candidate",
                    "priority_band": "Priority band",
                },
            )
            chart.update_layout(
                height=max(320, 26 * len(chart_data)),
                margin=dict(l=10, r=10, t=10, b=10),
                legend_title_text="",
            )
            st.plotly_chart(chart, use_container_width=True)

        table = filtered[
            [
                "candidate_id",
                "district",
                "zone_id",
                "priority_score",
                "priority_band",
                "input_coverage_pct",
                "reason_codes",
                "ai_anomaly_flag",
                "ai_anomaly_index",
                "review_status",
            ]
        ]
        st.dataframe(
            table,
            hide_index=True,
            use_container_width=True,
            column_config={
                "priority_score": st.column_config.NumberColumn(
                    "Baseline score", format="%.1f",
                    help="Explainable triage score. Not a leak probability.",
                ),
                "input_coverage_pct": st.column_config.ProgressColumn(
                    "Input coverage", min_value=0, max_value=100, format="%.0f%%",
                    help="Percent of baseline score weight supported by valid inputs.",
                ),
                "ai_anomaly_index": st.column_config.NumberColumn(
                    "AI relative index", format="%.1f",
                    help="Within-batch outlier ranking. Not a probability.",
                ),
            },
        )

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
        export_frame = filtered[export_columns]
        st.download_button(
            "Download filtered ranked queue",
            data=export_frame.to_csv(index=False).encode("utf-8"),
            file_name="wasac_triage_ranked_queue.csv",
            mime="text/csv",
        )

with review_tab:
    st.subheader("Review a candidate")
    if filtered.empty:
        st.info("Choose a district and band with candidate records.")
    else:
        id_counts = scored["candidate_id"].value_counts(dropna=False)
        display_names = {}
        for row_number, row in filtered.iterrows():
            display = f"{row['candidate_id']} — {row['district']} / {row['zone_id']}"
            if id_counts.get(row["candidate_id"], 0) > 1:
                display += f" · record {row_number + 1}"
            display_names[row["row_key"]] = display
        selected_key = st.selectbox(
            "Candidate",
            options=list(display_names),
            format_func=lambda key: display_names[key],
            key=f"candidate_{dataset_key}",
        )
        selected = scored.loc[scored["row_key"].eq(selected_key)].iloc[0]

        detail_left, detail_right = st.columns([1, 1])
        with detail_left:
            st.markdown(f"### {selected['candidate_id']}")
            reported_at = selected["reported_at"]
            report_label = (
                reported_at.strftime("%d %b %Y, %H:%M %Z")
                if pd.notna(reported_at)
                else "Not provided"
            )
            st.write(f"**District:** {selected['district']}")
            st.write(f"**Zone:** {selected['zone_id'] or 'Not provided'}")
            st.write(f"**Reported:** {report_label}")
            if pd.notna(selected["priority_score"]):
                st.metric(
                    "Baseline score (not probability)",
                    f"{selected['priority_score']:.1f} / 100",
                )
            else:
                st.metric("Baseline score", "Unranked")
            st.write(f"**Priority band:** {selected['priority_band']}")
            st.write(f"**Reason codes:** {selected['reason_codes']}")
            st.write(
                f"**Experimental AI flag:** {selected['ai_anomaly_flag']}  ·  "
                f"relative index: {selected['ai_anomaly_index'] if pd.notna(selected['ai_anomaly_index']) else '—'}"
            )
        with detail_right:
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
                use_container_width=True,
                column_config={
                    "Component score": st.column_config.NumberColumn(format="%.1f")
                },
            )
            st.markdown("**Human review status**")
            statuses = ["Needs review", "Reviewed", "Assigned", "Closed"]
            current_status = review_statuses.get(selected_key, "Needs review")
            status_key = f"status_{dataset_key}_{selected_key}"
            new_status = st.selectbox(
                "Status for this session",
                statuses,
                index=statuses.index(current_status)
                if current_status in statuses
                else 0,
                key=status_key,
            )
            if st.button("Save review status", type="primary", key=f"save_{status_key}"):
                review_statuses[selected_key] = new_status
                st.session_state["review_statuses"] = review_statuses
                st.rerun()
            st.caption("Status is temporary and is not written to a utility system.")

with quality_tab:
    st.subheader("Input quality")
    quality_cols = st.columns(3)
    quality_cols[0].metric("Rows with incomplete score inputs", int(scored["input_coverage_pct"].lt(100).sum()))
    quality_cols[1].metric("Rows not rankable", int(scored["priority_score"].isna().sum()))
    quality_cols[2].metric("Invalid cells", sum(invalid_counts.values()))

    quality_rows = []
    text_columns = {"candidate_id", "district", "zone_id"}
    for column in EXPECTED_COLUMNS:
        missing_mask = clean[column].isna()
        if column in text_columns:
            blank_mask = clean[column].astype("string").str.strip().eq("").fillna(True)
            missing_mask = missing_mask | blank_mask
        missing_count = int(missing_mask.sum())
        valid_count = len(clean) - missing_count
        quality_rows.append(
            {"Field": column, "Valid cells": valid_count,
             "Missing after validation": missing_count,
             "Invalid cells": invalid_counts.get(column, 0)}
        )
    st.dataframe(pd.DataFrame(quality_rows), hide_index=True, use_container_width=True)

    if validation_warnings:
        with st.expander("Import warnings", expanded=True):
            for warning in validation_warnings:
                st.write(f"- {warning}")
    if ignored_columns:
        st.info("Ignored upload fields were discarded before scoring and export.")

    coverage_chart = px.histogram(
        scored,
        x="input_coverage_pct",
        nbins=10,
        range_x=[0, 100],
        labels={"input_coverage_pct": "Input coverage (%)", "count": "Records"},
        title="Baseline input coverage",
    )
    coverage_chart.update_layout(height=300, margin=dict(l=10, r=10, t=45, b=10))
    st.plotly_chart(coverage_chart, use_container_width=True)

    st.subheader("Scoring and AI method")
    method_left, method_right = st.columns(2)
    with method_left:
        st.markdown("**Explainable baseline score**")
        weights_table = pd.DataFrame(
            [
                {"Component": LABELS[name], "Weight": f"{weight * 100:.0f}%"}
                for name, weight in WEIGHTS.items()
            ]
        )
        st.dataframe(weights_table, hide_index=True, use_container_width=True)
        st.caption(
            "Available components are reweighted when inputs are missing. "
            "Input coverage is not confidence. Scaling thresholds need utility review."
        )
    with method_right:
        st.markdown("**Experimental Isolation Forest screen**")
        if run_ai:
            st.write(ai_message)
        else:
            st.write(ai_message)
        st.caption(
            "The model is fit on this loaded batch. Its relative index and outlier flag "
            "do not change the baseline score and are not leak predictions. Do not use "
            "synthetic records to claim field accuracy."
        )
        st.caption(
            "To use the dataset for a real study, obtain written approval and follow "
            "the data owner's privacy, access, and retention rules."
        )

st.caption(
    f"Local prototype · generated {datetime.now().strftime('%Y-%m-%d %H:%M')} · "
    "no live WASAC connection"
)
