"""Input schema, normalization, and row-level validation for site observations."""

from __future__ import annotations

import numpy as np
import pandas as pd

EXPECTED_COLUMNS = [
    "site_id",
    "assessed_at",
    "district",
    "site_type",
    "slope_percent",
    "bare_soil_percent",
    "drainage_concern_0_5",
    "erosion_evidence_0_5",
    "runoff_concentration_0_5",
    "exposed_asset_0_5",
]

NUMERIC_COLUMNS = EXPECTED_COLUMNS[4:]
ORDINAL_COLUMNS = [
    "drainage_concern_0_5",
    "erosion_evidence_0_5",
    "runoff_concentration_0_5",
    "exposed_asset_0_5",
]
TEXT_COLUMNS = ["site_id", "district", "site_type"]


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

    for name in TEXT_COLUMNS:
        frame[name] = frame[name].astype("string").str.strip()

    raw_time = frame["assessed_at"]
    nonblank_time = raw_time.notna() & raw_time.astype("string").str.strip().ne("")
    parsed_time = pd.to_datetime(raw_time, errors="coerce", utc=True)
    bad_time = nonblank_time & parsed_time.isna()
    if bad_time.any():
        invalid_counts["assessed_at"] = int(bad_time.sum())
    frame["assessed_at"] = parsed_time.dt.tz_convert("Africa/Kigali")

    for name in NUMERIC_COLUMNS:
        raw = frame[name]
        nonblank = raw.notna() & raw.astype("string").str.strip().ne("")
        parsed = pd.to_numeric(raw, errors="coerce")
        bad_parse = nonblank & parsed.isna()
        frame[name] = parsed
        if bad_parse.any():
            invalid_counts[name] = int(bad_parse.sum())

    rules = {
        "slope_percent": frame["slope_percent"].lt(0) | frame["slope_percent"].gt(100),
        "bare_soil_percent": (
            frame["bare_soil_percent"].lt(0) | frame["bare_soil_percent"].gt(100)
        ),
    }
    for name in ORDINAL_COLUMNS:
        values = frame[name]
        rules[name] = values.notna() & (
            values.lt(0) | values.gt(5) | values.mod(1).ne(0)
        )

    for name, invalid_mask in rules.items():
        invalid_mask = invalid_mask.fillna(False)
        invalid_counts[name] = invalid_counts.get(name, 0) + int(invalid_mask.sum())
        frame.loc[invalid_mask, name] = np.nan

    missing_id = frame["site_id"].isna() | frame["site_id"].eq("")
    if missing_id.any():
        warnings.append(
            f"{int(missing_id.sum())} row(s) have no site_id; "
            "temporary IDs were assigned for this session."
        )
        frame.loc[missing_id, "site_id"] = [
            f"UNSPECIFIED-{i:03d}" for i in range(1, int(missing_id.sum()) + 1)
        ]

    frame["district"] = frame["district"].fillna("Unknown").replace("", "Unknown")
    frame["site_type"] = frame["site_type"].fillna("Not specified").replace(
        "", "Not specified"
    )

    duplicate = frame["site_id"].duplicated(keep=False)
    if duplicate.any():
        warnings.append(
            f"{int(duplicate.sum())} rows share a site_id. "
            "Review identifiers; session review statuses use row identity."
        )
    if frame["assessed_at"].isna().any():
        warnings.append(
            f"{int(frame['assessed_at'].isna().sum())} row(s) have no valid assessment time."
        )
    if extras:
        warnings.append("Extra columns were discarded: " + ", ".join(extras))
    if frame.empty:
        warnings.append("The input has headers but no site observations.")

    invalid_counts = {key: value for key, value in invalid_counts.items() if value > 0}
    return frame.reset_index(drop=True), warnings, invalid_counts, extras
