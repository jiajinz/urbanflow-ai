# Milestone 4C.1D.2 Acceptance Gate

Verification date: November 3, 2026. **4C.1D.2 Acceptance Gate: PASS**.
This accepts the historical, read-only interface. **Operational Readiness: NO-GO**
remains unchanged. No prospective evaluation, deployment, or live alerting occurred.

## A1. Model switching — PASS

Expected: selection isolates each frozen model across observations, expectations,
candidates, evidence, health and provenance.

Actual browser: September 1, 2025–August 31, 2026 / Bus / All showed 19 Seasonal
Trend candidates and one health-warning date; Calendar Median showed 10 candidates
and two health-warning dates. Both retained 365 observations. Browser-downloaded
ZIPs were opened and all four CSVs compared exactly with `build_research_view()`
outputs, including model identifiers, values, dates and provenance hashes.

Actual Seasonal Trend / Rail / March 15, 2025 evidence: actual 578,528, expected
270,475.0 (display rounded), deviation +113.89%, centered score +12.38, cause
unknown, review unreviewed and health clear. The NO-GO statement remained present.
Automated coverage: `test_model_switch_exports_and_evidence_never_mix_models`,
`test_primary_bounds_and_independent_candidate_filters` (both models/modes).

## A2. Actual direction versus centered score — PASS

Expected: Calendar Median / Rail / June 4, 2021 remains under Below expected.
Actual browser: one visible candidate; selected evidence showed actual 244,454,
expected 717,811.0, deviation −65.94%, score +3.94 (positive), direction low,
health warning, unreviewed and unknown cause.

Coverage: `test_below_expected_positive_centered_score` and
`test_below_expected_selection_and_export_preparation`. Direction uses the stored
actual-direction field, validated against observed minus expected by the loader.

## A3. Complete trends and empty results — PASS after targeted fix

Actual browser: Seasonal Trend / Rail / full research coverage retained 2,800
observed dates and both trend/health charts when search reduced 161 candidates
to zero. Health counts were unchanged. Candidate filters never select the base
observation or health frames; exact frame equivalence is tested independently.

Found and fixed: line-only traces were invisible for a single observed date,
particularly when no candidate marker remained. Traces now include a point when
only one nonmissing value is available. Browser confirmed two actual/expected
points with zero candidates. No values or filters changed.

Coverage: `test_single_day_empty_candidates_keep_visible_observation_and_expectation`,
`test_null_date_gap_stays_null`, and the four primary-filter parameterizations.
Missing dates remain null and `connectgaps=False`; no zero filling.

## A4. Health, uncertainty and NO-GO — PASS

Actual browser: both exact research/NO-GO statements were present. Model-health
context remained visible for populated and empty selections. Clear research
health did not replace NO-GO. Both inspected cases stated unknown causes and
unreviewed status. The interface explicitly says candidates are not confirmed
incidents. AppTest covers empty-state framing and forbidden training/recalibration,
archive analytics rebuilding and database calls.

Coverage: `test_research_default_framing_and_complete_health`,
`test_page_never_calls_training_recalibration_or_database`, and candidate-flag
independence tests.

## A5. Actual ZIP downloads — PASS

Three archives were downloaded using the real browser download control, opened
with `ZipFile`, CRC-checked and compared with the corresponding pure view frames:

- Seasonal Trend / Bus / September 2025–August 2026: 365 observation rows,
  19 candidates, 365 health rows.
- Calendar Median / Bus / same dates: 365 observations, 10 candidates, 365 health rows.
- Calendar Median / Rail / June 4, 2021 / Above expected: one observation,
  zero candidates with CSV headers preserved, one health row.

For each archive, all four CSVs matched exactly after CSV round trip; case IDs
were unique, selection definitions and `source_sha256` matched, NO-GO was retained,
and `prospective_validation_executed` was false. Local downloaded copies are not
repository deliverables. Automated chart/ZIP membership and empty ZIP regression
coverage also passed.

## Executed checks and boundaries

- Initial full suite inside the restricted sandbox: 261 passed, 3 failed and
  8 setup errors, all 11 failures caused by blocked local PostgreSQL socket access.
- Full suite with authorized local test-database access, before the display fix:
  **272 passed in 21.39 seconds**.
- After the display fix and two additional deterministic regressions:
  `pytest -q tests/test_anomaly_research_views.py tests/test_anomaly_research_ui.py`
  **17 passed in 3.44 seconds**.
- Final full regression results are recorded in the Product QA report.

Browser interaction verified real controls, case details, empty states and real
ZIP downloads. Unit tests establish numerical/frame equivalence; AppTest checks
Python widget/render behavior. These do not establish full accessibility or
production model readiness. A raw SVG path comparison changed after legend/marker
layout updates and was not used as a numerical equality assertion.
