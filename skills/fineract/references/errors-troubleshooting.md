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
| `error.msg.client.not.active.exception` (403) | Client isn't Active. Client-charge add/pay/waive/delete/undo **and every savings write, account creation included**, need an Active client — activate first |
| `validation.msg.CLIENTCHARGE.transaction.invalid.charge.amount.paid.in.access` | Paying **more than the outstanding** on a client charge ("in access" = "in excess"). Re-read `amountOutstanding` and pay at most that |
| `...transaction.invalid.account.charge.is.paid` / `...charge.is.already.waived` / `charge.is.not.active` | The client charge is already settled, waived or inactive — re-read before paying |
| `transaction.not.allowed.transaction.date.is.on.holiday` / `...is.a.non.workingday` (also `charge.due.date.is.on.holiday` / `...a.non.workingday`) | Date falls on a holiday or non-working day. Use a working day, or enable global configs `allow-transactions-on-holiday` / `allow-transactions-on-non-workingday` (e.g. for 24/7 USSD/mobile channels) |
| `transaction.before.activationDate` / `transaction.is.futureDate` / `dueDate.before.activationDate` | Client-charge date before the client's activation, or in the future |
| `error.msg.financialActivityAccount.not.found` | A needed financial activity isn't mapped — e.g. 103 Fund Source for client-charge payments. Map it (`accounting.md`) |
| `error.msg.glJournalEntry.invalid.accounting.closed` | Posting or reversing on/before the office's latest GL closure — reversals use the original date. Adjust in the current period |
| `error.msg.savingsaccount.transaction.withdrawals.blocked.during.lockin.period` | Savings lock-in — **every** withdrawal (transfers out included) is blocked until `lockedInUntilDate` |
| `cannot.be.redeemed.due.to.lockinperiod` | Share lock-in — the only redemption gate |
| `error.msg.clients.transaction.cannot.be.undone` | That client transaction was already reversed |
| `error.msg.client.charge.cannot.be.deleted` | The client charge has payments — waive the remainder instead |
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
- **Client-charge payment succeeded but there is no journal entry** → the charge definition has no
  GL account, so Fineract skipped accounting entirely. Map the charge's income account (and activity
  103), then fix the gap with a current-period entry.
- **Waived fees don't appear anywhere in the GL** → by design: client-charge waivers post nothing. Report
  forgone fees from `amountWaived`.
- **Fee "paid" but `isPaid` is false** → it was waived (`isWaived: true`). Test `amountOutstanding == 0`.
- **A retried batch or API call did nothing the second time** → an `Idempotency-Key` was reused for a
  different resource of the same entity type; the first result was replayed (`api-conventions.md`).
- **Nightly job keeps failing** (e.g. Pay Due Savings Charges) → one account can't cover a due charge;
  the job pays full outstandings only and fails the run. Check `/v1/jobs/{id}/runhistory`.

## When the message isn't enough

1. `api_lookup.py --op` the endpoint — mandatory fields per command are in the description.
2. `api_lookup.py --legacy <resource>` — narrative field semantics.
3. `/v1/audits?actionName=&entityName=` — see the exact stored command JSON that failed vs
   succeeded before.
4. Source: grep the globalisation code (see `architecture.md` "where to look").
