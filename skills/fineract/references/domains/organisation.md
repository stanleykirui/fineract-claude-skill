# Organisation setup (Fineract 1.14.0)

Tags: `Offices`, `Staff`, `Currency`, `Funds`, `Payment Type`, `Holidays`, `Working days`,
`Teller Cash Management` (19 ops), `Cashiers`, `Cashier Journals`, `Account number format`,
`Fineract Entity` (entity-to-entity mapping), `Business Date Management`.

## Offices (branch hierarchy)

`/v1/offices`: `{name, openingDate, parentId, externalId?}` — tree rooted at Head Office (id 1).
Everything (clients, users, GL entries) is office-scoped; users see their office subtree.
`GET /v1/offices?includeAllOffices=true`. Office transactions (inter-branch cash):
`/v1/officetransactions`.

## Staff & loan officers

`/v1/staff`: `{officeId, firstname, lastname, isLoanOfficer, isActive, mobileNo?, externalId?,
joiningDate?}`. Loan officers get assigned to loans/clients/groups; bulk transfer between staff via
`POST /v1/loans/loanreassignment`. `GET /v1/staff?status=active|inactive|all&officeId=`.

## Currencies

`/v1/currencies` — tenant-wide allow-list: `GET` shows `selectedCurrencyOptions` vs all;
`PUT /v1/currencies {"currencies": ["USD","KES",...]}` sets which are usable in products.

## Payment types

`/v1/paymenttypes`: `{name, description?, isCashPayment, position}` — the dropdown on every money
transaction (`paymentTypeId`), also routes GL via product paymentChannel mappings. Cash vs non-cash
affects teller cash tracking.

## Holidays & working days

- `/v1/holidays`: `{name, fromDate, toDate, offices[], reschedulingType (2=next working day |
  3=next repayment date)}` → then `POST /v1/holidays/{id}?command=activate`. Affects repayment
  schedule generation.
- `/v1/workingdays`: recurrence rule (e.g. `FREQ=WEEKLY;INTERVAL=1;BYDAY=MO,TU,WE,TH,FR`),
  `repaymentReschedulingType`, `extendTermForDailyRepayments`. One global config per tenant.

## Tellers & cashiers (branch cash management)

Model: Office → **Teller** (a till) → **Cashiers** (staff allocated to the till for a period) →
cash allocations/settlements + journals.

- `/v1/tellers`: `{officeId, name, status (300=ACTIVE), startDate...}`.
- Cashiers: `POST /v1/tellers/{tellerId}/cashiers` `{staffId, startDate, endDate, isFullDay|hours}`;
  allocate cash `POST .../cashiers/{cashierId}/allocate` `{txnAmount, currencyCode, txnDate, txnNote}`;
  settle back `POST .../cashiers/{cashierId}/settle`.
- Journals/transactions: `GET /v1/tellers/{tellerId}/journals`, `.../transactions`,
  `.../cashiers/{cashierId}/transactions` + summary.
- Requires financial activity mappings 101/103 (Cash at Teller / Mainvault) — see `accounting.md`.
- Cash transactions posted by that staff at that office flow into the cashier's running balance.

## Account number formats

`/v1/accountnumberformats`: per entity (CLIENT, LOAN, SAVINGS, CENTER, GROUP, SHARES) choose prefix
(OFFICE_NAME, CLIENT_TYPE, LOAN_PRODUCT_SHORT_NAME, SAVINGS_PRODUCT_SHORT_NAME, PREFIX_SHORT_NAME) —
controls generated `accountNo`. Set BEFORE go-live; changing later doesn't renumber.

## Entity-to-entity mapping (access scoping)

`/v1/entitytoentitymapping/{mapId}/{fromId}/{toId}` (tag Fineract Entity): restrict e.g.
office→loan products, office→savings products, role→loan product visibility.

## Business dates

`/v1/businessdate` (tag Business Date Management): `GET` current `BUSINESS_DATE` and `COB_DATE`;
`POST /v1/businessdate` `{type: "BUSINESS_DATE", date}` when global config `enable_business_date`
is on — decouples logical banking day from wall clock; COB advances it. See `batch-cob-jobs.md`.

## Typical tenant bootstrap order

1. Rename Head Office / create branch offices
2. `PUT /v1/currencies` allow-list
3. Payment types
4. Chart of accounts + financial activity mappings (`accounting.md`)
5. Staff (loan officers, tellers' staff)
6. Holidays + working days
7. Account number formats
8. Charges, then products (loan/savings/FD/RD/share)
9. Roles/permissions + users (`users-roles-permissions.md`)
10. Optional: tellers/cashiers, funds, taxes, delinquency buckets, datatables
