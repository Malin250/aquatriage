"""Deterministic, fictional records for the demo only."""

from __future__ import annotations

import numpy as np
import pandas as pd


def make_demo_data(rows: int = 45) -> pd.DataFrame:
    """Generate fictional candidate records; not measured utility data."""
    rng = np.random.default_rng(2026)
    demo_areas = ["Demo area A", "Demo area B", "Demo area C"]
    today = pd.Timestamp.now(tz="Africa/Kigali").normalize()
    records = []

    for index in range(rows):
        synthetic_outlier = index in {7, 19, 32, 41}
        flow_baseline = float(rng.uniform(3.0, 18.0))
        pressure_baseline = float(rng.uniform(2.4, 5.2))
        flow_multiplier = (
            float(rng.uniform(1.8, 2.5))
            if synthetic_outlier
            else float(rng.uniform(0.9, 1.45))
        )
        pressure_loss = (
            float(rng.uniform(0.28, 0.42))
            if synthetic_outlier
            else float(rng.uniform(0.0, 0.2))
        )
        duration = (
            float(rng.uniform(25.0, 48.0))
            if synthetic_outlier
            else float(rng.uniform(0.3, 18.0))
        )
        row = {
            "candidate_id": f"DEMO-{index + 1:03d}",
            "reported_at": (
                today - pd.Timedelta(days=int(rng.integers(0, 28)))
            ).isoformat(),
            "district": demo_areas[index % len(demo_areas)],
            "zone_id": f"DEMO-ZONE-{(index % 12) + 1:02d}",
            "flow_baseline_lps": round(flow_baseline, 2),
            "flow_observed_lps": round(flow_baseline * flow_multiplier, 2),
            "pressure_baseline_bar": round(pressure_baseline, 2),
            "pressure_observed_bar": round(
                pressure_baseline * (1.0 - pressure_loss), 2
            ),
            "duration_hours": round(duration, 1),
            "repeat_count_30d": int(rng.integers(0, 5)),
            "nearby_reports_7d": int(rng.integers(0, 4)),
            "criticality_index": int(rng.integers(1, 6)),
        }
        if index in {4, 15, 28}:
            row["flow_observed_lps"] = np.nan
        if index in {10, 34}:
            row["pressure_observed_bar"] = np.nan
        records.append(row)

    return pd.DataFrame.from_records(records)
