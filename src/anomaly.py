"""Experimental unsupervised outlier screen, separate from priority ranking."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer

from .scoring import COMPONENT_COLUMNS

MINIMUM_ROWS = 20
MINIMUM_FEATURES = 3
CONTAMINATION = 0.10


def screen_batch(
    frame: pd.DataFrame,
    minimum_rows: int = MINIMUM_ROWS,
) -> tuple[pd.DataFrame, str]:
    """Add an Isolation Forest flag without changing priority_score."""
    result = frame.copy()
    result["ai_anomaly_flag"] = "Not evaluated"
    result["ai_anomaly_index"] = np.nan

    if len(result) < minimum_rows:
        return result, f"Need at least {minimum_rows} rows for this exploratory screen."

    eligible = result[COMPONENT_COLUMNS].notna().sum(axis=1) >= MINIMUM_FEATURES
    model_rows = result.loc[eligible, COMPONENT_COLUMNS]
    if len(model_rows) < minimum_rows:
        return (
            result,
            f"Only {len(model_rows)} rows have at least {MINIMUM_FEATURES} "
            f"valid components; need {minimum_rows}.",
        )

    minimum_non_null = max(10, math.ceil(len(model_rows) * 0.5))
    useful = [
        column
        for column in COMPONENT_COLUMNS
        if int(model_rows[column].notna().sum()) >= minimum_non_null
    ]
    if len(useful) < MINIMUM_FEATURES:
        return result, "At least three scoring features must be populated across the batch."

    try:
        matrix = model_rows[useful].replace([np.inf, -np.inf], np.nan)
        matrix = SimpleImputer(strategy="median").fit_transform(matrix)
        model = IsolationForest(
            n_estimators=200,
            contamination=CONTAMINATION,
            random_state=42,
            n_jobs=1,
        )
        predictions = model.fit_predict(matrix)
        decision = model.decision_function(matrix)
    except (ValueError, FloatingPointError) as exc:
        return result, f"Experimental screen could not run: {exc}"

    indices = model_rows.index
    relative = (
        pd.Series(-decision, index=indices)
        .rank(method="average", pct=True)
        .mul(100.0)
        .round(1)
    )
    flags = pd.Series(
        np.where(predictions == -1, "Outlier review", "No outlier flag"),
        index=indices,
    )
    result.loc[indices, "ai_anomaly_index"] = relative
    result.loc[indices, "ai_anomaly_flag"] = flags
    message = (
        f"Screened {len(model_rows)} rows using {len(useful)} available features. "
        "Results are relative to this batch."
    )
    return result, message
