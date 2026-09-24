# Loans (Fineract 1.14.0)

Tags: `Loans` (31 ops), `Loan Transactions` (22), `Loan Charges` (22), `Loan Products`, `Loan
Collateral`, `Guarantors`, `Loan Disbursement Details`, `Reschedule Loans`, `Loan Rescheduling`,
`Delinquency Range and Buckets Management`, `Loan Interest Pause`, `Loan Buy Down Fees`,
`Loan Capitalized Income`, `Loan Account Lock`, `Loan COB Catch Up`, `Progressive Loan`,
`Bulk Loans`, `LoansPointInTime`, `repayment with post dated checks`.

## Loan products (admin prerequisite)

`POST /v1/loanproducts` defines everything a loan inherits: currency + `digitsAfterDecimal`,
principal/interest ranges, `interestType` (0=declining balance, 1=flat), `interestCalculationPeriodType`,
`amortizationType`, repayment frequency, grace settings, `transactionProcessingStrategyCode` (repayment
allocation order — e.g. `mifos-standard-strategy`, and in 1.14 `advanced-payment-allocation-strategy`),
accounting mapping (`accountingRule`: 1=NONE, 2=CASH, 3=ACCRUAL PERIODIC, 4=ACCRUAL UPFRONT + GL
account links), charges, penalty config, `loanScheduleType` (`CUMULATIVE` classic vs `PROGRESSIVE` new
in 1.x line — see below), down-payments, multi-disbursement (`multiDisburseLoan`, `maxTrancheCount`),
delinquency bucket. Start from `GET /v1/loanproducts/template`. Product mix (allowed combinations):
`/v1/loanproducts/{productId}/productmix`.

## Application lifecycle

```
POST /v1/loans                      submit application    (status: Submitted and pending approval)
POST /v1/loans/{id}?command=approve                     → Approved
POST /v1/loans/{id}?command=disburse                    → Active
    also: undoApproval, reject, withdrawnByApplicant, disburseToSavings, undoDisbursal,
          undolastdisbursal (multi-tranche), assignLoanOfficer, unassignLoanOfficer,
          recoverGuarantees, markAsFraud, charge-off / undo-charge-off
DELETE /v1/loans/{id}               only while pending
PUT  /v1/loans/{id}                 modify pending application
```

Application body essentials: `clientId` (or `groupId`), `productId`, `principal`,
`loanTermFrequency(+Type)`, `numberOfRepayments`, `repaymentEvery(+FrequencyType)`,
`interestRatePerPeriod`, `amortizationType`, `interestType`, `interestCalculationPeriodType`,
`transactionProcessingStrategyCode`, `expectedDisbursementDate`, `submittedOnDate`, `loanType`
(`individual|group|jlg|glim`), + `dateFormat`/`locale`. Preview schedule without saving:
`POST /v1/loans?command=calculateLoanSchedule`.

Reads: `GET /v1/loans/{id}?associations=repaymentSchedule,transactions,charges,collateral,guarantors,
futureSchedule,originalSchedule,linkedAccount,multiDisburseDetails` (or `all`; `exclude=` to trim).
Paged list `GET /v1/loans`. External-id variants exist for nearly every loan URL:
`/v1/loans/external-id/{loanExternalId}/...`.

## Transactions (`/v1/loans/{loanId}/transactions`)

`POST ...?command=`:
`repayment | merchantIssuedRefund | payoutRefund | goodwillCredit | chargeRefund | waiveinterest |
writeoff | undowriteoff | close-rescheduled | close | recoverypayment | refundByCash | foreclosure |
interestPaymentWaiver | chargeAdjustment (on .../transactions/{id})`.

Body (repayment-like): `{transactionDate, transactionAmount, paymentTypeId?, externalId?, note?,
receiptNumber?...}` + date boilerplate. **Always send an `Idempotency-Key`.**

On an existing transaction `/v1/loans/{loanId}/transactions/{transactionId}`:
- `GET` detail · `POST ?command=undo` (reverses; adjustments create counter-entries) ·
  `PUT` adjust (`adjustTransaction`) · `chargeback` command for repayment chargebacks.
- Templates: `GET /v1/loans/{id}/transactions/template?command=repayment` (prefills outstanding).

## Charges & penalties (`Loan Charges`)

