"""Explainable baseline feature engineering and priority score."""

from __future__ import annotations

import numpy as np
import pandas as pd

WEIGHTS = {
    "flow_anomaly": 0.18,
    "pressure_drop": 0.12,
    "persistence": 0.25,
    "repeat_events": 0.15,
    "nearby_reports": 0.15,
    "asset_criticality": 0.15,
}
LABELS = {
    "flow_anomaly": "Flow anomaly elevated",
    "pressure_drop": "Pressure drop observed",
    "persistence": "Signal persisted",
    "repeat_events": "Repeat events in zone",
    "nearby_reports": "Nearby reports present",
    "asset_criticality": "High asset criticality",
}
COMPONENT_COLUMNS = [f"{name}_score" for name in WEIGHTS]


def score_candidates(frame: pd.DataFrame) -> pd.DataFrame:
    """Calculate a 0-100 weighted baseline, renormalizing available components."""
    result = frame.copy()
    for column in (
        "flow_baseline_lps", "flow_observed_lps",
        "pressure_baseline_bar", "pressure_observed_bar",
        "duration_hours", "repeat_count_30d",
        "nearby_reports_7d", "criticality_index",
    ):
        result[column] = pd.to_numeric(result[column], errors="coerce")

    flow_valid = result["flow_baseline_lps"].gt(0) & result["flow_observed_lps"].ge(0)
    flow_increase = result["flow_observed_lps"] / result["flow_baseline_lps"] - 1.0
    flow_score = (
        (flow_increase.clip(lower=0.0) / 1.0).clip(upper=1.0) * 100.0
    ).where(flow_valid)

    pressure_valid = (
        result["pressure_baseline_bar"].gt(0)
        & result["pressure_observed_bar"].ge(0)
    )
    pressure_drop = (
        result["pressure_baseline_bar"] - result["pressure_observed_bar"]
    ) / result["pressure_baseline_bar"]
    pressure_score = (
        (pressure_drop.clip(lower=0.0) / 0.35).clip(upper=1.0) * 100.0
    ).where(pressure_valid)

    components = {
        "flow_anomaly": flow_score,
        "pressure_drop": pressure_score,
        "persistence": (
            (result["duration_hours"].clip(lower=0.0) / 24.0)
            .clip(upper=1.0) * 100.0
        ),
        "repeat_events": (
            (result["repeat_count_30d"].clip(lower=0.0) / 5.0)
            .clip(upper=1.0) * 100.0
        ),
        "nearby_reports": (
            (result["nearby_reports_7d"].clip(lower=0.0) / 3.0)
            .clip(upper=1.0) * 100.0
        ),
        "asset_criticality": (
            result["criticality_index"]
            .where(result["criticality_index"].between(1, 5))
            / 5.0 * 100.0
        ),
    }

    numerator = pd.Series(0.0, index=result.index)
    denominator = pd.Series(0.0, index=result.index)
    for name, component in components.items():
        available = component.notna()
        result[f"{name}_score"] = component.round(1)
        numerator += component.fillna(0.0) * WEIGHTS[name]
        denominator += available.astype(float) * WEIGHTS[name]

    result["priority_score"] = (
        numerator / denominator.replace(0.0, np.nan)
    ).round(1)
    result["input_coverage_pct"] = (denominator * 100.0).round(0)
    score = result["priority_score"]
    result["priority_band"] = np.select(
        [score.ge(70.0), score.ge(40.0)],
        ["High", "Review"],
        default="Routine",
    )
    result.loc[score.isna(), "priority_band"] = "Unranked"

    reasons = []
    for _, row in result.iterrows():
        contributions = []
        for name, label in LABELS.items():
            value = row.get(f"{name}_score")
            if pd.notna(value) and float(value) >= 40.0:
                contributions.append((float(value) * WEIGHTS[name], label))
        contributions.sort(key=lambda item: (-item[0], item[1]))
        if contributions:
            reasons.append("; ".join(label for _, label in contributions[:2]))
        elif pd.isna(row["priority_score"]):
            reasons.append("Insufficient valid input")
        else:
            reasons.append("No strong component signal")
    result["reason_codes"] = reasons
    return result
