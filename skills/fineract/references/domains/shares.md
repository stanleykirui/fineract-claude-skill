# Share Products, Accounts & Dividends (Fineract 1.14.0)

Tags: `Products` (share products live under `/v1/products/share`), `Share Account`,
`Self Share Accounts`, `Self Dividend`.

Share capital for member-owned institutions (SACCOs, co-ops): members buy/redeem shares; the
institution declares dividends against a share product and distributes them to accounts.

## Share products

`/v1/products/share` (the generic products resource typed by `share`):
`POST /v1/products/share` `{name, shortName, currencyCode, totalShares, unitPrice, nominalShares?,
sharesIssued?, minimumShares?, maximumShares?, lockinPeriodFrequency(+Type)?, minimumActivePeriod?,
allowDividendCalculationForInactiveClients?, charges?, marketPricePeriods? (date→price),
accountingRule + GL mappings}`.
`GET /v1/products/share` list · `GET /v1/products/share/{productId}` · `PUT` update ·
`GET /v1/products/share/template`.

## Share accounts

`/v1/accounts/share` (generic accounts resource typed by `share`):

```
POST /v1/accounts/share  {clientId, productId, submittedDate, requestedShares,
                          savingsAccountId (dividend payout target), applicationDate,
                          charges?, externalId?}                       → Submitted
POST /v1/accounts/share/{accountId}?command=approve                    → Approved
POST /v1/accounts/share/{accountId}?command=activate                   → Active
   also: reject, undoApproval, applyadditionalshares,
         approveadditionalshares, rejectadditionalshares,
         redeemshares, close
```

- Additional purchases post as pending share purchase transactions needing
  `approveadditionalshares`.
- `redeemshares` `{requestedDate, requestedShares}` sells shares back (lock-in period enforced).
- `GET /v1/accounts/share/{id}` shows purchased/redeemed/pending shares, charges and dividends.
- Charges: share account fees defined in `/v1/charges` with share-applicable types
  (e.g. share purchase %).

## Dividends

- Declare on the product: `POST /v1/shareproduct/{productId}/dividend`
  `{dividendPeriodStartDate, dividendPeriodEndDate, dividendAmount}` → creates a dividend pot and
  per-account provisional allocations (pro-rated by shares held over the period).
- Review allocations: `GET /v1/shareproduct/{productId}/dividend/{dividendId}` (paged per-account).
- Approve/post: `PUT /v1/shareproduct/{productId}/dividend/{dividendId}` — posts each account's
  dividend into its linked savings account.
- Member self-view: `/v1/self/shareproducts/{productId}/dividend` (tag Self Dividend).

## Gotchas

- `totalShares` (product cap) vs `sharesIssued` — applications beyond remaining issuable shares are
  rejected.
- Unit price changes over time via `marketPricePeriods`; purchases price at the period's rate.
- Dividend posting REQUIRES each share account to have a linked active savings account in the same
  currency (`savingsAccountId` at application).
- Inactive clients only participate in dividends if the product allows it.
- Share accounts have no overdraft/withdrawal concept — only purchase/redeem.
- **Redemption's only gate is the lock-in** (`lockinPeriodFrequency`; with none set there is no
  gate): `cannot.be.redeemed.due.to.lockinperiod`. Other redeem failures:
  `cannot.be.redeemed.due.to.insufficient.shares`, `no.purchase.transaction.found.before.redeem.date`,
  `cannot.be.redeemed.due.to.insufficient.shares.for.this.redeem.date`.
- **`minimumActivePeriod` is the minimum active period *for dividends*** — it governs dividend
  eligibility, **not** redemption. Changing it changes who receives dividends.
- Fineract has **no "non-redeemable / transfer-only" flag**. If by-laws say share capital is never
  refunded (common for SACCOs, and relevant to keeping members' shares classified as equity), enforce
  it above Fineract by never exposing `redeemshares`.
- `shareReferenceId` is a **single** GL account with no per-payment-channel mapping — every purchase
  debits it, whatever the money's source.
