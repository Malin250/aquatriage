import numpy as np
import pandas as pd
from pathlib import Path
from streamlit.testing.v1 import AppTest

from src.schema import EXPECTED_COLUMNS, validate_records
from src.scoring import score_candidates


def observation(**overrides):
    row = {
        "site_id": "SITE-001",
        "assessed_at": "2026-03-01T10:00:00+02:00",
        "district": "Example area",
        "site_type": "Hillside",
        "slope_percent": 20,
        "bare_soil_percent": 50,
        "drainage_concern_0_5": 2,
        "erosion_evidence_0_5": 3,
        "runoff_concentration_0_5": 2,
        "exposed_asset_0_5": 1,
    }
    return {**row, **overrides}


def test_score_uses_only_available_inputs_and_reports_coverage():
    frame = pd.DataFrame(
        [
            observation(
                slope_percent=np.nan,
                bare_soil_percent=np.nan,
                drainage_concern_0_5=4,
                erosion_evidence_0_5=2,
                runoff_concentration_0_5=np.nan,
                exposed_asset_0_5=np.nan,
            )
        ]
    )

    scored = score_candidates(frame).iloc[0]

    assert scored["priority_score"] == 56.0
    assert scored["input_coverage_pct"] == 50.0
    assert scored["priority_band"] == "Review"
    assert "Drainage concern" in scored["reason_codes"]
    assert pd.isna(scored["slope_score"])


def test_row_with_no_valid_indicators_is_unranked():
    frame = pd.DataFrame(
        [observation(**{column: np.nan for column in EXPECTED_COLUMNS[4:]})]
    )

    scored = score_candidates(frame).iloc[0]

    assert pd.isna(scored["priority_score"])
    assert scored["priority_band"] == "Unranked"
    assert scored["input_coverage_pct"] == 0.0
    assert scored["reason_codes"] == "Insufficient valid observations"


def test_validation_excludes_invalid_measurements_and_discards_extra_fields():
    frame = pd.DataFrame(
        [
            observation(
                slope_percent=101,
                bare_soil_percent="not measured",
                drainage_concern_0_5=6,
                erosion_evidence_0_5=2.5,
                private_note="not part of the schema",
            ),
            observation(site_id="SITE-001"),
        ]
    )

    clean, warnings, invalid_counts, ignored_columns = validate_records(frame)

    assert pd.isna(clean.loc[0, "slope_percent"])
    assert pd.isna(clean.loc[0, "bare_soil_percent"])
    assert pd.isna(clean.loc[0, "drainage_concern_0_5"])
    assert pd.isna(clean.loc[0, "erosion_evidence_0_5"])
    assert invalid_counts == {
        "slope_percent": 1,
        "bare_soil_percent": 1,
        "drainage_concern_0_5": 1,
        "erosion_evidence_0_5": 1,
    }
    assert ignored_columns == ["private_note"]
    assert any("share a site_id" in warning for warning in warnings)
    assert "private_note" not in clean.columns


def test_validation_reports_missing_headers_without_scoring_rows():
    frame = pd.DataFrame([{"site_id": "SITE-001"}])

    clean, warnings, invalid_counts, ignored_columns = validate_records(frame)

    assert clean.empty
    assert warnings[0].startswith("Missing required headers:")
    assert invalid_counts == {}
    assert ignored_columns == []


def test_streamlit_field_register_starts_without_app_errors():
    app_path = Path(__file__).resolve().parents[1] / "app.py"

    app = AppTest.from_file(str(app_path)).run()

    assert not app.exception
    assert any(
        "Start an observation register" in message.value for message in app.subheader
    )


def test_streamlit_synthetic_queue_renders_without_app_errors():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()

    app.selectbox[-1].set_value("Synthetic sample").run()

    assert not app.exception
    assert any("Sites in view" == metric.label for metric in app.metric)
    assert len(app.dataframe) >= 1


def test_field_observation_is_added_to_session_queue():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()

    app.text_input[0].set_value("FIELD-001")
    app.text_input[1].set_value("Approved area")
    app.number_input[0].set_value(25.0)
    app.number_input[1].set_value(80.0)
    app.form_submit_button[0].click().run()

    assert not app.exception
    records = app.session_state["field_observations"]["field-register-v1"]
    assert len(records) == 1
    assert records[0]["site_id"] == "FIELD-001"
    assert app.dataframe[0].value.iloc[0]["site_id"] == "FIELD-001"
    assert app.dataframe[0].value.iloc[0]["input_coverage_pct"] == 15.0
