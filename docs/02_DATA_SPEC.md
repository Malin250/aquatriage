# Data Specification: AquaTriage

## Purpose
One row represents a candidate event for human review; the app does not diagnose a leak. Built-in records are fictional. Use utility data only after the owner approves fields, anonymization, access, purpose, retention, and deletion.

## CSV contract
UTF-8 CSV with case-sensitive headers. All headers are required. Numeric feature cells may be blank; missing values reduce coverage and are omitted from scoring.

| Field | Type / unit | Meaning and validation |
|---|---|---|
| candidate_id | string | Unique pseudonymous event ID; no customer account ID. |
| reported_at | ISO datetime | Report/create time. Timestamps without a zone are interpreted as UTC, then displayed in Africa/Kigali. |
| district | string | Coarse approved district label. |
| zone_id | string | Pseudonymous operational zone, not an address. |
| flow_baseline_lps | number, L/s | Reference flow, greater than zero. |
| flow_observed_lps | number, L/s | Observed flow in same context, non-negative. |
| pressure_baseline_bar | number, bar | Reference pressure, greater than zero. |
| pressure_observed_bar | number, bar | Observed pressure, non-negative. |
| duration_hours | number, hours | Current signal duration, non-negative. |
| repeat_count_30d | integer | Previous candidate events in zone over the preceding 30 days, non-negative. |
| nearby_reports_7d | integer | Corroborating reports in the same approved coarse zone over 7 days, non-negative. |
| criticality_index | integer, 1-5 | Partner-defined asset/service criticality; agree the scale with the owner. |

Unknown columns are discarded. Blank candidate IDs receive temporary session IDs and a warning. Duplicate IDs and blank zones are warned. Invalid numerics, negative values, non-integer counts, and criticality outside 1-5 become missing; they are never set to zero.

## Baseline component formulas
Components are clipped to 0-100. Weights sum to 100%.

| Component | Weight | Formula |
|---|---:|---|
| Flow anomaly | 18% | 100 * clip((observed / baseline - 1) / 1.0, 0, 1) |
| Pressure drop | 12% | 100 * clip(((baseline - observed) / baseline) / 0.35, 0, 1) |
| Persistence | 25% | 100 * clip(duration_hours / 24, 0, 1) |
| Repeat events | 15% | 100 * clip(repeat_count_30d / 5, 0, 1) |
| Nearby reports | 15% | 100 * clip(nearby_reports_7d / 3, 0, 1) |
| Asset criticality | 15% | 100 * criticality_index / 5 |

clip limits a value to the 0-1 range. Scales and display bands are assumptions, not engineering standards; validate them with the owner and reviewed outcomes.

Priority is the weighted average of available components. Missing feature weights are omitted and remaining weights renormalized. With no valid components, the record is unranked. Input coverage is the fraction of original scoring weight represented by valid components. It is not confidence or probability.

## Experimental AI fields
Isolation Forest uses available component scores as features. It runs only with at least 20 candidate rows, each eligible row having at least three valid components, and at least three sufficiently populated features. Missing model inputs are median-imputed within the batch. The model uses contamination 0.10; flag/index are exploratory and relative to the current batch. The index is not a probability and does not change the baseline score.

## Privacy
Do not collect names, phone numbers, account IDs, credentials, precise household locations, or raw customer reports. Use aggregate corroboration counts and pseudonymous zones. The local app does not write uploads to a database; statuses are temporary. Never commit real exports to source control.
