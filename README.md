# WASAC Triage

A local bachelor-project prototype that prioritizes suspected water-network events for human inspection. It combines a transparent weighted score with an optional experimental Isolation Forest screen. It is not a leak diagnosis, production WASAC integration, leak probability, or automatic dispatch system.

## Start locally (Windows PowerShell)

    cd "$env:USERPROFILE\Desktop\wasac-triage-app"
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install -r requirements.txt
    python -m streamlit run app.py

Use Python 3.10 or newer. The first run starts in synthetic demo mode. Use the sidebar to upload a CSV following docs/02_DATA_SPEC.md.

## Implemented
- Fictional demo records, clearly labeled.
- CSV validation; extra columns are discarded and invalid measurements reduce input coverage.
- Explainable weighted score, priority band, component reasons, and data-quality view.
- Optional Isolation Forest flag/index, displayed separately and never mixed into priority.
- District and band filters, case details, temporary review status, queue export, and blank CSV template.
- No database, external API, operational control, or persistent upload storage.

## Data boundary
Use synthetic data for demos. Use utility data only with explicit owner authorization and approved anonymized fields. Do not upload names, accounts, contact details, household locations, passwords, or production credentials. Do not publish private records.

The model fits and scores the currently loaded batch. Its outlier index ranks rows relative to that batch; it is not probability or a validated leak prediction. Do not report synthetic-data performance as field accuracy. Keep the AI screen experimental until assessed on approved, representative data and a documented evaluation plan.

## Structure
- app.py: Streamlit application.
- src/schema.py: CSV contract and validation.
- src/scoring.py: baseline score and reason codes.
- src/anomaly.py: separate exploratory Isolation Forest screen.
- src/demo_data.py: deterministic synthetic records.
- docs/: product, data, and architecture specifications.
- requirements.txt: runtime libraries.
