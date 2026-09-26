"""WASAC Triage: explainable ranking of candidate water-network events.

Academic decision-support prototype. Demo records are synthetic. Scores prioritize
human review; they are not leak probabilities or diagnoses.
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="WASAC Triage",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.6rem; padding-bottom: 3rem;}
      .hero {padding: 1.25rem 1.5rem; border-radius: 16px;
             background: linear-gradient(115deg, #092f42, #126b78); color: white;
             margin-bottom: 1rem;}
      .hero h1 {margin: 0 0 .25rem 0; font-size: 2rem;}
      .hero p {margin: 0; color: #d5f1ed;}
      .scope {padding: .8rem 1rem; border-left: 4px solid #e3a52f;
              background: #fff7e4; border-radius: 6px; margin: .75rem 0 1.1rem 0;}
      [data-testid="stMetric"] {background: #f4f8f8; padding: .75rem;
                                border-radius: 12px;}
    </style>
    """,
    unsafe_allow_html=True,
)

EXPECTED_COLUMNS = [
    "candidate_id", "reported_at", "district", "zone_id",
    "flow_baseline_lps", "flow_observed_lps",
    "pressure_baseline_bar", "pressure_observed_bar",
    "duration_hours", "repeat_count_30d", "nearby_reports_7d",
    "criticality_index",
]
NUMERIC_COLUMNS = [
    "flow_baseline_lps", "flow_observed_lps",
    "pressure_baseline_bar", "pressure_observed_bar",
    "duration_hours", "repeat_count_30d", "nearby_reports_7d",
    "criticality_index",
]
WEIGHTS = {
    "flow_anomaly": 0.18,
    "pressure_drop": 0.12,
    "persistence": 0.25,
    "repeat_events": 0.15,
    "nearby_reports": 0.15,
    "asset_criticality": 0.15,
}
LABELS = {
    "flow_anomaly": "Flow anomaly",
    "pressure_drop": "Pressure drop",
    "persistence": "Signal persistence",
    "repeat_events": "Repeat events",
    "nearby_reports": "Nearby reports",
    "asset_criticality": "Asset criticality",
}


def make_synthetic_data() -> pd.DataFrame:
    """Create reproducible illustrative rows, not utility observations."""
    rng = np.random.default_rng(27)
    districts = ["Gasabo", "Kicukiro", "Nyarugenge"]
    today = pd.Timestamp.now().normalize()
    rows = []

    for i in range(1, 31):
        flow_base = float(rng.uniform(3.0, 18.0))
        flow_multiplier = float(
            rng.choice(
                [0.92, 1.04, 1.16, 1.35, 1.65, 2.05],
                p=[0.15, 0.18, 0.20, 0.20, 0.17, 0.10],
            )
        )
        pressure_base = float(rng.uniform(2.4, 5.2))
        pressure_loss = float(rng.choice([0.01, 0.06, 0.12, 0.22, 0.38]))
        rows.append(
            {
                "candidate_id": f"DEMO-{i:03d}",
                "reported_at": (
                    today - pd.Timedelta(days=int(rng.integers(0, 28)))
                ).isoformat(),
                "district": districts[(i - 1) % len(districts)],
                "zone_id": f"ZONE-{((i - 1) % 9) + 1:02d}",
                "flow_baseline_lps": round(flow_base, 2),
                "flow_observed_lps": round(flow_base * flow_multiplier, 2),
                "pressure_baseline_bar": round(pressure_base, 2),
                "pressure_observed_bar": round(
                    pressure_base * (1 - pressure_loss), 2
                ),
                "duration_hours": round(float(rng.uniform(0.5, 31.0)), 1),
                "repeat_count_30d": int(rng.integers(0, 7)),
                "nearby_reports_7d": int(rng.integers(0, 5)),
                "criticality_index": int(rng.integers(1, 6)),
            }
        )
    return pd.DataFrame(rows)


