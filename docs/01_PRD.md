# Product Requirements: AquaTriage

## Product purpose

AquaTriage is a local Streamlit prototype for capturing, screening, and organizing erosion-site observations for human follow-up. It provides a small field register, CSV import/export, data-quality feedback, and a transparent but **unvalidated** screening score.

The project does not establish erosion causation, slope stability, likelihood of failure, safety, treatment selection, or field efficacy. It is not an emergency system and has no live GIS, rainfall, monitoring, agency, dispatch, or contractor integration.

## Intended users

- Field observer: records pseudonymous site details and what was observed.
- Reviewer or supervisor: checks data quality, compares indicators, plans human follow-up, and exports a worklist.
- Qualified local professional: validates site conditions, risks, and any site-specific interventions.

## Core flow

1. Start a session-only field register, choose fictional sample records, or upload an anonymized CSV.
2. Record a site observation with a pseudonymous ID and coarse approved area; unassessed fields remain blank.
3. Review the preliminary queue, reason indicators, and missing-data coverage.
4. Filter the queue, update a temporary human review status, and export the filtered observations.

## Functional requirements

- Clearly separate fictional sample data from user-provided data.
- Support a downloadable CSV template and reject uploads that do not contain the full required header set.
- Normalize inputs and exclude invalid measurements rather than silently converting them to zero.
- Make duplicate site IDs, invalid cells, discarded columns, and missing inputs visible.
- Rank only on available indicators and report the fraction of scoring weight represented.
- Keep review status in the current Streamlit session; do not persist uploads to a database.
- Export only the declared observation and scoring fields; unknown source columns are discarded.
- Provide search and filters for area, site type, queue band, and review status.
- Preserve a no-data state that directs the user to add an observation, upload a template, or open the demo.

## Provisional scoring assumptions

Indicator weights, scaling, and display bands are project assumptions documented in [02_DATA_SPEC.md](02_DATA_SPEC.md). Missing input weights are renormalized for a score, so scores from records with different coverage may not be comparable. Neither the score nor its band is a hazard class, probability, engineering threshold, or validated prioritization method.

## Safety and data governance

- Never enter names, precise household addresses, contact details, account identifiers, or sensitive personal reports.
- Use only fields approved by the relevant land/data owner.
- This tool does not determine emergency response. Immediate danger must be handled through local emergency and safeguarding procedures without waiting for app output.
- Do not infer a site-specific erosion-control treatment from a score. A competent local erosion-control or geotechnical professional must assess causes, site context, downstream exposure, permits, and treatment suitability.
- Local runs keep upload contents and workflow status in app-session memory. A hosted deployment sends data to its host; hosting access, logs, retention, and deletion must be reviewed before use.

## Field validation required before deployment

Obtain owner authorization; define a local observation rubric with trained users; assess accessibility, safe field use, privacy, and consent; review scores and misses against independent local expert assessment and follow-up outcomes; measure error patterns and ranking stability; agree a qualified operational owner, escalation procedures, retention rules, and field-study protocol. The current repository provides none of that evidence and is not production-ready.
