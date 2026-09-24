# Clients, Groups, Centers (Fineract 1.14.0)

Tags: `Client`, `Client Identifier`, `Client Charges`, `Client Transaction`, `Client Family Member`,
`Clients Address`, `Client Collateral Management`, `ClientSearchV2`, `Groups`, `Centers`, `Calendar`,
`Meetings`, `Collection Sheet`, `Documents`, `Notes`.

## Clients

The customer entity (person or entity — `legalFormId`: 1=PERSON, 2=ENTITY).

Lifecycle: `Pending → Active → Closed` (+ `Rejected`, `Withdrawn`, `Transfer in progress/on hold`).
- `POST /v1/clients` — create. Either `firstname`/`lastname` (person) or `fullname` (entity);
  `officeId` required. `active:true` + `activationDate` creates directly active; otherwise Pending.
  Optional at create: `mobileNo` (unique), `externalId` (unique), `dateOfBirth`, `staffId`,
  `savingsProductId` (opens+links a savings account), `datatables` (inline custom data),
  `address` (if Address module enabled), `familyMembers`.
- `POST /v1/clients/{id}?command=` — `activate | close | reject | withdraw | reactivate |
  undoRejection | undoWithdrawal | assignStaff | unassignStaff | updateSavingsAccount |
  proposeTransfer | withdrawTransfer | rejectTransfer | acceptTransfer | proposeAndAcceptTransfer`.
  Transfers move a client between offices/branches (with their accounts).
- `PUT /v1/clients/{id}` update · `DELETE` only while Pending and unused.
- `GET /v1/clients` (paged; filters `officeId, displayName, firstName, lastName, externalId, status,
  orphansOnly, sqlSearch`) · `GET /v1/clients/{id}` (`?associations=all` isn't used here — related
  data has its own endpoints) · by external id: `/v1/clients/external-id/{externalId}`.
- `GET /v1/clients/{id}/accounts` — all their loan/savings/shares accounts with statuses. THE
  overview call for a customer 360.
- `POST /v2/clients/search` — modern paged/structured search (tag ClientSearchV2).
- Images: `POST/GET/DELETE /v1/clients/{id}/images` (multipart or data-URI; GET supports resize).

### Sub-resources

- **Identifiers** (KYC documents): `GET/POST /v1/clients/{clientId}/identifiers`, PUT/DELETE by id.
  Each = `{documentTypeId (code value from "Customer Identifier"), documentKey, status, description}`.
  Uniqueness of (type+key) enforced per tenant.
- **Documents** (file attachments, generic): `/v1/{entityType}/{entityId}/documents` — e.g.
  `/v1/clients/1/documents`, multipart upload, then `/documents/{id}/attachment` to download.
- **Addresses**: `GET/POST/PUT /v1/client/{clientId}/addresses` (enable via global config
  `Enable-Address`; field mix configured by `/v1/fieldconfiguration/{entity}`).
- **Family members**: `/v1/clients/{clientId}/familymembers`.
- **Charges** (client-level fees, e.g. membership/registration fees, fines): see
  **Client charges** below — they have several non-obvious behaviours.
- **Notes**: `/v1/clients/{id}/notes` (same pattern on groups/loans/savings).

## Client charges — how they actually behave

Tags `Client Charges` + `Client Transaction`. Charge definitions live in `/v1/charges`
(`chargeAppliesTo` = client); a client gets an **instance** of one.

**Identity.** Pay/waive/retrieve/delete take the **instance id** — the `id` in the list response (the
legacy reference calls it `clientChargeId`). The spec names this path parameter `{chargeId}`, but it is
**not** the definition's `chargeId`, which also appears in the payload. Mixing them up targets the
wrong row or 404s.

| Action | Call | Notes |
|---|---|---|
| Add | `POST /v1/clients/{clientId}/charges` `{chargeId, amount, dueDate, dateFormat, locale}` | JSON key is **`dueDate`** (the Java constant is `dueAsOfDateParamName`). Due date may not precede activation (`dueDate.before.activationDate`) or fall on a holiday / non-working day (`charge.due.date.is.on.holiday` / `...a.non.workingday`) |
| List | `GET /v1/clients/{clientId}/charges` | `?pendingPayment=true` = neither paid nor waived. **Per client only** — there is no endpoint across clients; use a Table report over `m_client_charge` for inventories |
| History | `GET .../charges/{id}?associations=transactions` | every payment/waiver on that instance |
| Pay | `POST .../charges/{id}?command=paycharge` `{amount, transactionDate, dateFormat, locale, paymentTypeId?, receiptNumber?, externalId?}` | **Partial payments are native**. Returns `transactionId` |
| Waive | `POST .../charges/{id}?command=waive` (no body) | Waives **the entire remaining outstanding** — there is no partial waive |
| Delete | `DELETE .../charges/{id}` | Only while no payment exists → else `error.msg.client.charge.cannot.be.deleted` (waive instead) |
| Undo | `POST /v1/clients/{clientId}/transactions/{transactionId}?command=undo` | The only command there. Undoes a payment *or* a waiver; already reversed → `error.msg.clients.transaction.cannot.be.undone` |

