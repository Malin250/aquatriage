# Product Requirements Document: AquaTriage

- Type: Bachelor capstone decision-support prototype
- Primary prospective partner: WASAC Utility Ltd
- Potential innovation partner: MININFRA
- Version: 1.0

## Product summary
AquaTriage ranks suspected water-network leak or abnormality candidates for human inspection. It makes the baseline score explainable, shows missing inputs, and offers a separate experimental unsupervised anomaly screen. That screen explores unusual records in the current batch; it does not confirm leaks.

The project is a local prototype. It has no live WASAC connection, work-order integration, valve control, or production claim. Built-in records are synthetic.

## Problem
Operations staff may receive several candidate reports or telemetry anomalies while having limited time for inspection. A consistent queue can help compare evidence and identify where a human reviewer may want to look first. Validate the real workflow and approved data with WASAC before claiming operational fit.

## Users
- Operations analyst / dispatcher: loads an approved list, filters and reviews candidates, exports an inspection worklist.
- Supervisor: reviews score assumptions and outcome measures.
- Field technician: completes inspections through existing utility processes.
- Student developer: builds the prototype and documents its evaluation and limits.

## Goals
1. Create a reproducible, explainable ranking for candidate events.
2. Make missing and invalid values visible.
3. Demonstrate AI/data science using a separately labeled Isolation Forest experiment.
4. Automate CSV checks, feature calculations, ranking, reason generation, and export.
5. Compare the transparent baseline and experimental screen against reviewed outcomes before proposing a pilot.

## Non-goals and safeguards
- No claim this is Rwanda's first leak-related solution.
- No automatic leak confirmation, dispatch, or equipment control.
- No household profiling or customer-identifying input.
- No unauthorized utility data.
- No assertion that a score is probability, field accuracy, or guaranteed water savings.
- AI anomaly results do not modify or combine with the human priority score.

## MVP features
- Streamlit local dashboard with synthetic demo mode and CSV upload.
- Fixed CSV schema and row-level validation.
- Weighted 0-100 transparent score, display band, reasons, and input coverage.
- Optional Isolation Forest screen fit and scored on the loaded batch.
- Outlier flag and within-batch index displayed separately from priority.
- District and band filters, case detail, session-only review status, queue export, and template download.
- Data-quality summary and synthetic-data labels.
- No database or outbound API calls.

## Core user tasks and acceptance criteria
1. Start the app and see clearly labeled synthetic records.
2. Upload a CSV; see missing headers or a ranked queue.
3. See invalid/missing readings reflected in coverage, not silently changed to zero.
4. Filter cases and inspect score components and reason codes.
5. Run or skip the experimental AI screen and see its limitations.
6. Set a review status for the current session and export a filtered CSV.
7. Confirm extra columns are discarded and not included in view/export.

## Baseline score
| Component | Weight |
|---|---:|
| Flow anomaly | 18% |
| Pressure drop | 12% |
| Signal persistence | 25% |
| Repeat events in zone | 15% |
| Nearby reports | 15% |
| Asset criticality | 15% |

Feature scales are in docs/02_DATA_SPEC.md. Valid weights are renormalized per row when data is missing. Coverage reports the valid original weight fraction. Initial bands (High >=70, Review >=40, Routine <40) are demo assumptions that require partner review.

## AI and data science
Isolation Forest operates on the six engineered 0-100 component features. It needs at least 20 rows with at least three valid components, uses median imputation, and has a fixed 10% contamination setting for this experiment. It is fit only to the currently loaded batch. Its relative outlier index is not probability or leak likelihood. Model output does not affect the baseline priority score.

The candidate batch may contain selected events rather than representative normal network behavior. The experimental flag can change with file composition. It is not a substitute for a time-series detector, engineering threshold, or supervised model. Keep it exploratory until evaluated on approved, representative data.

## Evaluation plan
- Compare baseline top-K precision, recall, false-priority rate, and ranking stability against an agreed threshold baseline when reviewed outcomes exist.
- Evaluate AI flags separately: precision/recall on reviewed cases, stability under missing data, and expert review of false positives.
- Never report synthetic-data performance as real-world accuracy.
- Conduct a small consented usability session and document participants, tasks, and limitations.
- Agree pilot baseline, duration, owner, and impact measures with WASAC before a field claim.

## Privacy and governance
Use synthetic records for public demos. Before utility data, get written approval for purpose, fields, access, retention, and deletion. Exclude customer identifiers, precise household coordinates, account numbers, contact details, and credentials. Review status stays in session state; uploaded records are not persisted to a database.

## Build sequence
1. Confirm workflow and capstone scope with a supervisor/partner.
2. Run the local synthetic demo and review scoring/data rules.
3. Gather usability feedback.
4. Request only approved anonymized records if a partner permits them.
5. Establish outcome labels and baseline evaluation.
6. Present measured results and limitations; propose a supervised pilot only with partner approval.
