# Architecture: WASAC Triage

## Runtime flow

    Synthetic demo or user-uploaded CSV
                   |
                   v
       src/schema.py: validate and normalize
                   |
                   v
       src/scoring.py: explainable baseline
                   |
          +--------+----------+
          |                   |
          v                   v
    Human review UI     src/anomaly.py
    and CSV export      Isolation Forest
          |                   |
          +---- separate -----+

The AI screen is parallel to the baseline and never changes priority_score.

## Stack
- Python 3.10+
- Streamlit for the local dashboard.
- pandas and NumPy for CSV handling, validation, and features.
- Plotly for queue and data-quality charts.
- scikit-learn IsolationForest for the optional experimental outlier screen.
- CSV input/export; no database, external API, production credentials, or utility-system connector.

## Code layout
- app.py: pages, filters, user interaction, export.
- src/schema.py: required headers, parsing, validation, discarded extras.
- src/demo_data.py: deterministic fictional records.
- src/scoring.py: component features, weighted priority, bands, reasons.
- src/anomaly.py: separate batch-relative Isolation Forest flag.
- docs/: product, data, architecture, privacy, and evaluation.
- requirements.txt: runtime libraries.
- README.md: Windows setup and launch instructions.
- .gitignore: virtualenv, secrets, and CSV safeguards.

## AI boundary and evaluation
The current Isolation Forest fits and scores the loaded batch; this demonstrates unsupervised screening, not field detection. The batch may not represent normal network behavior, so flags depend on which records were uploaded. Do not call a flag a leak or probability, and do not combine it with priority ranking before evaluation.

For later study, secure approved representative time-series data and reviewed outcomes. Compare a transparent threshold baseline, the rule score, and model candidates using time-aware splits, precision@K/recall@K, false-priority rate, missing-data stability, and expert review. Do not train and evaluate on the same rows and claim performance.

## Privacy and operations
- Process uploads during the app session; do not persist them or send them to external AI services.
- Discard unknown columns before display/export.
- Keep review statuses in Streamlit session state only.
- Never connect to valves, pumps, dispatch, or production systems.
- Keep personal data, credentials, and private CSVs out of source control.
- A future pilot requires written authorization, access controls, retention/deletion rules, and an operational owner.

## Run locally
From the project root, create and activate a Python virtual environment, install requirements.txt, then run python -m streamlit run app.py. Start with synthetic mode; the app presents its limits and a CSV template.
