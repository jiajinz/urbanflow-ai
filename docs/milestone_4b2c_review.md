# Milestone 4B.2C Review

This document covers Chicago Transit Authority (CTA) ridership data and analysis.

## Scope

Only Research & Methodology presentation changed. The approved Overview and
Explorer function bodies, SQL, research calculations, schema, and validated
snapshots are unchanged. No deployment, commit, AI integration, or 4B.3 work.

## Implementation and execution

`app_pages/methodology.py` calls `dashboard_ui.research_methodology()`.
`dataset()` loads the explicitly selected validated backend. The page passes its
metadata to `methodology.provenance_labels()`, a pure formatting function returning
coverage, counts, provenance timestamps, and explicit `Not recorded` labels.
It never derives original source counts from stored PostgreSQL rows. Failed data
loads retain the existing actionable error and stop behavior without fallback.

Five semantic sections separate provenance, quality, definitions, limitations,
and reproduction. `methodology.METRICS` documents existing functions rather than
calculating replacements. Technical explanations use native expanders. Styling
is scoped to the Methodology container; global theme and approved pages are intact.
Coverage and provenance are dynamic; the July 2012 example and statistical methods
are explicitly archived 4A documentation, not newly inferred backend results.

## Evidence and interpretation

The current bundle has 9,343 validated dates from 2001-01-01 through 2026-08-31.
The source archive contains 9,374 rows. All 31 rejected timestamps belong to
July 2012 and contain 07:00 rather than an accepted midnight timestamp.
Tests reprocess their raw records with the real validator. Counts reconcile in
the displayed example but do not override strict date validation. No cause for
the source timestamps is established. Raw evidence is preserved in
`data/history/cta-2026-11-01-v1/quarantine.json`.

Rejected rows, preserved quarantine records, and missing validated calendar dates
are distinct. July 2012 and annual 2012 lack completeness; July 2013 monthly YoY
and annual 2013 YoY lack a complete previous period. Other complete months remain
usable. The page distinguishes raw mode shares from fixed-calendar composition,
annual research totals from Explorer daily means, and equally weighted monthly
recovery indices from ratios of annual totals.

## Verification actually executed

- Full suite with `TEST_DATABASE_URL=postgresql:///urbanflow_ai_test`:
  **206 passed, 0 failed, 0 skipped**.
- Offline research CLI reproduced nine CSVs byte-for-byte against 4A.
- Offline dashboard export CLI reproduced six analytical tables equal to the
  current validated bundle, then successfully loaded the new bundle.
- AST comparison verified `dataset`, `header`, `executive_overview`, and
  `ridership_explorer` remained unchanged from the pre-phase copy.
- No live CTA request or new historical ingestion was performed in this phase.
  Online ingestion remains documented from the previously validated workflow.
- Initial development checks exposed a generated string syntax error and a test
  using the wrong ProcessingResult attribute; both were corrected before the
  successful full run.

Verified reproduction commands, from an installed checkout (use new output paths):

```sh
python -m urbanflow_ai.research --snapshot data/history/cta-2026-11-01-v1 --output /tmp/urbanflow-4b2c-research-verified
python -m urbanflow_ai.dashboard_data export --archive data/history/cta-2026-11-01-v1 --output /tmp/urbanflow-4b2c-dashboard-verified
TEST_DATABASE_URL=postgresql:///urbanflow_ai_test python -m pytest -q
python -m streamlit run streamlit_app.py --server.port 8512
```

## Review and unresolved methodology

Review the source cards and UTC timestamps, expand the July 2012 case, examine
both baseline definitions, and verify the separation of confirmed limitations,
assumptions, and hypotheses. Check native expander keyboard behavior, zoom, narrow
screens, and download controls. Automated rendering is not proof of accessibility.

Unresolved: timestamp cause, outlier-exclusion sensitivity, individual holiday
alignment, measurement-error estimation, service supply, and causal explanations.
The repository link identifies the existing project; uncommitted local work is
not asserted to have been published there. Snapshot generation is not source
publication. Scope stops at 4B.2C.

Final offline suite: **195 passed, 0 failed, 11 skipped** (PostgreSQL integration
checks intentionally skipped without TEST_DATABASE_URL). A desktop browser
review at 1280 × 720 verified the three source cards, five semantic sections,
provenance labels, and expanding July 2012 evidence. The saved screenshot is
`/tmp/urbanflow-methodology-review.png`; it is a local review artifact, not a
committed portfolio asset. Mobile, screen-reader, and comprehensive keyboard
accessibility audits were not performed.

Final `git status --short`, `git diff --stat`, and `git diff --check` were executed.
The whitespace check was clean. The working tree includes earlier uncommitted
milestones; tracked diff statistics do not include the many untracked new files.