def load_and_validate(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Keep documented columns and leave invalid measurements missing."""
    missing_headers = [name for name in EXPECTED_COLUMNS if name not in frame.columns]
    if missing_headers:
        return pd.DataFrame(), missing_headers

    extras = [name for name in frame.columns if name not in EXPECTED_COLUMNS]
    if extras:
        st.warning(
            "Unrecognized columns ignored for this demo: "
            + ", ".join(str(name) for name in extras)
        )

    clean = frame[EXPECTED_COLUMNS].copy()
    for name in ["candidate_id", "district", "zone_id"]:
        clean[name] = clean[name].astype("string").str.strip()

    clean["reported_at"] = pd.to_datetime(clean["reported_at"], errors="coerce")
    for name in NUMERIC_COLUMNS:
        clean[name] = pd.to_numeric(clean[name], errors="coerce")

    clean.loc[clean["flow_baseline_lps"] <= 0, "flow_baseline_lps"] = np.nan
    clean.loc[clean["flow_observed_lps"] < 0, "flow_observed_lps"] = np.nan
    clean.loc[clean["pressure_baseline_bar"] <= 0, "pressure_baseline_bar"] = np.nan
    clean.loc[clean["pressure_observed_bar"] < 0, "pressure_observed_bar"] = np.nan
    clean.loc[clean["duration_hours"] < 0, "duration_hours"] = np.nan
    for name in ["repeat_count_30d", "nearby_reports_7d"]:
        invalid = clean[name].lt(0) | (clean[name] % 1 != 0)
        clean.loc[invalid, name] = np.nan
    criticality_invalid = (
        ~clean["criticality_index"].between(1, 5)
        | (clean["criticality_index"] % 1 != 0)
    )
    clean.loc[criticality_invalid, "criticality_index"] = np.nan

    clean["district"] = clean["district"].fillna("Unknown").replace("", "Unknown")
    clean["zone_id"] = clean["zone_id"].fillna("").astype("string")
    clean["candidate_id"] = clean["candidate_id"].fillna("").astype("string")

    blank_ids = clean["candidate_id"].eq("")
    if blank_ids.any():
        ids = [f"UNSPECIFIED-{i:03d}" for i in range(1, int(blank_ids.sum()) + 1)]
        clean.loc[blank_ids, "candidate_id"] = ids

    warnings = []
    duplicate_rows = clean["candidate_id"].duplicated(keep=False)
    if duplicate_rows.any():
        warnings.append(
            f"{int(duplicate_rows.sum())} rows have duplicate candidate_id values; "
            "review IDs before interpreting or exporting."
        )
    if clean["zone_id"].eq("").any():
        warnings.append("Some rows have a blank zone_id; review them before export.")
    if clean.empty:
        warnings.append("The CSV contains no candidate rows.")
    return clean, warnings


def score_candidates(frame: pd.DataFrame) -> pd.DataFrame:
    """Apply the documented weighted score; omit unavailable components."""
    result = frame.copy()
    for name in NUMERIC_COLUMNS:
        result[name] = pd.to_numeric(result[name], errors="coerce")

    components = {}
    flow_valid = result["flow_baseline_lps"].gt(0) & result["flow_observed_lps"].ge(0)
    flow_change = result["flow_observed_lps"] / result["flow_baseline_lps"] - 1.0
    components["flow_anomaly"] = (
        (flow_change.clip(lower=0) / 1.0).clip(upper=1.0) * 100.0
    ).where(flow_valid)

    pressure_valid = (
        result["pressure_baseline_bar"].gt(0)
        & result["pressure_observed_bar"].ge(0)
    )
    pressure_loss = (
        result["pressure_baseline_bar"] - result["pressure_observed_bar"]
    ) / result["pressure_baseline_bar"]
    components["pressure_drop"] = (
        (pressure_loss.clip(lower=0) / 0.35).clip(upper=1.0) * 100.0
    ).where(pressure_valid)

    components["persistence"] = (
        (result["duration_hours"].clip(lower=0) / 24.0).clip(upper=1.0) * 100.0
    )
    components["repeat_events"] = (
        (result["repeat_count_30d"].clip(lower=0) / 5.0).clip(upper=1.0) * 100.0
    )
    components["nearby_reports"] = (
        (result["nearby_reports_7d"].clip(lower=0) / 3.0).clip(upper=1.0) * 100.0
    )
    components["asset_criticality"] = (
        result["criticality_index"].where(result["criticality_index"].between(1, 5))
        / 5.0 * 100.0
    )

    numerator = pd.Series(0.0, index=result.index)
    available_weight = pd.Series(0.0, index=result.index)
    for key, component in components.items():
        valid = component.notna()
        numerator += component.fillna(0.0) * WEIGHTS[key]
        available_weight += valid.astype(float) * WEIGHTS[key]
        result[f"{key}_score"] = component.round(1)

    result["priority_score"] = (
        numerator / available_weight.replace(0.0, np.nan)
    ).round(1)
    result["input_coverage_pct"] = (available_weight * 100.0).round(0)
    result["priority_band"] = pd.cut(
        result["priority_score"],
        bins=[-0.01, 40.0, 70.0, 100.01],
        labels=["Routine", "Review", "High"],
        right=False,
    ).astype("string").fillna("Unranked")

    reasons = []
    for _, row in result.iterrows():
        ranked_reasons = []
        for key, label in LABELS.items():
            value = row.get(f"{key}_score")
            if pd.notna(value) and float(value) >= 40.0:
                ranked_reasons.append((float(value) * WEIGHTS[key], label))
        ranked_reasons.sort(reverse=True)
        if ranked_reasons:
            reasons.append("; ".join(label for _, label in ranked_reasons[:2]))
        elif pd.isna(row["priority_score"]):
            reasons.append("Insufficient valid input")
        else:
            reasons.append("No strong component signal")
    result["reason_codes"] = reasons
    return result


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
    "This app ranks submitted candidate events for human review. "
    "A score is not a leak diagnosis or probability. No operational action is automated.</div>",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Choose data")
    data_mode = st.radio("Source", ["Synthetic demo", "Upload CSV"])
    uploaded_file = None
    if data_mode == "Upload CSV":
        uploaded_file = st.file_uploader("Select a CSV", type=["csv"])
        st.caption("Use the headers in docs/02_DATA_SPEC.md.")
    st.divider()
    st.caption(
        "Uploads are processed in this app session only. "
        "Do not upload personal or unauthorized utility data."
    )

if data_mode == "Synthetic demo":
    source_frame = make_synthetic_data()
    source_label = "SYNTHETIC DEMO DATA"
else:
    if uploaded_file is None:
        st.info("Upload a CSV to build a review queue. No file is sent to an external service.")
        st.stop()
    try:
        source_frame = pd.read_csv(uploaded_file)
    except Exception as exc:
        st.error(f"Could not read this CSV: {exc}")
        st.stop()
    source_label = "USER-PROVIDED CSV"

clean_frame, validation_messages = load_and_validate(source_frame)
missing_headers = [name for name in EXPECTED_COLUMNS if name not in source_frame.columns]
if missing_headers:
    st.error("CSV is missing required headers: " + ", ".join(missing_headers))
    st.stop()
for message in validation_messages:
    st.warning(message)
if clean_frame.empty:
    st.info("There are no candidate records to rank yet.")
    st.stop()

invalid_rows = int(clean_frame[NUMERIC_COLUMNS].isna().any(axis=1).sum())
if invalid_rows:
    st.caption(
        f"{invalid_rows} row(s) contain at least one missing or invalid measurement. "
        "Their input coverage will be lower."
    )

scored = score_candidates(clean_frame)
if "review_statuses" not in st.session_state:
    st.session_state.review_statuses = {}
scored["review_status"] = scored["candidate_id"].map(
    st.session_state.review_statuses
).fillna("Needs review")

st.markdown(f"**{source_label}**  |  {len(scored)} candidate records")
districts = sorted(scored["district"].dropna().astype(str).unique().tolist())
selected_districts = st.multiselect("Filter by district", districts, default=districts)
filtered = scored[scored["district"].astype(str).isin(selected_districts)].copy()
filtered = filtered.sort_values(
    ["priority_score", "input_coverage_pct"],
    ascending=[False, False],
    na_position="last",
)

high_count = int(filtered["priority_band"].eq("High").sum())
review_count = int(filtered["priority_band"].eq("Review").sum())
available_scores = filtered["priority_score"].dropna()
highest_score = f"{available_scores.max():.1f}" if not available_scores.empty else "—"

metrics = st.columns(4)
metrics[0].metric("Candidates in view", len(filtered))
metrics[1].metric("High priority", high_count)
metrics[2].metric("Review band", review_count)
metrics[3].metric("Highest score", highest_score)

left, right = st.columns([1.35, 1], gap="large")
with left:
    st.subheader("Inspection-priority queue")
    if filtered.empty:
        st.info("No rows match this district filter.")
    else:
        chart_frame = filtered.dropna(subset=["priority_score"]).head(12).copy()
        if not chart_frame.empty:
            chart_frame = chart_frame.sort_values("priority_score")
            chart = px.bar(
                chart_frame,
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
                    "priority_score": "Illustrative priority score (0-100)",
                    "candidate_id": "Candidate",
                    "priority_band": "Band",
                },
            )
            chart.update_layout(
                height=340,
                margin=dict(l=12, r=15, t=15, b=15),
                legend_title_text="",
            )
            st.plotly_chart(chart, use_container_width=True)

        display_columns = [
            "candidate_id", "district", "zone_id", "priority_score",
            "priority_band", "input_coverage_pct", "reason_codes", "review_status",
        ]
        st.dataframe(
            filtered[display_columns],
            hide_index=True,
            use_container_width=True,
            column_config={
                "priority_score": st.column_config.NumberColumn(
                    "Score (not probability)", format="%.1f"
                ),
                "input_coverage_pct": st.column_config.ProgressColumn(
                    "Input coverage (%)", min_value=0, max_value=100, format="%.0f"
                ),
            },
        )
        st.download_button(
            "Download filtered queue as CSV",
            data=filtered.to_csv(index=False).encode("utf-8"),
            file_name="wasac_triage_ranked_queue.csv",
            mime="text/csv",
        )

with right:
    st.subheader("Review a candidate")
    if filtered.empty:
        st.caption("Choose a district with candidate records to review.")
    else:
        candidate_ids = filtered["candidate_id"].astype(str).tolist()
        selected_id = st.selectbox("Candidate ID", candidate_ids)
        selected = filtered.loc[
            filtered["candidate_id"].astype(str).eq(selected_id)
        ].iloc[0]

        st.markdown(f"### {selected_id}")
        st.write(
            f"**District:** {selected['district']}  |  "
            f"**Zone:** {selected['zone_id'] or 'Not provided'}"
        )
        if pd.notna(selected["priority_score"]):
            st.metric("Priority score (not probability)", f"{selected['priority_score']:.1f} / 100")
        else:
            st.metric("Priority score", "Unranked")
        coverage = (
            f"{selected['input_coverage_pct']:.0f}%"
            if pd.notna(selected["input_coverage_pct"])
            else "0%"
        )
        st.write(f"**Band:** {selected['priority_band']}  |  **Input coverage:** {coverage}")
        st.write(f"**Reason codes:** {selected['reason_codes']}")

        component_rows = [
            {
                "Signal": LABELS[key],
                "Component score": selected.get(f"{key}_score"),
                "Weight": f"{WEIGHTS[key] * 100:.0f}%",
            }
            for key in LABELS
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
        current = st.session_state.review_statuses.get(selected_id, "Needs review")
        new_status = st.selectbox(
            "Status for this session",
            statuses,
            index=statuses.index(current) if current in statuses else 0,
            key=f"status_{selected_id}",
        )
        if st.button("Save review status", type="primary"):
            st.session_state.review_statuses[selected_id] = new_status
            st.rerun()
        st.caption("Status is temporary; it is not saved to a database or WASAC system.")

with st.expander("How the score works"):
    st.write(
        "Flow anomaly 18%, pressure drop 12%, persistence 25%, repeat events 15%, "
        "nearby reports 15%, and asset criticality 15%. Available components are "
        "reweighted when measurements are missing. Input coverage is not confidence."
    )
    st.write(
        "Scaling values and priority bands are demonstration assumptions. "
        "Validate them against approved operational definitions and reviewed examples "
        "before field use. See docs/02_DATA_SPEC.md."
    )

st.caption(
    f"Prototype generated at {datetime.now().strftime('%Y-%m-%d %H:%M')} local app time. "
    "No data is connected to WASAC systems."
)