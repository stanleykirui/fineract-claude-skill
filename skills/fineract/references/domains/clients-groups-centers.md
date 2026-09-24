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
- **Charges** (client-level fees): `/v1/clients/{clientId}/charges` + `?command=paycharge|waive` on
  `.../charges/{chargeId}`; transactions listed under `/v1/clients/{clientId}/transactions`
  (undo via `POST .../transactions/{transactionId}?command=undo`).
- **Notes**: `/v1/clients/{id}/notes` (same pattern on groups/loans/savings).

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
