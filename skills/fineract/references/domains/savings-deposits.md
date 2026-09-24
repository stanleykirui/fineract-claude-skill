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

- **Add:** `POST /v1/savingsaccounts/{id}/charges` `{chargeId, amount, dueDate, dateFormat, locale}` —
  `amount` is **mandatory**, so the same charge definition can carry a different amount per account.
  The response's `resourceId` is the savings-account-charge id to pay against.
- **Accounting:** paying a savings charge posts **Dr the product's savings control / Cr its
  income-from-fees account** (or the charge-specific `feeToIncomeAccountMappings`) — straight from the
  account, with no fund-source mapping involved. Contrast client charges (`clients-groups-centers.md`).
- **The Pay Due Savings Charges job** collects every charge with a due date on or before the business
  date (not paid/waived, active, on an Active account) and pays the **full outstanding** — never part
  of it. If the balance can't cover it, that payment throws and **the whole job run is marked failed**,
  night after night. Don't leave due-dated charges an account can't cover — add and pay in one step
  when the funds are there.
- Paying a savings charge on a holiday is rejected unless `allow-transactions-on-holiday` is enabled.

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
  `accountBalance` in summaries). Decide "is there enough?" from `availableBalance`.
- **Every savings write needs an Active client** — creating the account included. A Pending client
  cannot even receive a deposit (403 `error.msg.client.not.active.exception`).
- **A lock-in (`lockinPeriodFrequency`) blocks *every* withdrawal until `lockedInUntilDate`** —
  including account transfers out and any system/integration withdrawal:
  `error.msg.savingsaccount.transaction.withdrawals.blocked.during.lockin.period`. Deposits in still
  work. Don't put a lock-in on an account your own processes must debit; enforce "non-withdrawable"
  in your integration layer instead.
