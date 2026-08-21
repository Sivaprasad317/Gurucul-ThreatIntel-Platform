# Data quality policy

## Required behavior

- Do not fabricate country.
- Do not fabricate industry.
- Do not count null country/industry values as a country/industry.
- Do not mix global values into actor-scoped values.
- Do not calculate dashboard totals in React.
- Preserve provenance for enrichment.

## Coverage

Coverage is:

`known values / total actor victims * 100`

A dashboard can therefore say:

`Countries: 17 — 74.1% coverage`

instead of implying every victim has a verified country.

## Evidence

Each enrichment can be stored with:
- source
- confidence
- evidence URL
