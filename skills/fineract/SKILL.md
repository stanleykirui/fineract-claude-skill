---
name: fineract
description: "Apache Fineract 1.14.0 core banking platform — API reference (clients, loans, savings, deposits, shares, accounting, tellers, self-service), admin & operations (multi-tenancy, provisioning, scheduler/COB jobs, configuration, security), and usage conventions. Use for ANY question about Fineract: calling or debugging its REST APIs, request/response shapes, error messages, running/deploying it, tenant management, or how a Fineract feature works."
---

# Apache Fineract 1.14.0

Fineract is a multi-tenant core banking / microfinance platform (Java 21, Spring Boot, JAX-RS/Jersey,
MariaDB or PostgreSQL). This skill is **pinned to version 1.14.0** and carries the complete API surface
of that release: **563 paths, 879 operations, 1,476 schemas, 151 tags**.

## How to answer API questions — use the lookup script, don't guess

Exact endpoint/parameter/schema answers come from the bundled spec via:

```bash
python skills/fineract/scripts/api_lookup.py <args>     # run from this skill's directory root
```

| Need | Command |
|---|---|
| Find operations by keyword | `api_lookup.py "savings"` (matches path, summary, tag, operationId) |
| Everything under one tag | `api_lookup.py --tag "Loan Transactions"` |
| Full detail of one operation (params, request/response schemas) | `api_lookup.py --op "POST /v1/loans/{loanId}/transactions"` |
| Resolve a schema's fields | `api_lookup.py --schema PostLoansRequest` (fuzzy name match) |
| List all tags (feature areas) | `api_lookup.py --tags` |
| Narrative docs for a resource (field semantics, examples) | `api_lookup.py --legacy loans` · list anchors: `--legacy-list loan` |

The spec (`api/fineract-1.14.0.openapi.json`, 1.3 MB) and legacy doc (`api/apiLive-1.14.0.htm`, 1.7 MB)
must **never** be read wholesale into context — always go through the script.

## Core conventions (memorize these — they answer 80% of problems)

1. **Base URL**: `https://<host>:8443/fineract-provider/api/v1` (self-signed TLS by default → `curl -k`).
2. **Every request needs a tenant**: header `Fineract-Platform-TenantId: default` (or query param
   `?tenantIdentifier=default`). Missing/wrong tenant → `400 Invalid tenant identifier`.
3. **Auth**: HTTP Basic (default `mifos` / `password`) enabled by default. A login endpoint exists:
   `POST /v1/authentication` with **JSON body** `{"username":"mifos","password":"password"}` — since
   FINERACT-726 credentials go in the body, NOT query params. It returns `base64EncodedAuthenticationKey`
   plus the user's roles/permissions; you still send it as a Basic header on subsequent calls.
   OAuth2 and 2FA are opt-in (see `references/admin/security.md`).
4. **Dates need `dateFormat` + `locale` in the same payload**, and dates are strings in that format:
   `{"submittedOnDate": "24 September 2026", "dateFormat": "dd MMMM yyyy", "locale": "en"}`.
   Responses return dates as arrays `[2026, 9, 24]`.
5. **State changes are commands**: `POST /v1/<resource>/{id}?command=<verb>` — e.g. loans:
   `approve`, `disburse`, `undoApproval`, `reject`, `withdrawnByApplicant`, `assignLoanOfficer`;
   savings: `activate`, `deposit`, `withdrawal`. The same URL with different `command` values does
   different things — always check with `--op`.
6. **Error envelope** is consistent:
   `{"developerMessage", "httpStatusCode", "defaultUserMessage", "userMessageGlobalisationCode",
   "errors": [{"parameterName", "defaultUserMessage", "userMessageGlobalisationCode", "args"}]}`.
   The `userMessageGlobalisationCode` (e.g. `validation.msg.loan.approvedOnDate.cannot.be.blank`) is
   the precise machine key — search it in the legacy doc or codebase to diagnose.
7. **Write responses** return `{"officeId", "clientId", "loanId", "resourceId", "changes": {...}}` —
   `resourceId` is the created/affected entity; `changes` echoes what was modified.
