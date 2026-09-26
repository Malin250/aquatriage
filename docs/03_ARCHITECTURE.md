# Architecture and Technology: WASAC Triage

## MVP architecture

    Synthetic demo CSV or user-selected CSV
                      |
                      v
          Streamlit upload / data loader
                      |
                      v
             Header and value checks
                      |
                      v
       Feature engineering and rule score
                      |
                      v
       Priority queue + reasons + coverage
                      |
              +-------+-------+
              |               |
              v               v
       Human review UI     CSV export
       (session only)   (filtered results)

The MVP is a local, single-process Streamlit app. It has no database, login, background service, third-party API, telemetry connector, or production integration. Extra upload columns are ignored after a warning.

## Technology stack
MVP: Python 3.10+, Streamlit, pandas, NumPy, Plotly, and CSV. requirements.txt lists dependencies used by the app.
Possible later additions: scikit-learn for a carefully evaluated anomaly-detection experiment; SQLite or PostgreSQL only if an approved multi-user pilot needs persistence; GIS only if an approved workflow needs mapping; authentication and hosting only after security and operational review. Do not add these to the student demo just to make it look production-ready.

## Component responsibilities
- Input loader: select synthetic data or CSV, require documented headers, discard extra columns after warning, and keep uploaded data in app memory only.
- Validator: parse numbers without replacing invalid values with zero; check baselines, non-negative measurements/counts, criticality range, and duplicate IDs; show errors and warnings.
- Scoring engine: calculate six documented components, use only valid weights, renormalize over available weights, calculate coverage separately, and produce band and reasons deterministically.
- Dashboard: show a synthetic-data badge, district filter, queue, explanation, temporary review status, and filtered CSV export. State that score is not leak confirmation or probability.

## Future anomaly-model experiment
Start with the transparent rule baseline. If an authorized representative time-series dataset and reviewed labels become available:
1. Define a time-aware train/validation split to avoid leakage across nearby periods.
2. Compare the baseline with a suitable model such as Isolation Forest.
3. Evaluate precision@K, recall@K, false-priority rate, missing-data stability, and performance by zone where sample size allows.
4. Ask utility experts to review false positives and false negatives.
5. Show model score and transparent reasons separately.
6. Do not automate dispatch without owner approval and monitored validation.

Do not fit a model to synthetic demo rows and report accuracy as field performance.

## Security and operational boundaries
- Run locally for the capstone demo.
- Never commit real utility data, credentials, or private exports to source control.
- Do not use raw utility data in screenshots, slides, or a public repository.
- Do not add automated valve or pump control.
- Do not send uploads to external AI services.
- A later pilot requires written data authorization, access controls, retention/deletion rules, and an operational owner.

## Local run instructions
From the project directory:

    python -m venv .venv

Activate the environment, then run:

    python -m pip install -r requirements.txt
    streamlit run app.py

Open the local address printed by Streamlit. The app starts with synthetic demo data. Use the sidebar to try a CSV following 02_DATA_SPEC.md.