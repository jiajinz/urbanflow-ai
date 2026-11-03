# Milestone 4C.1B — Verification Record

Chicago Transit Authority (CTA) anomaly validation research; phase-only execution
record. Existing 4C.1A reports, outputs, detector, and historical definitions were
preserved. README and approved dashboards were not edited.

## Tests actually executed

- Initial targeted diagnostics tests: 9 passed.
- Final complete suite after adding prior-only calibration reconstruction and
  invalid-budget coverage: **230 passed, 0 failed, 0 skipped**, 12.34 seconds.
  This includes 11 new validation tests and existing detector leakage tests.
- Command: `TEST_DATABASE_URL=postgresql:///urbanflow_ai_test python -m pytest -q --tb=short`
- PostgreSQL integration tests use the configured local test database. No live CTA
  API request or external incident search was performed.

New tests cover half-open date boundaries, invalid windows, same-direction
calendar runs, missing/non-alert date gaps, cross-mode grouping, empty episode
sets, episode intersections across temporal boundaries, threshold/gate equality,
zero-alert periods, partial years, overlap identities, deterministic ranking,
retention of unranked observations, invalid budgets, duplicate/cutoff/flag guards,
future-suffix independence, and reconstruction of actual prior-only calibration.
Synthetic grouping/boundary fixtures are engineering tests, not actual incidents.

## Artifact verification actually executed

- Repeated diagnostics to `/tmp/urbanflow-4c1b-reproduced`; all 11 CSVs and manifest
  were byte-identical to `data/anomaly/cta-4c1b-v1`.
- Replayed the unchanged 4C.1A detector on the validated archive; every frozen
  prediction matched with numeric tolerance 1e-12 (serialization rounding).
- Source counts/day types, residual arithmetic, score arithmetic, candidate flags,
  strict prior fit cutoffs, and archive/detector hashes were checked.
- Protected original snapshots, SQL, analytics, chart renderers, and style files
  matched their stored hashes. Approved dashboard code and README were not edited.
- The deterministic report and self-contained Plotly evidence were generated from
  the final CSVs. No browser rendering or accessibility QA is claimed.

These checks establish reproducibility and software behavior, not incident
precision, recall, causal validity, reviewer usefulness, or production readiness.
All reported historical assessment dates had already been exposed in 4C.1A.
No threshold was promoted using the retrospective last-period results.

## Practical exercise

Open `data/anomaly/cta-4c1b-v1/annual.csv` and find calendar_median / bus / 2021.
Compare WAPE, alerts, magnitude_without_alert, median_center, median_scale, and
center_suppressed. Then inspect rail on 2021-06-04 in `daily.csv`. Calculate
`(log_residual - center) / scale` and explain why a positive score can accompany
negative raw deviation. Finally compare threshold 3.5 and 4.5 episode counts in
`threshold_episodes.csv`; explain why fewer raw alerts alone cannot identify a
better detector or guarantee preservation of important episodes.
