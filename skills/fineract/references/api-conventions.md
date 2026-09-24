# API conventions in depth (Fineract 1.14.0)

Base: `https://<host>:8443/fineract-provider/api/v1` · every call: `Fineract-Platform-TenantId` header
+ Basic auth. This file covers the cross-cutting request/response mechanics; per-domain semantics live
in `domains/`.

## Dates and locale

Any payload containing a date **must** also carry `dateFormat` and `locale`, and every date string
must match that format exactly:

```json
{"approvedOnDate": "24 September 2026", "dateFormat": "dd MMMM yyyy", "locale": "en"}
```

- `dateFormat` uses Java `DateTimeFormatter` patterns (`dd MMMM yyyy`, `yyyy-MM-dd`, …).
- Responses return dates as **integer arrays**: `"approvedOnDate": [2026, 9, 24]` (y, m, d) — date-times
  add `[y,m,d,H,M,S,...]`.
- Month names are locale-sensitive: `"24 September 2026"` needs `"locale": "en"`.
- Some monetary/numeric fields are also locale-parsed; when in doubt include `locale`.

## The command pattern (state machines)

Lifecycle transitions are `POST /<resource>/{id}?command=<verb>` on the *same* URL. The OpenAPI spec
merges all commands of one URL into one operation (e.g. `POST /v1/loans/{loanId}` summary lists
"Approve … | Disburse … | Undo …") — read the operation's `description` (via
`api_lookup.py --op`) to see each command's mandatory fields. The request body's schema is the union
of all commands' fields; only send the fields of your command.

Notable command families:
- Loans: `approve, undoApproval, reject, withdrawnByApplicant, disburse, disburseToSavings,
  undoDisbursal, undolastdisbursal, assignLoanOfficer, unassignLoanOfficer, recoverGuarantees,
  markAsFraud, charge-off, undo-charge-off` (see `domains/loans.md` for transactions-level commands).
- Savings: `approve, undoApproval, reject, withdrawnByApplicant, activate, close, block, unblock,
  blockCredit, blockDebit` + transaction commands `deposit, withdrawal, holdAmount, releaseAmount`.
- Clients: `activate, close, reject, withdraw, reactivate, undoRejection, undoWithdrawal,
  assignStaff, unassignStaff, proposeTransfer, acceptTransfer, rejectTransfer, withdrawTransfer,
  updateSavingsAccount`.

## Error envelope

Non-2xx bodies are structured:

```json
{
  "developerMessage": "The request was invalid...",
  "httpStatusCode": "400",
  "defaultUserMessage": "Validation errors exist.",
  "userMessageGlobalisationCode": "validation.msg.validation.errors.exist",
  "errors": [{
    "developerMessage": "The parameter approvedOnDate cannot be blank",
    "defaultUserMessage": "...",
    "userMessageGlobalisationCode": "validation.msg.loan.approvedOnDate.cannot.be.blank",
    "parameterName": "approvedOnDate",
    "value": null, "args": []
  }]
}
```

Common statuses: 400 validation / bad tenant · 401 bad credentials · 403 no permission (message names
the missing permission code, e.g. `error.msg.not.authorized...`) or platform errors like
domain-rule violations (also 403 with `error.msg.*` codes) · 404 unknown resource ·
409 in-flight idempotent duplicate or optimistic lock · 500 unexpected (check server logs).
See `errors-troubleshooting.md` for a catalogue.

## Write-response envelope

```json
{"officeId": 1, "clientId": 1, "loanId": 1, "resourceId": 1,
 "changes": {"status": {...}, "locale": "en"},
 "commandId": 42, "rollbackTransaction": false}
```

- `resourceId` = the entity created/acted on; sub-entity actions add `subResourceId`.
- Under maker-checker, the write is **queued**: you get `commandId` and NO `resourceId`; nothing
  changed yet until a checker approves (`domains/users-roles-permissions.md`).

## externalId — idempotent references to entities

Most core entities (clients, loans, savings, transactions…) accept a caller-supplied unique
`externalId` at creation, and 1.14 has parallel endpoint variants addressing entities by it, e.g.
`GET /v1/loans/external-id/{loanExternalId}`. Use your own system's IDs as externalIds to make
integrations idempotent and lookups cheap.

## Idempotency keys

Header `Idempotency-Key: <unique-string>` (name configurable via
`FINERACT_IDEMPOTENCY_KEY_HEADER_NAME`). Semantics: same key + same action + same entity =
same command. Completed → replays stored result with `x-served-from-cache: true`; still running →
409. Works per batch-item too (below). Always use one on money-moving writes (repayments, deposits,
disbursements).

## Batch API

`POST /v1/batches?enclosingTransaction=true` executes many calls in one request (optionally one DB
transaction — all-or-nothing):

```json
[
  {"requestId": 1, "relativeUrl": "clients", "method": "POST",
   "headers": [{"name": "Idempotency-Key", "value": "abc-1"}],
   "body": "{\"officeId\":1, ...}"},
  {"requestId": 2, "relativeUrl": "loans", "method": "POST", "reference": 1,
   "body": "{\"clientId\":\"$.clientId\", ...}"}
]
```

- `reference` points at an earlier `requestId`; `$.field` in the body resolves from that response
  (dependent chaining).
- Each item returns `{requestId, statusCode, headers, body}`; with `enclosingTransaction=true` any
  failure rolls back the whole set.
- Body is a **string** containing JSON, not nested JSON.

## Pagination, sorting, field selection

- Paginated lists: `?offset=0&limit=15&orderBy=id&sortOrder=DESC` →
  `{"totalFilteredRecords": N, "pageItems": [...]}`. `limit=-1` on some endpoints returns all.
- Many GETs support `?fields=id,name,status` partial responses.
- `?associations=all|<names>` on detail GETs pulls related collections (e.g.
  `/loans/{id}?associations=repaymentSchedule,transactions`); `exclude=` trims them.

## Search

- `GET /v1/search?query=...&resource=clients,loans` — cross-entity quick search.
- `POST /v1/search/advance` — structured queries against configured tables.
- `POST /v2/clients/search` (tag `ClientSearchV2`) — newer paged client search.

## Template endpoints

`GET /<resource>/template` returns everything needed to render a create/edit form: allowed enum
options, office/staff/product lists, defaults. Loan/savings templates take context params
(`?clientId=&productId=&templateType=`). Use templates instead of hardcoding option IDs — IDs are
tenant-specific data.

## Uploads & binary

File endpoints (client images, documents, bulk import) use `multipart/form-data`. Client images also
accept base64 data URIs. Reports can return CSV/PDF/XLS via `?exportCSV=true` etc.

## Self-service API

Parallel surface under `/v1/self/*` for end-customer apps (own data only): registration
(`/self/registration` + `/self/registration/user`), `/self/authentication`, clients, loans, savings,
share accounts, third-party transfers, run-reports, device registration for push. Backed by
self-service users (`isSelfServiceUser: true`) linked to clients. Staff APIs and self APIs enforce
different permission sets (`domains/users-roles-permissions.md`).

## API versioning note

Everything is `/api/v1` except a handful of v2 additions (e.g. `/v2/clients/search`). There is no
global v2; don't pluralize versions by guessing — check `api_lookup.py`.
