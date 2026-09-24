# Errors & Troubleshooting (Fineract 1.14.0)

Error envelope recap (`api-conventions.md`): top-level `userMessageGlobalisationCode` + per-field
`errors[]` with `parameterName`. The globalisation code is the stable machine key.

## Decode by HTTP status

| Status | Typical meaning | First moves |
|---|---|---|
| 400 | Validation (`validation.msg.*`), bad tenant, malformed JSON, missing `dateFormat`/`locale` | Read `errors[].parameterName`; check date boilerplate; check tenant header |
| 401 | Bad/missing credentials; expired OAuth token; missing TFA token when 2FA on | Verify Basic header/user active; 2FA → `Fineract-Platform-TFA-Token` |
| 403 | Missing permission (`error.msg.not.authorized...` naming the code) OR a domain rule (platform `error.msg.*` DomainRuleException) | Grant the named `ACTION_ENTITY`; if domain rule, the message states the business constraint |
| 404 | Wrong id/externalId/URL (`error.msg.<entity>.id.invalid`) | `api_lookup.py` the path — don't guess URLs |
| 409 | Idempotent replay in-flight; optimistic lock; loan COB lock (`LoanIsLocked`) | Retry later; for COB locks see `domains/batch-cob-jobs.md` |
| 415 | Missing `Content-Type: application/json` (or multipart where required) | Set the header |
| 500 | Unhandled — real bug or infra | Server logs + `/v1/jobs/.../runhistory` if job-related |

## Frequent error codes → fixes

| Code (pattern) | Fix |
|---|---|
| `error.msg.tenant.identifier.invalid` / "Invalid tenant identifier" | Header `Fineract-Platform-TenantId` missing/typo; tenant not in registry |
| `validation.msg.validation.errors.exist` | Umbrella — the real details are in `errors[]` |
| `validation.msg.*.<field>.cannot.be.blank` | Send the field — check command-specific mandatory fields (`--op` description) |
| `validation.msg.invalid.date.format` / locale errors | `dateFormat` must match every date string; include `locale` |
| `validation.msg.*.in.min.max.range` | Product min/max constraint (principal, rate, term) |
| `error.msg.loan.approval.date.before.submittal.date` (family) | Chronology rules: submitted ≤ approved ≤ disbursed; watch business date |
| `error.msg.savings.account.insufficient.balance` | Balance/min-balance/hold constraint |
| `error.msg.savings.account.transaction.dates...` / backdating rejections | Global config allows backdating? After interest posting? |
| `error.msg.loan.written.off...` / wrong-state errors | Action invalid for current status — check the state machine in the domain guide |
| `error.msg.clients.duplicate.mobileNo` / `externalId` duplicates | Unique per tenant — look up the existing record |
| `error.msg.current.date.before.holiday` / holiday-related | Holiday/working-day rules affect the date used |
| `error.msg.glaccount.glcode.duplicate` / header-posting errors | GL codes unique; post only to DETAIL accounts, after latest closure |
| `error.msg.office.id.invalid` on visible data | Office-hierarchy scoping — user's office can't see that branch |
| `LoanIsLocked` / `error.msg.loan.locked` | COB owns the loan right now — retry or inline-COB |
| `error.msg.user.password...` | Password policy (`/v1/passwordpreferences`) |
| `Invalid master password` (startup log) | Registry `schema_password`/hash vs runtime master password mismatch (`admin/tenancy-provisioning.md`) |

## Situational recipes

- **"It worked in Postman, fails in code"** → 90%: missing tenant header, missing
  `Content-Type`, or date boilerplate. Diff the raw requests.
- **Write returned 200 but nothing changed** → maker-checker queued it: response has `commandId`,
  no `resourceId`. Approve via `/v1/makercheckers`.
- **Duplicate transactions after retries** → client retried without `Idempotency-Key`. Undo one
  (`?command=undo`) and add keys.
- **Numbers off by rounding** → product `digitsAfterDecimal`/`inMultiplesOf` + tenant rounding mode
  (`FINERACT_CONFIG_ROUNDING_MODE`, default 6=HALF_EVEN).
- **Interest didn't post** → posting job not run yet (scheduler stopped? instance not
  batch-enabled?) — `/v1/jobs` runhistory.
- **Schedule dates look shifted** → holidays/working-days rescheduling rules or
  `interestChargedFromDate` config.
- **Search can't find a new client** → office scoping of the caller, or paged defaults (limit) —
  raise `limit`, check `officeId` filter.
- **405 on a POST** → command endpoints need `?command=`; base POST may not exist for that URL.
- **Big lists slow/timeout** → always paginate; avoid `associations=all` in loops; prefer
  external-id direct lookups.

## When the message isn't enough

1. `api_lookup.py --op` the endpoint — mandatory fields per command are in the description.
2. `api_lookup.py --legacy <resource>` — narrative field semantics.
3. `/v1/audits?actionName=&entityName=` — see the exact stored command JSON that failed vs
   succeeded before.
4. Source: grep the globalisation code (see `architecture.md` "where to look").
