# Architecture: AquaTriage

## Runtime flow

```text
Fictional sample / anonymized CSV / session field register
                          |
                          v
          src/schema.py: normalize and validate
                          |
                          v
          src/scoring.py: provisional indicator score
                          |
                          v
          app.py: filters, review status, data quality, CSV export
```

The score is an explicitly unvalidated screening heuristic. The UI provides no site-specific treatment prescription, sensor analysis, GIS overlay, rainfall feed, or external service call.

## Code layout

- `app.py`: Streamlit UI and in-memory session workflow.
- `src/schema.py`: required observation fields, normalization, range validation, warning counts.
- `src/scoring.py`: provisional component scaling, weighted score, bands, and explanation labels.
- `src/demo_data.py`: deterministic fictional sample records.
- `docs/`: product, field-data, and validation assumptions.
- `tests/`: focused schema and scoring tests.

## Data and state

CSV inputs are restricted to the declared schema before scoring/export. Field-register entries and review statuses live in Streamlit session state; there is no database or application-level durable storage. Hosting the app makes the host a data recipient, so network deployment requires a separate privacy, access, logging, retention, and deletion review.

## Validation boundary

There are no validated geotechnical models, local engineering thresholds, trained erosion models, verified field outcomes, or efficacy claims. Weights, scales, slope reference, and display bands are prototype assumptions. Before a pilot, qualified local specialists must assess the rubric, safe collection workflow, score utility, false negatives, and escalation process using owner-approved local evidence. No score should delay emergency response or substitute for professional site assessment.

## Local checks

Run focused tests with:

```powershell
python -m pytest
```

Start the app from the repository root with `python -m streamlit run app.py` after installing `requirements.txt`.
