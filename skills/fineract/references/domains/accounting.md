# Accounting & General Ledger (Fineract 1.14.0)

Tags: `General Ledger Account`, `Journal Entries`, `Accounting Closure`, `Accounting Rules`,
`Mapping Financial Activities to Accounts`, `Periodic Accrual Accounting`, `Provisioning
Category/Criteria/Entries`, `Funds`, `Tax Components`, `Tax Group`.

Fineract keeps a full double-entry GL per tenant. Product accounting rules decide what posts
automatically; manual entries fill the gaps.

## Chart of accounts

`/v1/glaccounts`: `{name, glCode (unique), type (1=ASSET, 2=LIABILITY, 3=EQUITY, 4=INCOME,
5=EXPENSE), usage (1=DETAIL postable, 2=HEADER grouping), parentId?, manualEntriesAllowed,
description?, tagId? (code value)}`. Tree comes from parent links. `GET /v1/glaccounts?disabled=false
&manualEntriesAllowed=true&type=1&usage=1` filters. Template lists valid types/usages/tags.
Disable rather than delete once used.

## Product → GL wiring

Products carry `accountingRule`: 1=NONE, 2=CASH, 3=ACCRUAL PERIODIC, 4=ACCRUAL UPFRONT (loans);
savings/deposits/shares use NONE/CASH(/accrual for savings in 1.14). With accounting on, the product
payload must map GL accounts: loans — `fundSourceAccountId, loanPortfolioAccountId,
interestOnLoanAccountId, incomeFromFeeAccountId, incomeFromPenaltyAccountId, writeOffAccountId,
overpaymentLiabilityAccountId, transfersInSuspenseAccountId, receivableInterestAccountId (accrual),
receivableFeeAccountId, receivablePenaltyAccountId, incomeFromRecoveryAccountId,
goodwillCreditAccountId, incomeFromChargeOffInterestAccountId, chargeOffExpenseAccountId,
chargeOffFraudExpenseAccountId...`; savings — `savingsReferenceAccountId, savingsControlAccountId,
interestOnSavingsAccountId, incomeFromFeeAccountId, transfersInSuspenseAccountId, overdraft
accounts...`. Optional finer routing: `paymentChannelToFundSourceMappings`,
`feeToIncomeAccountMappings`, `penaltyToIncomeAccountMappings`.

## Journal entries

- Auto entries: every accounting-enabled product transaction posts balanced debits/credits.
- Manual: `POST /v1/journalentries` `{officeId, transactionDate, currencyCode, referenceNumber?,
  comments?, credits: [{glAccountId, amount}...], debits: [...], paymentTypeId?, accountNumber?...}`
  — must balance. Reverse: `POST /v1/journalentries/{transactionId}?command=reverseEntries`
  (creates counter-entries; original stays, flagged reversed).
- Query: `GET /v1/journalentries?officeId=&glAccountId=&manualEntriesOnly=&fromDate=&toDate=
  &transactionId=&entityType=&loanId=&savingsId=&orderBy=&sortOrder=` (paged).
  `GET /v1/journalentries/{entryId}?transactionDetails=true`.
- Opening balances migration: `/v1/journalentries/openingbalance` (+ office-level
  `/v1/officetransactions` for inter-branch cash movements).

## Accounting closures

`/v1/glclosures`: `{officeId, closingDate, comments}` — blocks entries on/before closingDate for
that office (sub-offices too). DELETE only the latest closure. Do closures after period-end checks.

Reversals — `reverseEntries`, and product-level undos such as a client-charge payment undo — post at
the **original** transaction date, so a closure covering that date blocks them too
(`error.msg.glJournalEntry.invalid.accounting.closed`). Correct closed-period items with an
adjustment in the current open period instead.

## Accounting rules (manual-entry templates)

`/v1/accountingrules`: predefine debit/credit account (or allowed lists via tags) so tellers post
standard vouchers fast; `POST /v1/journalentries` accepts `accountingRule` id.

## Financial activity mapping

`/v1/financialactivityaccounts`: map platform activities → GL accounts. Activity ids (source:
`AccountingConstants.FinancialActivity`): 100=Asset Transfer, 200=Liability Transfer (savings
transfers in transit), 101=Cash at Mainvault, 102=Cash at Teller, **103=Fund Source (the GL debited
by every client-charge payment — its only consumer in the codebase)**, 201=Payable Dividends,
300=Opening Balances Contra. Required before tellers/vault ops and inter-account transfer suspense
postings work.

**Activity 103 (Fund Source) in detail** — it must map to an **ASSET** account, and it is **not
payment-type aware**: every client-charge payment debits the same account, however the money arrived.
Fineract resolves it **at posting time** with a throw-if-missing lookup, so:
- unmapped → accounting-enabled client-charge payments fail with
  `error.msg.financialActivityAccount.not.found` (tenants aren't mapped out of the box — check with
  `GET /v1/financialactivityaccounts`);
- remapping affects future payments **and reversals of old ones** — an undo credits the *new* account,
  not the one the original payment debited;
- remap with `PUT /v1/financialactivityaccounts/{mappingId}`, never delete-then-create — while
  unmapped, every such payment in the tenant fails.

## Periodic accrual

For ACCRUAL PERIODIC loan products, accrued interest/fees post via the **Add Periodic Accrual
Transactions** job or on-demand `POST /v1/runaccruals` `{tillDate}` (tag Periodic Accrual Accounting).

## Provisioning (loan-loss)

- Categories `/v1/provisioningcategory` (e.g. STANDARD, SUB-STANDARD, DOUBTFUL, LOSS),
- Criteria `/v1/provisioningcriteria`: per loan product, per category age bands + provisioning % +
  liability & expense GL accounts,
- Entries `/v1/provisioningentries`: `{date, createjournalentries?}` generates the provisioning run
  (+ `?command=recreateprovisioningentry`, `addjournalentries`); view entries per run.

## Funds & fund mapping

`/v1/funds` — sources of lending capital tagged on loans (fundId), used in reporting/portfolio splits.

## Taxes (withholding on interest)

`/v1/taxes/component` `{name, percentage, creditAccountType, creditAccountId, startDate}` →
`/v1/taxes/group` bundles components with date ranges. Attach `taxGroupId` + `withHoldTax` on
savings/FD/RD products; tax withholds on interest posting.

## Gotchas

- Journal entries are office-scoped; cross-office consolidation happens in reporting, not posting.
- You cannot post to HEADER accounts or before the latest closure date.
- Reversals are new entries — totals only net out, lines remain.
- CASH vs ACCRUAL choice is fixed per product after transactions exist (create a new product to
  change).
- `transactionId` in journal queries is the string transaction identifier shared by an entry set
  (e.g. `L123` loan txn) — not the numeric entry id.
- **Client charges are cash-basis only** — there is no accrual processor for them. Posting a charge
  records no receivable; income posts only when it is paid, and only if the charge definition has a
  GL account (otherwise the payment posts **nothing**). Waivers post no entry. Details:
  `clients-groups-centers.md` → Client charges.
- **Savings-charge payments** post Dr savings control / Cr income-from-fees directly from the
  account — no fund-source mapping involved (`savings-deposits.md`).
