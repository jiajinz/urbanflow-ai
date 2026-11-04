# Data Source and Public-Release Basis

Chicago Transit Authority (CTA) publishes systemwide daily boarding totals through
[the Chicago Data Portal](https://data.cityofchicago.org/Transportation/CTA-Ridership-Daily-Boarding-Totals/6iiy-9s97),
resource `6iiy-9s97`. Data provided by Chicago Transit Authority. UrbanFlow AI is an
independent research project without agency affiliation or endorsement.

## Provenance and measurement

The preserved November 1, 2026 retrieval contains 9,374 source dates from January 1,
2001 through August 31, 2026. Existing validation excludes 31 July 2012 records
with non-midnight timestamps, leaving 9,343 validated daily records. Quarantine
and source bytes remain unchanged. Boardings are aggregate rides, not identified
people. No route, station, trip, location history or rider identifiers are present.
Snapshot generation, source retrieval and agency publication are different dates;
unknown publication or research-generation times remain unknown.

Parquet snapshots and retrospective research outputs derive from those public
aggregates. Their manifests record source/code lineage and hashes. Candidate
labels are model-relative statistical leads, not confirmed incidents or evidence
of an external cause. The research page is read-only and operational NO-GO.

## Terms reviewed for this preflight

On November 3, 2026, official dataset metadata identified the publisher as CTA and
the license as “See Terms of Use,” without a separate unrestricted license grant.
The official portal-hosted [CTA data agreement](https://data.cityofchicago.org/api/assets/F1D239A9-B082-4C11-9F6F-2E637985FA5C)
permits conditional use, reproduction and distribution for rider assistance or
promotion of public transportation. It restricts implied agency endorsement,
standalone data sales and transfers, and calls for reasonable efforts to keep
cached data current. CTA retains data rights and disclaims accuracy/availability
warranties. Attribution does not itself establish compliance with every condition.

The metadata did not supply a dataset-specific terms URL, so the exact applicability
of that broader agreement also remains a release-review question.
The project presents historical demand research and planning discussion. Whether
its portfolio-first purpose and fixed historical archives satisfy those conditions
requires an explicit owner review or clarification from the publisher before the
first public application release. This preflight does not substitute public
readability for unrestricted redistribution permission. No agreement was accepted,
no rights were relicensed, and no frozen data was edited to resolve this question.

The terms URL returned a Windows-1252 HTML document, not a PDF. It was read as text;
no claim of PDF rendering or signed agreement review is made. The raw response is
not added to the repository. Its checksum and selected metadata are recorded in
the release evidence. Terms can change; revisit the official source before release.
