# V1 Deployment Preflight and Local Release Validation

Chicago Transit Authority (CTA) historical analytics and experimental anomaly
research. Checked November 3, 2026 (America/New_York).

**Release assessment: NOT READY — BLOCKERS REMAIN.**

The pinned local candidate passes installation, offline four-page smoke checks,
packaging, downloads and full regression. Public release still requires a documented
data-use basis and target Linux execution evidence. These are open release gates,
not claims that a Linux defect or terms violation has been demonstrated.
**Operational Readiness: NO-GO** remains the detector's separate scientific decision.
A public historical research interface must retain that decision and all uncertainty.

No GitHub push, tag, history rewrite, cloud deployment, training, forecasting,
change-point implementation, agent or LLM development occurred.

## 1. Repository and release inventory

Starting branch/HEAD: `main` at `f7d1214a124e99d4c6734a62173839c331eed3e5`.
A read-only `git ls-remote origin refs/heads/main` returned
`5b578583cb3c5e86e0f046c9aea23c03655152eb`; this matched cached `origin/main`.
At that time the checkout was two commits ahead and zero behind. The local
checkpoint created for this preflight adds another commit; its hash is reported
in the completion message. Push authentication was not exercised.

The [inventory](qa/release-v1/inventory.json) verified 42 existing required paths
were tracked: four route files, entrypoint/config/package inputs, the analytical
bundle and research lineage dependencies. Every required research payload returned
by `verified_payloads()` was tracked. The new `constraints.txt`, preflight script,
reports, tests and actual release screenshots are intentional checkpoint additions.
Versioned data files total approximately 13.2 MB; size alone is not a readiness test.

Local-file protection now includes `.agents/`, AGENTS.md, `.env`, `.env.*` with an
explicit `.env.example` exception, IDE settings, virtual environments and caches.
`git check-ignore` confirmed the intended exclusions. No local configuration,
downloaded archive, fresh virtual environment, build wheel or temporary log is staged.
Only curated QA evidence is part of this release checkpoint.

### Git history and private-content review

The historical scan inspected all seven reachable starting commits and 227 unique
blobs, not just the worktree. No private-key block, GitHub token or AWS access-key
pattern was found. Four password-URI matches were deliberate documentation/test
placeholders, confirmed by reading/classifying their values without printing them.
Four email-containing blobs held bundled third-party JavaScript copyright credits.
Ordinary owner author identity/email metadata remains in Git history.

The first ingestion commit `db300ba` contained AGENTS.md and `.idea` settings;
`8bd4e61` removed them and added ignore rules. Those old nonsecret development
instructions/settings remain historically accessible. They are absent from the
current source export. No `.env` or Streamlit secrets history was found. History
was not rewritten. Three blobs contain legacy developer path labels: the B/C
manifests and their compatibility mapping in the research loader. Their presence
is documented, not silently edited or represented as necessary runtime paths.
The relocated installation and portable-root tests demonstrate that the app does
not open the original developer directory.

This was a pattern and targeted content review, not a complete credential/CVE
certification. [Historical scan evidence](qa/release-v1/history_scan.json) stores
paths and hashes, not matched password or personal-email values.

## 2. Fresh installation and packaging

Two isolated environments were used. The first resolved existing broad ranges;
for example it selected psycopg 3.3.7 while the original development environment
held 3.3.6. A second **new** environment installed the final requirements from a
relocated `git archive` source export with reviewed candidate files overlaid.
No global site packages, original `.venv`, AGENTS.md, `.agents/` or `.env` were copied.
An installed-module path assertion confirmed this second environment imported the
relocated source, not the owner's checkout.

