# Version notes — what this skill is pinned to

**Apache Fineract 1.14.0** (released 2025; imported source tag `1.14.0`). The bundled OpenAPI spec
(`api/fineract-1.14.0.openapi.json`) was captured live from a 1.14.0 build: **563 paths ·
879 operations · 1,476 schemas · 151 tags**. The legacy narrative doc (`api/apiLive-1.14.0.htm`) is
the file shipped inside that release.

## Notable capabilities present in 1.14.0 (vs. older Fineract many tutorials describe)

- **Progressive loans** (`loanScheduleType: PROGRESSIVE`) + **advanced payment allocation**
  strategy with configurable allocation ordering — plus the family of features that only work on
  progressive loans: interest pause, re-age / re-amortize, capitalized income, buy-down fees,
  contract termination, approved-amount modification, backdated interest-rate changes,
  down-payments, interest recalculation refinements.
- **External-ID-first API surface**: parallel `.../external-id/{externalId}` URL variants across
  loans/savings/clients/transactions.
- **Loan COB** as a partitioned Spring Batch job with configurable business steps, loan account
  locking, catch-up + inline COB APIs.
- **Business date / COB date** management endpoints.
- **Reliable external events** (Avro, outbox) with per-type configuration API.
- **Idempotency keys** on writes + batch items (`Idempotency-Key` header).
- **Charge-off** (incl. fraud flag), goodwill credit, merchant/payout refunds, chargebacks,
  interest payment waiver as first-class loan transaction commands.
- **Delinquency buckets/ranges** + delinquency pause actions; loan points-in-time API.
- **External asset owners** (`fineract-investor`): selling/transferring loans to investors,
  transfer journal entries, product attributes.
- **Interoperation APIs** (`Inter Operation` tag, `/v1/interoperation/*`): Mojaloop-style
  parties/quotes/transfers surface.
- **ClientSearchV2** (`POST /v2/clients/search`) — one of the few v2 endpoints.
- **Two-factor** endpoints in-core; OAuth2 resource-server mode; springdoc serving the
  pre-generated spec at `/fineract-provider/fineract.json`.
- Legacy self-service API intact under `/v1/self/*`.

## Known changes vs. older versions to not trip on

- `POST /v1/authentication` takes **JSON body** credentials (older docs show
  `?username=&password=` query params — removed by FINERACT-726).
- Transaction processing strategy is referenced by **code string**
  (`transactionProcessingStrategyCode`, e.g. `mifos-standard-strategy`), not the old numeric
  `transactionProcessingStrategyId`.
- Dev-stack images run Java 21; Gradle builds need Java 21.
- Swagger UI lives at `/fineract-provider/swagger-ui/index.html`; the live springdoc scan
  (`/fineract-provider/api-docs`) is **empty by design** (JAX-RS resources) — use
  `/fineract-provider/fineract.json`.

## Re-pinning this skill to another Fineract version

1. Run the target version; download `https://<host>:8443/fineract-provider/fineract.json` →
   `api/fineract-<ver>.openapi.json`.
2. Copy its `fineract-provider/src/main/resources/static/legacy-docs/apiLive.htm` →
   `api/apiLive-<ver>.htm`.
3. Update `SPEC_FILE`/`LEGACY_FILE` names in `scripts/api_lookup.py`, the counts in `SKILL.md`,
   and this file.
4. Skim upstream release notes for behaviour changes and amend the domain guides.
