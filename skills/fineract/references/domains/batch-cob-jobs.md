# Batch API, Scheduler Jobs, Loan COB, Business Dates (Fineract 1.14.0)

Tags: `Batch API`, `SCHEDULER JOB`, `Scheduler`, `Inline Job`, `Internal COB`, `Loan COB Catch Up`,
`Business Date Management`, `Business Step Configuration`, `External event configuration`,
`Instance Mode`.

## Batch API (client-side batching)

`POST /v1/batches?enclosingTransaction=true|false` — array of batch items:

```json
[{"requestId": 1, "relativeUrl": "clients", "method": "POST",
  "headers": [{"name": "Idempotency-Key", "value": "k1"}], "body": "{...json string...}"},
 {"requestId": 2, "relativeUrl": "loans", "method": "POST", "reference": 1,
  "body": "{\"clientId\": \"$.clientId\", ...}"}]
```

- `reference` + `$.field` chain dependent requests (value plucked from the referenced response).
- `enclosingTransaction=true` = single DB transaction, all-or-nothing; item responses come back in
  one array `{requestId, statusCode, headers, body}`.
- Bodies are JSON **strings**. Relative URLs omit `/api/v1/`.

## Scheduler jobs (server-side periodic work)

`/v1/jobs` (tag SCHEDULER JOB):
- `GET /v1/jobs` — all jobs with cron, last run status, currently-running flag. Well-known names:
  `Loan COB` (the big one), `Post Interest For Savings`, `Transfer Interest To Savings`,
  `Add Periodic Accrual Transactions`, `Recalculate Interest For Loans`, `Apply penalty to overdue
  loans`, `Update Loan Arrears Ageing`, `Update Non Performing Assets`, `Execute Standing
  Instruction`, `Apply Holidays To Loans`, `Pay Due Savings Charges`, `Post Dividends For Shares`,
  `Update Deposit Accounts Maturity details`, `Generate Mandatory Savings Schedule`,
  `Execute Report Mailing Jobs`, `Purge External Events`, `Purge Processed Commands`...
- `PUT /v1/jobs/{jobId}` — change `cronExpression`/`active`.
- `POST /v1/jobs/{jobId}?command=executeJob` — run now (async; poll run history).
- `GET /v1/jobs/{jobId}/runhistory` — outcomes + stack traces of failures.
- Global pause/resume of the scheduler: `POST /v1/scheduler?command=stop|start`,
  `GET /v1/scheduler` status (tag Scheduler).
- **Inline job** (`/v1/jobs/{jobName}/inline`): run a job synchronously for specific entities —
  notably `POST /v1/jobs/LOAN_COB/inline` `{loanIds: [...]}` to COB specific loans immediately.

## Loan COB (Close of Business) — nightly loan processing

Spring-Batch-based partitioned job that advances every active loan one business day at a time:
applies penalties, accruals, delinquency tagging, maturity processing via configurable **business
steps**.

- Steps admin (tag Business Step Configuration): `GET /v1/jobs/{jobName}/steps` — for `LOAN_CLOSE_OF_BUSINESS`
  lists ordered steps (e.g. APPLY_CHARGE_TO_OVERDUE_LOANS, LOAN_DELINQUENCY_CLASSIFICATION,
  CHECK_LOAN_REPAYMENT_DUE, CHECK_LOAN_REPAYMENT_OVERDUE, UPDATE_LOAN_ARREARS_AGING,
  ADD_PERIODIC_ACCRUAL_ENTRIES, EXTERNAL_ASSET_OWNER_TRANSFER...); `PUT` reorders/enables.
- While COB processes a loan it **soft-locks** it (writes → 409 `LoanIsLocked`); inspect
  `GET /v1/loans/locked`. Internal endpoints under `Internal COB` are test/ops-only.
- **Catch-up**: if COB lags behind (downtime), `POST /v1/loans/catch-up` replays days;
  `GET /v1/loans/is-catch-up-running` checks (tag Loan COB Catch Up).
- Scale-out: run dedicated batch-manager + batch-worker instances (below); partitions distribute by
  loan ranges via Spring Batch remote partitioning (queue-backed).

## Business dates

Global config `enable_business_date` = true switches the platform from wall-clock to logical dates:
- `GET/POST /v1/businessdate` — types `BUSINESS_DATE` (current banking day) and `COB_DATE`
  (day being closed, = business date - 1 during COB).
- COB job advances business date; backdated/future-dated writes validate against it.
- With it off (default), "today" = tenant-timezone system date.

## Instance modes (read/write/batch topology)

Env flags (see `admin/operations.md`): `FINERACT_MODE_READ_ENABLED`, `FINERACT_MODE_WRITE_ENABLED`,
`FINERACT_MODE_BATCH_WORKER_ENABLED`, `FINERACT_MODE_BATCH_MANAGER_ENABLED` — all true by default
(single instance). Split for scale: N read instances (read-replica DB, read APIs only), 1 write
(the only Liquibase migrator, receives events), batch manager (schedules/partitions jobs) + batch
workers (execute partitions). `GET /v1/instance-mode` reports the current instance's mode; write
APIs on a read instance return errors by design.

## External/business events

Reliable event framework (see `architecture.md`): enable `FINERACT_EXTERNAL_EVENTS_ENABLED=true` →
domain events (ClientCreated, LoanApproved, LoanDisbursal, journal postings...) are stored in an
outbox table and published (JMS/ActiveMQ, Kafka via config) as Avro payloads.
- `PUT /v1/externalevents/configuration` — enable/disable individual event types
  (`GET` lists all with flags).
- Purge job trims processed events. (Tag External event configuration.)

## Hooks (legacy webhooks)

`/v1/hooks`: template `Web` (fires HTTP POST on configured entity/action events, optional payload
templating) or `Message Gateway`. Simpler than the event framework; per-tenant; no retry
guarantees. Prefer external events for production integrations.

## Gotchas

- `executeJob` returns 202 immediately — check `runhistory` for the outcome; a "running" scheduler
  won't double-start a job.
- COB requires business dates enabled and an initial `COB_DATE`; on fresh dev tenants the Loan COB
  job errors until business date config is set.
- Job cron expressions are Quartz format (6-7 fields), evaluated in tenant timezone.
- Batch API ≠ scheduler jobs ≠ Spring Batch COB — three different "batch" concepts; disambiguate
  before answering.
