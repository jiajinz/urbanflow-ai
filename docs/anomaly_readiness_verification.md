# Milestone 4C.1C — Verification and Reproduction Record

Chicago Transit Authority (CTA) investigation readiness research. No production
integration, prospective observation acquisition, external incident research,
reviewer-adjudicated case decisions, deployment, commit, or push was performed.

## Actually executed

- Targeted final tests: `python -m pytest tests/test_anomaly_readiness.py -q --tb=short`
  returned **11 passed**, 2.72 seconds. Initial development exposed an empty-frame
  episode-ID assignment error; it was fixed before the successful targeted/full runs.
- Full available suite with local PostgreSQL integration:
  `TEST_DATABASE_URL=postgresql:///urbanflow_ai_test python -m pytest -q --tb=short`
  returned **241 passed, 0 failed, 0 skipped**, 14.70 seconds.
- Existing tests still establish past-only detector/calibration behavior and
  historical analytics consistency. The new tests verify candidate preservation,
  stable IDs, score-sign versus actual-direction separation, source context,
  episode membership, explicit missing observations/cross-mode evidence, trailing
  health arithmetic, disjoint drift windows, data-availability states, priority
  components, capacity overflow retention, empty data, and overwrite prevention.
- A future-suffix invariance test truncates all post-2021-06-30 evidence and
  rebuilds cases and health. Earlier records are unchanged, including episode
  age, stable IDs, daily priority rank, and health flags. Full final episode
  durations are retrospective registry metadata and are excluded from this test's
  as-of case fields and ranking inputs.

## Artifact audit

The first final export was written to `data/anomaly/cta-4c1c-v1`. An independent
CLI run to `/tmp/urbanflow-4c1c-reproduced` produced byte-identical cases,
model_health, episode_registry, weekly_load CSVs and manifest.

All 763 frozen candidate observations were retained, with no duplicate case ID.
The 200 episode registry rows exactly match frozen 4C.1B episode fields. Every
case's current count/day type/reconciled total matched the validated archive.
All existing protected data, source Python, SQL, reports, README and theme files
matched their pre-phase SHA-256 hashes. No existing 4C.1A/1B output was rewritten.
Only new phase-specific modules, tests, documents and output files were added.

`data/anomaly/cta-4c1c-v1/verification.json` records these checks. The prospective
configuration and protocol, detector, input diagnostics and new core module are
hashed in the manifest. The report and self-contained Plotly diagnostics were
regenerated from the final CSVs. No browser or accessibility QA is claimed.

## Interpretation and practical exercise

Tests prove deterministic software behavior, not operational utility or incident
precision/recall. Every exported case remains unreviewed. The initial health rules
and staffing assumptions are proposed gates, not empirically approved limits.

Open `cases.csv` for calendar_median / rail / 2021-06-04. Compare
`actual_direction`, `centered_score_sign`, `model_health_status`, and the dated
prior observations. Explain why a positive score cannot label this high ridership.
Then open `weekly_load.csv` for the maximum-arrival week: calculate how many
candidate records exceed the ten-review staffing assumption, explain why they
must remain in the queue, and propose an escalation without lowering detection
thresholds or declaring episodes confirmed incidents.
