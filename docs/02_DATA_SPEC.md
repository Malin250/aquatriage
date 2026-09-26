# Data Specification: WASAC Triage

## Purpose and source boundary
This schema ranks candidate events for human review; it does not prove that an event is a leak. Built-in records are synthetic, not WASAC measurements. A data owner must approve non-synthetic data, fields, anonymization, access, retention, and use before import. Never upload customer names, phone numbers, account IDs, credentials, or household-level locations.

## CSV input contract
UTF-8 CSV, one row per candidate event. Header names are case-sensitive.

| Field | Type / unit | Header required | Cell may be blank? | Rule / meaning |
|---|---|---:|---:|---|
| candidate_id | string | Yes | No | Unique pseudonymous event ID, not a customer account ID. |
| reported_at | ISO 8601 datetime | Yes | Yes | Candidate creation or report time. |
| district | string | Yes | Yes | Coarse district label approved for the dataset. |
| zone_id | string | Yes | No | Pseudonymous operational zone, not a household address. |
| flow_baseline_lps | number, L/s | Yes | Yes | Reference flow; must be greater than zero to score. |
| flow_observed_lps | number, L/s | Yes | Yes | Observed flow in same context; must be non-negative. |
| pressure_baseline_bar | number, bar | Yes | Yes | Reference pressure; must be greater than zero to score. |
| pressure_observed_bar | number, bar | Yes | Yes | Observed pressure; must be non-negative. |
| duration_hours | number, hours | Yes | Yes | Current signal duration; must be non-negative. |
| repeat_count_30d | integer, events | Yes | Yes | Prior candidate events in zone in preceding 30 days; non-negative. |
| nearby_reports_7d | integer, reports | Yes | Yes | Corroborating reports in same approved coarse zone in preceding 7 days; non-negative. |
| criticality_index | integer, 1-5 | Yes | Yes | Partner-defined asset/service criticality; agree scale with data owner. |

All headers are required, but feature cells may be blank. Missing or invalid features are omitted and lower coverage. Review duplicate candidate IDs before interpreting exports.

## Derived features and score
Each component is clipped to 0-100. Weights sum to 100%.

| Component | Weight | Formula |
|---|---:|---|
| Flow anomaly | 18% | 100 * clip((observed / baseline - 1) / 1.0, 0, 1) |
| Pressure drop | 12% | 100 * clip(((baseline - observed) / baseline) / 0.35, 0, 1) |
| Persistence | 25% | 100 * clip(duration_hours / 24, 0, 1) |
| Repeat events | 15% | 100 * clip(repeat_count_30d / 5, 0, 1) |
| Nearby reports | 15% | 100 * clip(nearby_reports_7d / 3, 0, 1) |
| Asset criticality | 15% | 100 * criticality_index / 5 |

clip(x, 0, 1) limits x to the 0 through 1 range. The flow increase, pressure decrease, and caps are demonstration scales, not engineering standards. Validate or replace them with WASAC-approved definitions.

For each row, priority score is the weighted average of valid component scores, divided by the sum of weights for valid components. If no component is valid, score is blank and the row is unranked.

Input coverage percent is 100 times the sum of weights for valid components divided by 100. Coverage shows how much weighted input is available. It is not statistical confidence or probability. Low-coverage cases need human review.

Initial bands: High >= 70; Review >= 40 and < 70; Routine < 40. Confirm thresholds using reviewed examples before operational use.

## Reason codes
Generate concise reasons from valid component values: Flow anomaly elevated; Pressure drop observed; Signal persisted; Repeat events in zone; Nearby reports present; High asset criticality; or Insufficient valid input for meaningful ranking. Reasons explain signals; they do not diagnose a cause.

## Validation and missing data
- Parse numeric cells as numbers; never convert invalid text to zero.
- Baseline flow and pressure must be greater than zero.
- Observed flow and pressure, durations, and counts cannot be negative.
- Counts and criticality must be integers; criticality is from 1 to 5.
- Omit missing/invalid components and lower input coverage.
- Do not impute operational readings in the MVP.
- Normalize timestamps to a documented timezone before time-window calculations.
- Report duplicate IDs and invalid values so source data can be corrected.

## Privacy
Use synthetic data by default. Use pseudonymous zone and candidate IDs. Do not collect direct identifiers or precise household locations. The MVP does not write uploads to a database; review status is session-only. For an approved study, document source, owner, purpose, authorized users, storage, retention, and deletion.