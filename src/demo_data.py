"""Deterministic, fictional erosion-site records for the demo only."""

from __future__ import annotations

import numpy as np
import pandas as pd


def make_demo_data(rows: int = 36) -> pd.DataFrame:
    """Generate fictional site observations, not measured field data."""
    rng = np.random.default_rng(2026)
    areas = ["Demo area A", "Demo area B", "Demo area C"]
    site_types = ["Roadside drain", "Hillside", "Stream bank", "Cultivated land"]
    today = pd.Timestamp.now(tz="Africa/Kigali").normalize()
    records = []

    for index in range(rows):
        flagged_example = index in {5, 14, 22, 31}
        record = {
            "site_id": f"DEMO-{index + 1:03d}",
            "assessed_at": (
                today - pd.Timedelta(days=int(rng.integers(0, 30)))
            ).isoformat(),
            "district": areas[index % len(areas)],
            "site_type": site_types[index % len(site_types)],
            "slope_percent": round(
                float(rng.uniform(18.0, 38.0) if flagged_example else rng.uniform(1, 24)),
                1,
            ),
            "bare_soil_percent": round(
                float(rng.uniform(65, 98) if flagged_example else rng.uniform(5, 70)),
                1,
            ),
            "drainage_concern_0_5": int(
                rng.integers(4, 6) if flagged_example else rng.integers(0, 4)
            ),
            "erosion_evidence_0_5": int(
                rng.integers(4, 6) if flagged_example else rng.integers(0, 4)
            ),
            "runoff_concentration_0_5": int(
                rng.integers(4, 6) if flagged_example else rng.integers(0, 4)
            ),
            "exposed_asset_0_5": int(rng.integers(1, 6)),
        }
        if index in {3, 11, 25}:
            record["slope_percent"] = np.nan
        if index in {8, 28}:
            record["drainage_concern_0_5"] = np.nan
        records.append(record)

    return pd.DataFrame.from_records(records)
