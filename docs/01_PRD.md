# Product Requirements Document: WASAC Triage

- Type: Bachelor capstone decision-support prototype
- Primary prospective partner: WASAC Utility Ltd
- Potential innovation partner: MININFRA
- Version: 0.1

## Product summary
WASAC Triage turns suspected water-network leak or abnormality reports into an explainable inspection queue. It combines flow and pressure deviations, signal duration, repeat events, nearby reports, and asset criticality. It explains each ranking and leaves inspection decisions with utility staff.

This is a prototype. It does not confirm leaks, control valves, or treat a high score as a diagnosis. It runs on synthetic examples or a CSV approved by the data owner.

## Problem and opportunity
When several possible network issues are reported, staff need a consistent way to decide which location to inspect first. Signals may be noisy, incomplete, or spread across records. A transparent queue could help compare cases, show missing information, and record review decisions. Validate the actual workflow and data fields with a utility partner. The student demo does not require live utility access.

## Users
- Operations analyst / dispatcher: imports approved records, reviews and filters the queue, inspects explanations, and exports a worklist.
- Supervisor: reviews priority bands and data coverage, assigns inspections through existing processes, and evaluates outcomes.
- Field technician: inspects assigned locations through existing processes and returns an outcome.
- Student developer: implements the prototype and evaluates it on synthetic or approved examples.

## Goals
1. Rank submitted candidate events consistently and transparently.
2. Show component scores, reason codes, and input coverage.
3. Validate a documented CSV schema and make missing data visible.
4. Let users filter, inspect, update temporary review status, and export a queue.
5. Define evaluation against a simple baseline before any field trial.
6. Keep the demo usable without sensors, paid APIs, or production credentials.

## Non-goals and boundaries
- No claim to be Rwanda's first or only leak-related system.
- No autonomous leak confirmation, dispatch, or operational control.
- No household-level monitoring or customer-identifying data.
- No connection to WASAC production systems.
- No guaranteed reduction in water loss, response time, or cost.
- No model trained on invented data presented as validated AI.

## MVP scope
Included: Streamlit dashboard, labeled synthetic data, CSV upload and validation, explainable 0-100 weighted score, priority band, reason codes and input coverage, district filter, case detail, session-only review status, CSV export, and a clear decision-support notice. No database or external service calls.

Deferred: login, persistent multi-user status, database, audit log, mobile forms, notifications, work-order integration, live telemetry, sensors, digital twin, production hosting, and an ML model in the operational ranking path.

## User stories and acceptance criteria
### Import and inspect
- An analyst can explore synthetic data without private records.
- An analyst can upload a CSV with the documented headers.
- Missing required headers are listed and the incompatible file is not scored.
- Extra columns are ignored after a warning.
- Missing or invalid feature values reduce input coverage; they are not silently changed to zero.

### Prioritize and review
- Candidates are sorted by a reproducible score, with a band and up to two concise reasons.
- Each score can be traced to the documented feature formulas.
- The UI says the score is not leak probability or diagnosis.
- Review states are Needs review, Reviewed, Assigned, or Closed, and apply only to the current session.
- The user can download the filtered ranked queue as CSV.

### Prototype targets
- A 1,000-row CSV remains practical on a typical student laptop; record actual load time.
- Identical input produces identical ranking.
- When outcomes are available, compare top-K precision and recall with a simple threshold baseline.
- Gather usability feedback from a small, consented group and report limitations.

## Ranking method
The MVP uses a transparent weighted rule, not a trained model.

| Signal | Weight |
|---|---:|
| Abnormal flow increase | 18% |
| Pressure drop | 12% |
| Signal persistence | 25% |
| Repeat events in zone | 15% |
| Nearby reports | 15% |
| Asset criticality | 15% |

Feature scales are in 02_DATA_SPEC.md. Missing or invalid features are omitted; remaining weights are renormalized. Input coverage is reported separately. Initial bands are High (70-100), Review (40-69.9), and Routine (0-39.9). These are demo thresholds; calibrate with partner-reviewed outcomes before field use.

## AI, data science, and automation
- MVP data science: validation, feature engineering, transparent scoring, ranking, and evaluation.
- MVP automation: CSV checks, score calculation, sorting, reason generation, and queue export.
- Future AI experiment: compare a suitable anomaly detector, such as Isolation Forest, against the transparent baseline only after sufficient approved data and a documented evaluation set exist.
- Staff decide what to inspect. A score must not create a confirmed leak label by itself.

## Data and privacy
Use synthetic records for public demonstrations. Obtain written authorization before using utility records. Request the smallest anonymized dataset needed. Exclude names, phone numbers, account numbers, precise household locations, and credentials. Keep demo data local and follow the data owner's access and retention rules. Input coverage is not model confidence, probability, or certainty.

## Success measures
Prototype measures: valid rows accepted, invalid input explained, reproducible rankings, reasons and coverage visible, top-K precision/recall and false-priority rate measured when labels exist, and usability feedback recorded.
For a later approved pilot, agree the baseline period, comparison method, owner, and metrics with WASAC. Candidate measures include time to first inspection, confirmed cases among top-K inspections, repeat visits, and repair completion time. Do not infer water savings from app use alone.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| No operational data access | Use marked synthetic examples and request workflow feedback first. |
| Overstated novelty | Describe the human-triage contribution and validate with supervisor and utility staff. |
| Missing or noisy telemetry | Show input coverage and require human review. |
| False priorities | Compare with a baseline and inspect false positives and negatives. |
| Accidental sensitive upload | Document allowed fields, ignore extras, and do not persist uploads. |
| Demo mistaken for production | Keep the scope notice visible. |

## Build sequence
1. Confirm scope with supervisor.
2. Implement the CSV schema and synthetic records.
3. Build scoring, explanations, and queue.
4. Add validation, export, and usability feedback.
5. If approved records become available, compare the baseline to an anomaly model.
6. Present measured findings and limitations; propose a supervised pilot only with partner approval.