`/v1/loans/{loanId}/charges`: attach product-defined charges (`chargeId`, `amount`, timing/calculation
inherited from `/v1/charges` definitions). Commands on `.../charges/{loanChargeId}`:
`pay` (from linked savings), `waive`, `adjustment`; PUT/DELETE while unpaid. Charge definitions
themselves: `/v1/charges` (applies to loans/savings/client/shares; time types: disbursement, specified
due date, installment fee, overdue penalty…; calculation: flat, % of amount, % of interest…).

## Collateral & guarantors

- Product-collateral catalogue: `/v1/collateral-management` (name, quality, base %, unit type); tie to
  loans at application or `/v1/loans/{loanId}/collaterals` (tag Loan Collateral, value/description).
- Guarantors: `/v1/loans/{loanId}/guarantors` — internal (client/staff, optionally covering from their
  savings via `savingsId`) or external person. On-hold funds tracked; `recoverGuarantees` command
  seizes them.

## Reschedule / restructure

- `POST /v1/rescheduleloans` — create a reschedule request (`loanId`, `rescheduleFromDate`,
  `rescheduleReasonId` (code value), one of: `adjustedDueDate` shift, `graceOnPrincipal/Interest`,
  `extraTerms`, `newInterestRate`, `emi` change) → then
  `POST /v1/rescheduleloans/{requestId}?command=approve|reject`. Preview:
  `GET /v1/rescheduleloans/{id}?command=previewLoanReschedule`.
- Re-ageing / re-amortization (1.14, progressive loans): `POST /v1/loans/{loanId}/transactions?command=reAge`
  and `reAmortize` (see version-notes).

## Delinquency

- Buckets/ranges admin: `/v1/delinquency/buckets`, `/v1/delinquency/ranges` — attach bucket to product.
- Per loan: `GET /v1/loans/{id}/delinquencytags`; delinquency-pause actions
  `POST /v1/loans/{loanId}/delinquency-actions` (pause/resume delinquency classification).
- Loan arrears/aging also surfaces in `r_` reports and `GET /v1/loans/{id}` summary block.

## Interest pause (1.14)

`POST /v1/loans/{loanId}/interest-pauses` (+ external-id variant, PUT/DELETE) — suspend interest
accrual for a period on progressive loans.

## Progressive loans & advanced payment allocation (headline 1.x feature)

Product `loanScheduleType: PROGRESSIVE` + `transactionProcessingStrategyCode:
"advanced-payment-allocation-strategy"` enables: configurable per-transaction-type allocation order
(`paymentAllocation` rules: PAST_DUE_PENALTY, PAST_DUE_FEE, PAST_DUE_PRINCIPAL, PAST_DUE_INTEREST,
IN_ADVANCE_*, DUE_*…), `FUTURE_INSTALLMENT` handling, down-payments, EMI recalculation, interest
pause, re-age/re-amortize, capitalized income, buy-down fees, contract termination. Progressive-only
calculators: `POST /v1/loans/calculate-interest` etc. under tag `Progressive Loan`. The embeddable
schedule generator exists as a separate artifact (`fineract-progressive-loan-embeddable-schedule-generator`).

## Point-in-time & bulk

- `GET /v1/loans/{loanId}/points-in-time?date=...` (tag LoansPointInTime) — loan state as of a date.
- Bulk loan officer reassignment: `POST /v1/loans/loanreassignment` (tag Bulk Loans).

## Loan account locks & COB

While the nightly **Loan COB** job processes a loan it takes a lock; writes then get rejected
(409/`LoanIsLocked`). Inspect locks: `GET /v1/loans/locked` (tag Loan Account Lock). Catch-up stale
loans: tag `Loan COB Catch Up` (`POST /v1/loans/catch-up`, `GET /v1/loans/is-catch-up-running`).
See `batch-cob-jobs.md`.

## Gotchas

- Approve/disburse amounts can differ from applied principal (`approvedLoanAmount`,
  `transactionAmount` at disburse) within product min/max.
- `writeoff` then `undowriteoff` restores; `close` requires zero balance; `foreclosure` computes
  early-settlement amounts (template shows them).
- Interest waivers/goodwill credits are transactions, not charge edits.
- Backdating past the last transaction triggers reprocessing; with accrual accounting expect
  replayed journal entries.
- Multi-disbursement products need `disbursementData` tranches at application/approval.
- `LoanIsLocked` during COB window → retry after COB or use catch-up API, don't force.
