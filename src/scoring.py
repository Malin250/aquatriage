"""Transparent provisional screening score for erosion-site observations."""

from __future__ import annotations

import numpy as np
import pandas as pd

WEIGHTS = {
    "erosion_evidence": 0.30,
    "drainage_concern": 0.20,
    "runoff_concentration": 0.20,
    "exposed_asset": 0.15,
    "bare_soil": 0.10,
    "slope": 0.05,
}
LABELS = {
    "erosion_evidence": "Observed erosion evidence",
    "drainage_concern": "Drainage concern",
    "runoff_concentration": "Concentrated runoff",
    "exposed_asset": "Exposed people, assets, or receiving areas",
    "bare_soil": "Bare soil",
    "slope": "Slope",
}
COMPONENT_COLUMNS = [f"{name}_score" for name in WEIGHTS]


def score_candidates(frame: pd.DataFrame) -> pd.DataFrame:
    """Calculate a provisional 0-100 score, renormalizing available inputs."""
    result = frame.copy()
    numeric_columns = (
        "slope_percent",
        "bare_soil_percent",
        "drainage_concern_0_5",
        "erosion_evidence_0_5",
        "runoff_concentration_0_5",
        "exposed_asset_0_5",
    )
    for column in numeric_columns:
        result[column] = pd.to_numeric(result[column], errors="coerce")

    components = {
        "erosion_evidence": result["erosion_evidence_0_5"] / 5.0 * 100.0,
        "drainage_concern": result["drainage_concern_0_5"] / 5.0 * 100.0,
        "runoff_concentration": result["runoff_concentration_0_5"] / 5.0 * 100.0,
        "exposed_asset": result["exposed_asset_0_5"] / 5.0 * 100.0,
        "bare_soil": result["bare_soil_percent"],
        "slope": (result["slope_percent"] / 30.0 * 100.0).clip(upper=100.0),
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
        ["Higher review priority", "Review"],
        default="Routine review",
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
            reasons.append("Insufficient valid observations")
        else:
            reasons.append("No elevated recorded indicator")
    result["reason_codes"] = reasons
    return result