**Fields:** `amount`, `amountPaid`, `amountWaived`, `amountWrittenOff`, `amountOutstanding`; flags
`isActive`, `isPaid`, `isWaived`, `penalty` (not `isPenalty`). No `amountPaidOutstanding` — that is a
loan-charge field.

**Rules that bite:**
- **Overpaying is a hard 400**, validated before anything changes:
  `validation.msg.CLIENTCHARGE.transaction.invalid.charge.amount.paid.in.access` ("in access" is a
  long-standing typo for "in excess"). Always pay at most `amountOutstanding`, read just before
  paying. Paying a settled charge → `...charge.is.paid`; a waived one → `...already.waived`; an
  inactive one → `charge.is.not.active`.
- **Active client required** for add, pay, waive, delete and undo (403
  `error.msg.client.not.active.exception`).
- **Payment dates:** not before client activation (`transaction.before.activationDate`), not in the
  future (`transaction.is.futureDate`), not on a holiday or non-working day (`...is.on.holiday` /
  `...is.a.non.workingday`). The holiday / non-working-day checks (for payments and due dates) are
  skipped when global configs `allow-transactions-on-holiday` / `allow-transactions-on-non-workingday`
  are enabled — needed for 24/7 channels such as USSD or M-Pesa.
- **After a waive, `isPaid` stays `false`** (`isWaived: true`, `amountOutstanding: 0`,
  `amountPaid` unchanged). Test "settled" with `amountOutstanding == 0`, never `isPaid`.
- **A posted charge's amount can never change** — update is not implemented. To change a fee, waive
  (or delete, if unpaid) and add a new instance.
- **Nothing stops duplicates**: there is no unique constraint on client + charge definition, so
  enforce "one instance" yourself.
- **Drift:** `paycharge` derives outstanding by *subtracting* the payment, while undo recomputes
  `amount − paid − waived − writtenOff`. With a 0-decimal currency using `inMultiplesOf`, rounding can
  make the two disagree (even a negative outstanding, which then permanently fails the overpay check).
  Audit with `amount = paid + waived + writtenOff + outstanding`.
- **Client charges don't drive client status** — paying one never activates the client. "Activate the
  member once the fee is fully paid" needs orchestration above Fineract.

**Accounting (cash):**
- A payment posts **Cr the charge definition's GL account** (its income account) and **Dr the account
  mapped to Financial Activity 103 `fundSource`** — a single org-wide mapping, **not payment-type
  aware** (see `accounting.md`).
- Accounting runs only if **at least one paid charge's definition has a GL account**; otherwise the
  payment posts **no journal entries at all**, silently. If 103 is unmapped, a payment that does need
  accounting fails with `error.msg.financialActivityAccount.not.found`.
- **Waivers post no journal entry** — there is no waive-off account and **no write-off command** for
  client charges. Forgone fees are visible only in `amountWaived`.
- Undo posts **new opposite-sign entries at the original transaction date**, resolving activity 103
  **at posting time** (after a remap, reversing an old payment credits the *new* account), and is
  rejected if an accounting closure covers that date.

## Groups

Solidarity/lending groups of clients (also standalone). Tag `Groups`.

- `POST /v1/groups` — `{name, officeId, active?, activationDate?, clientMembers?}`.
- Commands on `POST /v1/groups/{id}?command=`: `activate | close | associateClients |
  disassociateClients | assignStaff | unassignStaff | transferClients` etc.
- `GET /v1/groups/{id}?associations=all` includes members.
- Group loans: `POST /v1/loans` with `groupId` instead of `clientId`; GLIM (group loan w/ individual
  monitoring) uses `/v1/loans/glimAccount/{glimId}` + Bulk-Loans endpoints.
- GSIM (group savings individual monitoring): `/v1/savingsaccounts/gsim...` endpoints.

## Centers

A meeting-place aggregation of groups (MFI field model). Tag `Centers`.
- `POST /v1/centers`, commands `activate | associateGroups | disassociateGroups | close |
  saveCollectionSheet`, `GET /v1/centers/{id}?associations=groupMembers`.

## Meetings & collection sheets (field operations)

- **Calendars** attach meeting schedules to centers/groups:
  `/v1/{entityType}/{entityId}/calendars` (recurrence rules).
- **Meetings**: `/v1/{entityType}/{entityId}/meetings` — attendance tracking.
- **Collection sheet**: `POST /v1/collectionsheet?command=generateCollectionSheet` then
  `?command=saveCollectionSheet` — bulk field collection of repayments/deposits for a
  center/group meeting day. Individual (non-grouped) variant: `/v1/individualcollectionsheet`.

## Gotchas

- Client create with `active:false` → must later `?command=activate` with `activationDate` ≥
  `submittedOnDate` and not in future (unless global config allows).
- `displayName` is derived; search by it uses `displayName` param.
- Deleting is only for data-entry errors in Pending; production flows close instead.
- Client numbering is controlled by Account Number Format admin (`/v1/accountnumberformats`,
  entity CLIENT) — don't assume `accountNo` shape.
- A client's office is immutable except via the transfer flow.
