# Gurucul ThreatIntel Platform architecture

## Data flow

```text
Source
  -> actor-specific parser
  -> canonical victim
  -> normalization
  -> enrichment with provenance
  -> PostgreSQL/SQLite
  -> server-side actor-scoped aggregation
  -> React actor dashboard
```

## Country

Country is normalized to ISO alpha-2. A source-provided country is preferred. ccTLD inference is explicitly lower-confidence and is never treated as verified headquarters location.

## Industry

Industry uses a controlled taxonomy. Source-provided activity/industry is preferred. Keyword inference is lower-confidence. Unknown values remain null.

## Dashboard rule

The selected `group_id` is the first predicate in every actor aggregation. The frontend does not compute country/industry totals.

## Collection health

Operational health is separate from intelligence activity. A healthy source does not imply a high threat level, and a high victim count does not imply source health.
