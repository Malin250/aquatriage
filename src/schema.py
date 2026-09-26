"""Input schema, normalization, and row-level validation."""

from __future__ import annotations

import numpy as np
import pandas as pd

EXPECTED_COLUMNS = [
    "candidate_id",
    "reported_at",
    "district",
    "zone_id",
    "flow_baseline_lps",
    "flow_observed_lps",
    "pressure_baseline_bar",
    "pressure_observed_bar",
    "duration_hours",
    "repeat_count_30d",
    "nearby_reports_7d",
    "criticality_index",
]

NUMERIC_COLUMNS = [
    "flow_baseline_lps",
    "flow_observed_lps",
    "pressure_baseline_bar",
    "pressure_observed_bar",
    "duration_hours",
    "repeat_count_30d",
    "nearby_reports_7d",
    "criticality_index",
]


def validate_records(
    source: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str], dict[str, int], list[str]]:
    """Return known columns, warnings, invalid-cell counts, and ignored headers."""
    missing = [name for name in EXPECTED_COLUMNS if name not in source.columns]
    extras = [str(name) for name in source.columns if name not in EXPECTED_COLUMNS]
    if missing:
        return pd.DataFrame(), ["Missing required headers: " + ", ".join(missing)], {}, extras

    frame = source[EXPECTED_COLUMNS].copy()
    warnings: list[str] = []
    invalid_counts: dict[str, int] = {}

    for name in ("candidate_id", "district", "zone_id"):
        frame[name] = frame[name].astype("string").str.strip()

    raw_time = frame["reported_at"]
    nonblank_time = raw_time.notna() & raw_time.astype("string").str.strip().ne("")
    parsed_time = pd.to_datetime(raw_time, errors="coerce", utc=True)
    bad_time = nonblank_time & parsed_time.isna()
    if bad_time.any():
        invalid_counts["reported_at"] = int(bad_time.sum())
    frame["reported_at"] = parsed_time.dt.tz_convert("Africa/Kigali")

    for name in NUMERIC_COLUMNS:
        raw = frame[name]
        nonblank = raw.notna() & raw.astype("string").str.strip().ne("")
        parsed = pd.to_numeric(raw, errors="coerce")
        bad_parse = nonblank & parsed.isna()
        frame[name] = parsed
        invalid_counts[name] = int(bad_parse.sum())

    rules = {
        "flow_baseline_lps": frame["flow_baseline_lps"].le(0),
        "flow_observed_lps": frame["flow_observed_lps"].lt(0),
        "pressure_baseline_bar": frame["pressure_baseline_bar"].le(0),
        "pressure_observed_bar": frame["pressure_observed_bar"].lt(0),
        "duration_hours": frame["duration_hours"].lt(0),
    }
    for name in ("repeat_count_30d", "nearby_reports_7d"):
        values = frame[name]
        rules[name] = values.notna() & (
            values.lt(0) | values.mod(1).ne(0)
        )
    criticality = frame["criticality_index"]
    rules["criticality_index"] = criticality.notna() & (
        ~criticality.between(1, 5) | criticality.mod(1).ne(0)
    )

    for name, invalid_mask in rules.items():
        invalid_mask = invalid_mask.fillna(False)
        invalid_counts[name] = invalid_counts.get(name, 0) + int(invalid_mask.sum())
        frame.loc[invalid_mask, name] = np.nan

    missing_id = frame["candidate_id"].isna() | frame["candidate_id"].eq("")
    if missing_id.any():
        warnings.append(
            f"{int(missing_id.sum())} row(s) have no candidate_id; "
            "temporary IDs were assigned for this session."
        )
        frame.loc[missing_id, "candidate_id"] = [
            f"UNSPECIFIED-{i:03d}" for i in range(1, int(missing_id.sum()) + 1)
        ]

    frame["district"] = frame["district"].fillna("Unknown").replace("", "Unknown")
    frame["zone_id"] = frame["zone_id"].fillna("").astype("string")

    duplicate = frame["candidate_id"].duplicated(keep=False)
    if duplicate.any():
        warnings.append(
            f"{int(duplicate.sum())} row(s) share a candidate_id. "
            "Review identifiers; session review statuses use row identity."
        )
    if frame["zone_id"].eq("").any():
        warnings.append("Some rows have a blank zone_id.")
    if extras:
        warnings.append("Extra columns were discarded: " + ", ".join(extras))
    if frame.empty:
        warnings.append("The input has headers but no candidate rows.")

    invalid_counts = {key: value for key, value in invalid_counts.items() if value > 0}
    return frame.reset_index(drop=True), warnings, invalid_counts, extras
