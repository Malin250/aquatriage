# Data Specification: Erosion-Site Observations

## Purpose and limits

One row represents an observed site for preliminary human review. Inputs are observations, not proof of cause. The schema and screening scales are prototypes; they are not an engineering survey specification or validated hazard methodology. Use the template to identify missing required headers.

## CSV contract

UTF-8 CSV with case-sensitive headers. All headers below are required; measurement/indicator cells may be blank. Invalid measurements become missing, never zero. Extra columns are discarded before scoring and export.

| Field | Type / unit | Meaning and validation |
|---|---|---|
| `site_id` | string | Unique pseudonymous observation ID; not a household or person identifier. Blank IDs get a temporary session ID and warning. Duplicate IDs are warned. |
| `assessed_at` | ISO datetime | Observation time. Naive timestamps are treated as UTC and converted to Africa/Kigali for display. |
| `district` | string | Coarse, approved area label; blank becomes `Unknown`. Do not enter a street address. |
| `site_type` | string | Site context, such as a roadside drain, hillside, stream bank, cultivated land, or construction area. |
| `slope_percent` | number, percent | Measured slope percent, 0–100. Leave blank when not measured. No measurement method is prescribed here. |
| `bare_soil_percent` | number, percent | Estimated bare-soil coverage, 0–100. Leave blank when not assessed. |
| `drainage_concern_0_5` | integer, 0–5 | Assessor-entered ordinal concern observation. |
| `erosion_evidence_0_5` | integer, 0–5 | Assessor-entered ordinal visible-erosion observation. |
| `runoff_concentration_0_5` | integer, 0–5 | Assessor-entered ordinal runoff-concentration observation. |
| `exposed_asset_0_5` | integer, 0–5 | Assessor-entered ordinal concern for people, assets, or receiving areas exposed. This is not a consequence or vulnerability assessment. |

For the ordinal fields, `0` means “none observed”; `1`–`5` indicate increasing concern according to an assessor-entered, **unvalidated** local scale. Use the same locally agreed rubric across assessors. If a factor was not checked, leave it blank—do not use zero. This app does not define the individual levels as an engineering standard.

Blank `district` and `site_type` become display placeholders. Numeric parse errors and values outside the specified ranges become missing and are reported. Counts of invalid values are cell-level, not row-level. The app does not geocode or enrich the data.

## Provisional screening calculation

Components are scaled to 0–100 and combined as a weighted mean over available values. All choices below are **unvalidated demo assumptions**, not technical standards:

| Component | Weight | Prototype scale |
|---|---:|---|
| Visible erosion evidence | 30% | ordinal rating / 5 × 100 |
| Drainage concern | 20% | ordinal rating / 5 × 100 |
| Concentrated runoff | 20% | ordinal rating / 5 × 100 |
| Exposed people, assets, or receiving areas | 15% | ordinal rating / 5 × 100 |
| Bare soil | 10% | entered percent |
| Slope | 5% | entered percent / 30 × 100, capped at 100 |

Missing components are omitted and the remaining weights renormalized. Coverage is the sum of original weights with valid observations. It is not confidence; two sites with different coverage may not be comparable.

Display bands are `Higher review priority` (score ≥70), `Review` (≥40), `Routine review` (<40), or `Unranked` (no valid indicator). These labels do not imply safety, hazard severity, failure probability, urgency, or a treatment. Validate the features, field rubric, slope reference, weights, bands, and missing-data behavior with local specialists and reviewed outcomes before operational use.

## Privacy and retention

Do not include names, account IDs, phone numbers, exact household locations, credentials, or raw personal reports. Use owner-approved pseudonymous IDs and coarse areas only. The prototype holds observations and statuses in Streamlit session memory, not a database. A hosted deployment transmits uploads to its server; assess hosting access, logs, retention, and deletion before entering non-public data. Never commit real exports.
