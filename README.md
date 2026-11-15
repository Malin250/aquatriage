# AquaTriage

AquaTriage is a Streamlit prototype for recording and prioritizing **erosion-site observations for human follow-up**. It supports a fictional demonstration dataset, an anonymized CSV, or a session-only field register. The queue is an explainable screening aid—not an erosion forecast, slope-stability assessment, hazard rating, or prescription for a treatment.

## Run locally (Windows PowerShell)

From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the displayed local address. Start with **Synthetic sample** to explore the queue without real site data.

## Workflow

1. Select the session field register, fictional sample, or an anonymized CSV.
2. Download the CSV template or add a field observation. Use a pseudonymous site ID and approved coarse area labels; leave unassessed fields blank.
3. Review the ordered queue, contributing indicators, missing-input coverage, and data-quality warnings.
4. Filter, save a temporary human review status, and export the visible queue.

Uploads and statuses are held in Streamlit session memory, not persisted by this prototype to a database. When deployed to a server, uploads are sent to that host; review its access, logging, retention, and deletion policies before using any non-public data.

## Screening assumptions and limits

The score uses assessor-entered indicators and provisional project weights/scales documented in [docs/02_DATA_SPEC.md](docs/02_DATA_SPEC.md). Missing values are omitted and the remaining weights are renormalized; coverage is not confidence. The bands and weights are **not scientifically or operationally validated**. Do not interpret the score as probability, predictability, or evidence that a site is safe.

This app does not connect to GIS, rainfall, sensors, emergency services, or agency systems. It does not recommend a site-specific erosion-control intervention. A competent local erosion-control or geotechnical professional must verify observations, evaluate causes and downstream exposure, and decide suitable action. Follow local emergency and safeguarding procedures for immediate danger; do not wait for a queue score.

Before any real-world pilot, obtain land/data-owner authorization, agree privacy and retention controls, validate the field rubric and queue against local expert review and outcome data, and conduct a field usability/safety review. This repository does not establish field efficacy or deployment readiness.

## Project layout

- `app.py` — Streamlit field register, queue, filters, review status, and export.
- `src/schema.py` — CSV contract, normalization, and validation.
- `src/scoring.py` — transparent provisional screening score and reasons.
- `src/demo_data.py` — deterministic fictional sample records.
- `docs/` — data, product, field-validation, and architecture notes.
- `tests/` — focused validation and scoring tests.