8. **Pagination**: `?offset=0&limit=200` (+ `orderBy`/`sortOrder` on paginated lists) →
   `{"totalFilteredRecords", "pageItems": [...]}`. Un-paginated lists return a bare array.
9. **Idempotency**: send header `Idempotency-Key: <unique>` on writes. Replay of a completed command
   returns the original result with `x-served-from-cache: true`; an in-flight duplicate returns 409.
10. **Template pattern**: most resources have `GET /<resource>/template` returning the dropdown
    options/defaults needed to build a create form (e.g. `/v1/loans/template?clientId=1&templateType=individual`).
11. **Maker-checker**: if enabled for a permission, a write returns the command as a pending
    `commandId` instead of executing; a different user with the `CHECKER` capability approves via
    `POST /v1/makercheckers/{auditId}?command=approve`. Permissions ending `_CHECKER` control this.
12. **Money**: amounts are JSON numbers with product-defined `digitsAfterDecimal`; currency comes from
    the product/account (`currencyCode` ISO-4217). Never assume 2 decimals.

### Canonical first call

```bash
curl -k -u mifos:password -H "Fineract-Platform-TenantId: default" \
  "https://localhost:8443/fineract-provider/api/v1/offices"
```

## Where to go deeper (progressive disclosure — read only what the task needs)

| Topic | File |
|---|---|
| Install & run (Docker, from source), first calls, health | `references/getting-started.md` |
| Request/response conventions in depth (dates, commands, batch API, external IDs, search) | `references/api-conventions.md` |
| Clients, groups, centers, KYC-ish data (identifiers, documents, addresses, family) | `references/domains/clients-groups-centers.md` |
| Loans: products, full lifecycle, transactions, charges, reschedule, delinquency, progressive loans | `references/domains/loans.md` |
| Savings, fixed & recurring deposits, interest-rate charts, account transfers, standing instructions | `references/domains/savings-deposits.md` |
| Share products & accounts, dividends | `references/domains/shares.md` |
| Accounting: GL, journal entries, closures, rules, financial-activity mapping, provisioning | `references/domains/accounting.md` |
| Organisation: offices, staff, currencies, funds, payment types, holidays, working days, tellers | `references/domains/organisation.md` |
| Users, roles, permissions, maker-checker, self-service users, password rules | `references/domains/users-roles-permissions.md` |
| Data tables (custom fields), codes/code-values, reports, run-reports, audits, notes, documents | `references/domains/datatables-reports.md` |
| Batch API, scheduler jobs, Loan COB, business dates, inline jobs | `references/domains/batch-cob-jobs.md` |
| Multi-tenancy: registry DB, creating tenants, per-tenant schemas, encrypted tenant DB passwords | `references/admin/tenancy-provisioning.md` |
| Global configuration, external services (SMTP/S3/SMS), hooks, caching, instance types | `references/admin/configuration.md` |
| Security: basic/OAuth2/2FA setup, CORS, HSTS, hardening checklist | `references/admin/security.md` |
| Operating it: env vars, compose stacks, logs/observability, common startup failures | `references/admin/operations.md` |
| Internals: module layout, command pipeline, business events, COB architecture, custom modules | `references/architecture.md` |
| Error catalogue & troubleshooting recipes | `references/errors-troubleshooting.md` |
| What's notable in 1.14.0 specifically | `references/version-notes.md` |
| **Site-specific deployment notes (if present)** | `references/local/` — read any files there **first** for local ports, credentials pointers, and quirks of the deployment at hand |

## Ground rules when advising

- **Trust the spec over memory**: Fineract's API has version-specific quirks; this skill's spec was
  captured from a live 1.14.0 build. If an answer matters, verify with `api_lookup.py` first.
- **Never invent endpoints or field names.** If the lookup finds nothing, say so and check the legacy
  doc (`--legacy`) before concluding a capability doesn't exist.
- Production advice must respect multi-tenancy (per-tenant DB isolation), idempotency on money
  movements, and maker-checker where configured.
- Default credentials (`mifos`/`password`) are for dev only — flag them in any production context.
