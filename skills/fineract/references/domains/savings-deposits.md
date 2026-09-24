# Savings & Term Deposits (Fineract 1.14.0)

Tags: `Savings Product`, `Savings Account` (18 ops), `Savings Account Transactions`, `Savings
Charges`, `Fixed Deposit Product/Account/Account Transactions`, `Recurring Deposit
Product/Account/Account Transactions`, `Interest Rate Chart`, `Interest Rate Slab`, `Account
Transfers`, `Standing Instructions`, `Deposit Account On Hold Fund Transactions`, `Pocket`,
`Self Savings Account`.

## Savings products & accounts

Product (`/v1/savingsproducts`): currency, `nominalAnnualInterestRate`, `interestCompoundingPeriodType`
(daily/monthly), `interestPostingPeriodType` (monthly/quarterly/biannual/annual), `interestCalculationType`
(daily balance / average daily), `interestCalculationDaysInYearType` (360/365), `minRequiredOpeningBalance`,
`minBalanceForInterestCalculation`, overdraft (`allowOverdraft`, `overdraftLimit`,
`nominalAnnualInterestRateOverdraft`), `enforceMinRequiredBalance`, `withdrawalFeeForTransfers`,
`withHoldTax` (+`taxGroupId`), dormancy tracking (`isDormancyTrackingActive`, days to
inactive/dormant/escheat), accounting rule + GL mappings, charges.

Account lifecycle (`/v1/savingsaccounts`):

```
POST /v1/savingsaccounts   {clientId|groupId, productId, submittedOnDate, ...}   → Submitted
POST /v1/savingsaccounts/{id}?command=approve   (approvedOnDate)                 → Approved
POST /v1/savingsaccounts/{id}?command=activate  (activatedOnDate)                → Active
    also: undoApproval, reject, withdrawnByApplicant, close (withdraw balance option),
          block, unblock, blockCredit, unblockCredit, blockDebit, unblockDebit
GET /v1/savingsaccounts/{id}?associations=all   (transactions, charges)
```

Field officer assign/unassign: `POST .../savingsaccounts/{id}?command=assignSavingsOfficer|unassignSavingsOfficer`.
Gsim (group) variants exist. External-id URL variants throughout.

### Transactions (`/v1/savingsaccounts/{id}/transactions`)

`POST ?command=deposit|withdrawal` `{transactionDate, transactionAmount, paymentTypeId?, ...}` —
**Idempotency-Key recommended**. On existing transaction: `POST .../transactions/{txId}?command=undo`
(reversal), `?command=modify` (adjust = reverse+re-post), `holdAmount` / `releaseAmount` (funds
holds; held amounts listed under Deposit Account On Hold Fund Transactions tag).
`GET .../transactions/template` prefills. Interest posting happens via the scheduler job (Post
Interest For Savings) or on-demand `?command=postInterestAsOn` / `calculateInterest`.

### Charges

`/v1/savingsaccounts/{accountId}/charges` + `paycharge|waive|inactivate` commands. Withdrawal fees &
annual fees come from charge definitions with savings-applicable time types.

## Fixed deposits (FD)

Product `/v1/fixeddepositproducts`: term ranges (`minDepositTerm(+TypeId)`, `maxDepositTerm`),
`preClosurePenalApplicable` (+interest %-age), and an **interest rate chart** (see below). Account
`/v1/fixeddepositaccounts`: `{clientId, productId, depositAmount, depositPeriod(+FrequencyId),
submittedOnDate, maturityInstructions...}`; commands `approve → activate`, then at term end
`prematureClose`, `close` (payout to savings/transfer), `calculatePrematureAmount`. Interest can
transfer to a linked savings (`transferInterestToSavings`, `linkedAccountId`).

## Recurring deposits (RD)

`/v1/recurringdepositproducts` + `/v1/recurringdepositaccounts`: adds `mandatoryRecommendedDepositAmount`,
`recurringFrequency(+Type)`, `isCalendarInherited` (group meeting sync), adherence tracking. Deposit
installments arrive as transactions `POST /v1/recurringdepositaccounts/{id}/transactions?command=deposit`;
missed installments tracked; `prematureClose` supported. Account state machine mirrors FD.

## Interest rate charts (FD/RD pricing)

`/v1/interestratecharts` (chart per product, from/end dates) with slabs
`/v1/interestratecharts/{chartId}/chartslabs`: period-based (e.g. 1–6 months → 5%) and/or
amount-range-based tiers; optional incentives (e.g. +0.25% for female clients — attribute-based
`incentives` per slab).

## Moving money

- **Account transfers** (`/v1/accounttransfers`): one-off transfers savings↔savings or
  savings→loan(repayment) across clients/offices. `POST /v1/accounttransfers`
  `{fromOfficeId, fromClientId, fromAccountType(2=savings), fromAccountId, toOfficeId, toClientId,
  toAccountType(1=loan|2=savings), toAccountId, transferAmount, transferDate, transferDescription}`.
  Template + `templateRefundByTransfer` for loan refunds via transfer.
- **Standing instructions** (`/v1/standinginstructions`): recurring scheduled transfers (fixed amount /
  full balance / interest posted), priority, validity window; history at
  `/v1/standinginstructionrunhistory`; executed by the Execute Standing Instruction scheduler job.
- **Self third-party transfers**: `/v1/self/accounttransfers` + beneficiary management
  (`/v1/self/beneficiaries/tpt`).

## Pocket

`/v1/self/pockets` — a self-service "pocket" linking several of the user's accounts for one view
(`?command=linkAccounts|delinkAccounts`).

## Gotchas

- Interest posting is job-driven; a freshly activated account shows 0 interest until the posting job
  runs (or `postInterestAsOn` is called — needs global config allowing backdated posting).
- `close` on savings requires zero (or withdrawn) balance; use `withdrawBalance: true` payload.
- Overdraft usage appears as negative `accountBalance`; interest on overdraft posts separately.
- Dormancy: transactions on a dormant account are rejected until reactivation per product dormancy
  settings.
- FD/RD "accounts" are savings subtypes — some generic savings endpoints work on them (e.g.
  transactions listing), but lifecycle commands live on their own resource paths.
- Transfers between currencies are rejected — same currency both sides.
- On-hold amounts reduce available but not ledger balance (see `availableBalance` vs
  `accountBalance` in summaries).