Validated host: macOS ARM64, Python **3.11.9**. Cloud configuration should explicitly
select the supported Python 3.11 minor; its managed patch may differ. Official
[Community Cloud status](https://docs.streamlit.io/deploy/streamlit-community-cloud/status)
limits Python to released, security-supported versions. The
[deployment dependency guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies)
describes Linux hosting, requirements-file selection and Python selection.

`requirements.txt` now installs `-e .` under `constraints.txt`. The constraints
pin the existing runtime dependency graph; the package metadata retains compatible
ranges and raises the Streamlit floor to **1.66.1**, the
[latest release checked on PyPI](https://pypi.org/project/streamlit/).
No new application dependency was introduced. The Linux-only watchdog pin is an
existing conditional Streamlit dependency, not a new feature or macOS requirement.
Constraints do not lock the interpreter, isolated build tooling or wheel bytes
across platforms. Upgrade them through a new fresh validation.

Actual clean results:

- `pip install -r requirements.txt`: PASS from the relocated checkout.
- `pip check`: PASS, no broken requirements.
- Local noneditable wheel build: PASS; ZIP inspection found all **eight SQL files**.
  SQL package-data declarations work. Data and route files remain checkout assets;
  the wheel alone is not advertised as a standalone dashboard distribution.
- Streamlit import and all four route executions: PASS via AppTest and browser.
- Snapshot: **9,343 validated dates**; research: **11,200 daily rows, 763 cases and
  11,200 health rows**. Hashes, schemas and lineage passed existing loaders.
- API, PostgreSQL and fitting/calibration entrypoints were patched to fail during
  the offline smoke test. All pages still worked. The actual PostgreSQL service
  was not stopped; separate integration tests used its dedicated test database.
- Runtime pin validation rejects changed or missing packages before a PASS result.

No Docker, Podman or Linux runner was available in this session. Download resolution
found **39 compatible wheels** for CPython 3.11 / Linux x86_64 using manylinux2014
and manylinux_2_28 targets. This is package availability evidence, **not Linux
installation/import/execution proof**. No OS packages were demonstrated necessary.
[Wheel inventory](qa/release-v1/linux_wheels.json),
[project wheel contents](qa/release-v1/wheel.json), and
[fresh preflight output](qa/release-v1/fresh_preflight.json) retain the actual results.

## 3. Four-page local release smoke

The second environment ran the candidate on local port 8516 with the repository
configuration and explicit snapshot backend. Only its network binding/port and
headless option were local test overrides; no database secrets were configured.
`client.showErrorDetails="none"` hides unexpected public stack traces while existing
safe data-access messages remain visible. Cloud may override platform-managed
settings, including telemetry; the local telemetry setting is not a cloud promise.

Actual browser observations:

- **Overview:** navigation and both baseline controls worked; the weekday KPI
  switched 70.90 → 69.18 → 70.90. Reporting through August 31, 2026, source retrieval
  November 1 and snapshot generation November 2 remained visible.
- **Explorer:** date/mode/day-type/baseline filtering worked. Removing both modes
  showed the clear empty state. Selecting January–December 2025, Bus/Rail, W/A,
  2017–2019 reference produced a downloaded **48-row CSV**, exactly equal to the
  active view-model series after CSV round trip.
- **Methodology:** navigation, source/coverage and the July 2012 timestamp example
  were present. The five approved sections remained intact.
- **Research:** default Seasonal Trend/Bus annual window showed 19 candidates and
  one health-warning date; Calendar Median showed 10 and two respectively. The
  June 4, 2021 Calendar Median/Rail case remained below expected at **−65.94%**
  despite centered score **+3.94**. The actual downloaded ZIP passed CRC and all four
  CSVs matched the selected view exactly, with one observation/case/health row,
  provenance hashes and NO-GO. Switching to Above expected produced zero cases,
  retaining the observation, both charts, one health warning and both NO-GO statements.
- **Error isolation:** a separate local service pointed research at an empty
  directory without modifying frozen data. The browser displayed the safe missing-
  artifact message and no research plot; Methodology remained accessible. AppTest
  also checked a missing analytical snapshot and the research-only failure.

The normal browser error log was empty. The server startup log contained no
ERROR/Traceback. Its Watchdog installation suggestion is optional on macOS;
Linux's conditional dependency is pinned. Bare AppTest runs reported missing
ScriptRunContext warnings, and sandboxed PyArrow inspection reported denied hardware
`sysctl` probes; neither caused test failure. The initial metadata request through
Python's default TLS store failed certificate validation; a system-trusted curl
request succeeded. Certificate checks were never disabled. No live ridership
API ingestion or refresh was performed.

Screenshots were captured from this exact isolated candidate at 1280 × 720 after
waiting for stable layout: [Overview](figures/release_overview.jpg) and
[research](figures/release_anomaly_research.jpg). An intermediate capture caught a
sidebar navigation animation and was replaced after checking stable text bounds.
These are local captures, not a public deployment or historical mockup.

CSV and ZIP downloads were actually opened and compared, not inferred from buttons.
Browser-tool operations waited approximately 31 seconds for the CSV and 123 seconds
for the ZIP sequence. Transfer, automation-event and path-save times were not
separately profiled; these waits cannot be attributed to app computation. Repeat
real download timing on the target platform before making responsiveness claims.

## 4. Runtime, caches and resources

Final fresh-process `load_bundle()` took **0.106 s**; research verification/parsing
took **0.482 s** in that run. OS/filesystem caches were not purged. A separate benchmark
measured explicit cold research loading at **0.526 s**, warm verified loading at
**0.018 s median** (five repetitions). First in-process entrypoint execution after
benchmark imports was **0.351 s**. A new server announced its listening URL after
**0.368 s**, excluding first page execution and browser rendering.

Warm in-process page rerun medians were **58.7 / 32.5 / 6.8 / 44.1 ms** for
Overview/Explorer/Methodology/Research. Representative baseline/question/model
changes took **59.4 / 40.6 / 42.6 ms** respectively. These are local AppTest timings,
not public HTTP latencies. The research loader verifies actual bytes before each
cache lookup; analytical data retains its existing bounded five-minute cache.
Neither verification nor health reporting was weakened.

A separate Seasonal Trend/Rail benchmark measured view plus two chart builds at
16.3 ms for 365 dates and 20.8 ms for 2,800 dates. ZIP generation medians were
8.5 ms / 60.2 ms, producing approximately 56 KB / 408 KB archives. These server-side
measurements do not explain the longer browser automation waits.

Pandas deep accounting for research frames was **10,022,258 bytes**. Benchmark
high-water process RSS was **354 MiB**; the separate export benchmark peaked at
255.5 MiB. A point-in-time live-server process-tree sample was **72 MiB**. These
measurements involve different workloads and time scopes; the server sample is
not a peak or a per-user memory budget. No concurrent-session stress test occurred.

The official [resource documentation](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app#resource-limits)
still labels its approximate numbers as February 2024: memory 690 MB–2.7 GB, CPU
0.078–2 cores, storage up to 50 GB. It says allocations may change without notice.
A single-session pilot appears plausible relative to that published range, but
local macOS RSS/CPU timings do not establish a Linux/cloud memory ceiling,
concurrency capacity or cold-start latency. Inspect actual allocation and logs in
the next authorized target-platform validation. File size is only an inventory fact.

## 5. Public data, scientific and README review

[Source notice](data_source_notice.md) records provenance and the unresolved terms
question. Official metadata says “See Terms of Use”; public read access alone is
not sufficient release authorization evidence. Owner review or publisher
clarification of applicability, purpose and historical-cache conditions remains a
**blocking public-release gate**. No claim of a legal violation or clearance is made.

[Protected-file verification](qa/release-v1/protected.json) confirms **71 files
unchanged byte-for-byte**. SQL, validated snapshots, research model outputs,
thresholds, analytical definitions and health results were not altered. All data
is aggregate public transit boardings; no rider identities or individual location
histories were found in the dataset schema. Unknown causes and review status stay
unknown/unreviewed; historical evaluation remains retrospective. Legacy source-root
labels remain traceable but are not opened as arbitrary paths or exposed in normalized
research exports. No CTA logos or affiliation claims were added.

README now documents four implemented pages, the experimental read-only scope,
NO-GO, fixed-version setup, source/limits, current actual screenshots and a clearly
marked pending live URL. Its verified research numbers remain unchanged. The
outdated three-page/separate-from-dashboard wording and screenshot placeholder
were removed. No public URL, release tag or deployment success was invented.
Future AI reporting, forecasting and change-point work remain future work.

## 6. Tests and accessibility boundary

Final fresh-environment full suite, including the dedicated local PostgreSQL
integration tests: **280 passed, 0 failed, 0 skipped in 21.31 seconds**.
The initial fresh run before the two new runtime-pin regressions was 278 passed
in 22.57 seconds. New deterministic tests check marker-aware pin verification and
clear failure for version mismatch/missing packages. Existing tests cover analytics,
exports, gaps, hashes, UI state and the NO-GO decision.

AppTest validates Python execution/state; PostgreSQL tests validate actual local
persistence and SQL parity. Browser smoke verifies rendered interactions/downloads.
No live API test or Linux execution was reported as passing. `pip check` and
`git diff --check` passed. The unchanged protected-file inventory passed again.

Actual 200% browser/text zoom remains **NOT VERIFIED**: the embedded browser
exposes viewport resizing but no page-zoom control; native Chrome control returned
Computer Use permission unavailable. No user action was requested to substitute
for routine verification. No screen-reader session, mobile touch-hardware test,
complete Plotly/grid keyboard audit or accessibility certification occurred. Prior
4B.3B limitations remain; its 20 viewport results are historical evidence, not
newly rerun results for this release. A 1280-pixel smoke capture is not a zoom test.

## 7. Reproduce and close the release gates

From a clean checkout containing the versioned artifacts:

```sh
python3.11 -m venv /tmp/urbanflow-v1-venv
source /tmp/urbanflow-v1-venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -c constraints.txt -e '.[test]'
URBANFLOW_DATA_BACKEND=snapshot python scripts/release_preflight.py
URBANFLOW_DATA_BACKEND=snapshot python scripts/benchmark_dashboard.py
python -m pytest -m 'not integration' -q
# Optional full integration run with a separate disposable PostgreSQL database:
TEST_DATABASE_URL=postgresql:///urbanflow_ai_test python -m pytest -q --tb=short
python -m streamlit run streamlit_app.py --server.port 8516
```

`release_preflight.run()` checks the installed checkout and runtime pins, loads the
existing verified bundles, then exercises four routes with network/database/fitting
entrypoints forbidden. It returns JSON only after checks pass. Its
`validate_runtime_constraints(path, version_lookup)` reads package/version rules,
skips markers for other platforms and raises a clear RuntimeError for mismatches
or missing packages. It catches accidental use of a different development environment.
The same SQL/data loaders and UI view models are reused; no release-only analytics
or frozen artifact regeneration exists.

Hands-on exercise: in a disposable environment, run `python -m pip show psycopg`
and compare with constraints, then call preflight. Explain why passing tests under
3.3.6 cannot substitute for validating a release pinned to 3.3.7. The deterministic
mismatch test demonstrates failure without modifying a working environment.

Exact remaining steps before the first cloud release:

1. Document the owner's data-use basis or obtain publisher clarification for the
   questions in the source notice. Resolve that public-release gate first.
2. Run the pinned requirements, preflight and offline regression on Linux x86_64
   / Python 3.11. Retain results. Linux execution is an open validation gate;
   compatible wheel downloads are not a substitute. For a future available Docker
   runner, export only tracked files rather than mounting local secrets:

   ```sh
   git archive HEAD | docker run --rm -i python:3.11-slim sh -c \
     'mkdir /app && tar -xf - -C /app && cd /app && python -m pip install -r requirements.txt && python -m pip install -c constraints.txt -e ".[test]" && python scripts/release_preflight.py && python -m pytest -m "not integration" -q'
   ```

   This command was prepared but **not executed** in this session.
3. Review this local checkpoint and remaining zoom/screen-reader/download-latency
   limits. After the release gates are closed, reassess readiness. Keep NO-GO.
4. Only after explicit push authorization, push the reviewed `main` checkpoint.
   Verify GitHub contains the exact reviewed commit and all data files.
5. Only after explicit deployment authorization, use Streamlit Community Cloud:
   repository `jiajinz/urbanflow-ai`, branch `main`, entrypoint `streamlit_app.py`,
   advanced Python version **3.11**. Use default snapshot mode; no PostgreSQL/API
   credentials or custom local-root environment variables are needed. Review
   platform settings and actual resource limits rather than assuming local values.
6. Verify all four public routes, source dates, NO-GO/health, empty states, CSV/ZIP
   downloads, cold starts and cloud logs. Populate README's `LIVE_DEMO_URL` location
   only with the actual verified URL. Do not create release tags automatically.

Local implementation/preflight work is complete. The public release assessment
remains **NOT READY — BLOCKERS REMAIN** until the listed gates are closed.
Stop here for owner review; do not push, deploy or start another ML milestone.
