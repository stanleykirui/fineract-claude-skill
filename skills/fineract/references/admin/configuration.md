# Configuration, External Services, Hooks, Caching (Fineract 1.14.0)

Three layers of configuration:
1. **Boot-time**: env vars / `application.properties` (per instance; see `admin/operations.md`).
2. **Tenant runtime**: Global Configuration + External Services APIs (per tenant, in-DB).
3. **Entity-level**: products, charges, account number formats, etc. (the `domains/` guides).

## Global configuration (`/v1/configurations`)

`GET /v1/configurations` lists all flags; each has `name, enabled, value?, stringValue?,
dateValue?, trapDoor`. Update by id `PUT /v1/configurations/{configId}` or by name
`PUT /v1/configurations/name/{name}` with `{enabled, value}`.

High-impact entries (names as stored):
- `maker-checker` — master switch for 4-eye (then per-permission flags; see
  `domains/users-roles-permissions.md`).
- `enable_business_date` (+ related COB date handling) — logical banking day.
- `Enable-Address` — client address module; `Enable-Configurable-fields` family for client field
  requiredness.
- `allow-backdated-transaction-before-interest-posting...` — backdating rules for savings.
- `meetings-mandatory-for-jlg-loans`, `min-clients-in-group`, `max-clients-in-group`.
- `financial-year-beginning-month`, `office-specific-products-enabled`,
  `restrict-products-to-user-office`.
- `amazon-S3` — store documents in S3 instead of DB (with external service creds below).
- `reschedule-future-repayments`, `reschedule-repayments-on-holidays`, holiday/non-working-day
  behaviour.
- `savings-interest-posting-current-period-end`, `interest-charged-from-date-same-as-disbursal-date`.
- `daily-tpt-limit`, transfer limits; `sub-rates` (multi-rate interest), `charge-accrual-date`
  and penalty behaviour toggles.
- `next-payment-due-date` strategy, `days-before-repayment-due` reminders, delinquency display.
- `enable-auto-generated-external-id`, `enable-post-reversal-txns-for-reverse-transactions`.
- `purge-external-events-older-than-days`, `purge-processed-commands-older-than-days`.
- `trapDoor: true` entries are one-way (e.g. enabling some accounting behaviours) — cannot be
  switched back.

Get one by name: `GET /v1/configurations/name/{name}`.

## External services (`/v1/externalservice/{servicename}`)

Per-tenant credentialed integrations; `GET` then `PUT /v1/externalservice/S3|SMTP|SMS|NOTIFICATION`
with `{name→value}` pairs:
- `S3`: `s3_access_key, s3_secret_key, s3_bucket_name` (+ global config `amazon-S3` on).
- `SMTP`: `username, password, host, port, useTLS, fromEmail, fromName` — password resets, report
  mailing.
- `SMS`: bridge config for the (separate) mifos message-gateway (`host_name, end_point, tenant_app_key…`);
  SMS campaign endpoints live under `/v1/smscampaigns` + `/v1/sms`.
- `NOTIFICATION`: server key for FCM push (device registration endpoints pair with this).

## Hooks (`/v1/hooks`)

Webhook-style callouts on entity/action events:
`{name: "Web", displayName, isActive, events: [{actionName: "CREATE", entityName: "CLIENT"}...],
config: [{fieldName: "Payload URL", fieldValue: "https://..."}, {fieldName: "Content Type",
fieldValue: "json"}]}`. Template at `/v1/hooks/template`. Fire-and-forget; for guaranteed delivery
use the external-events framework (`architecture.md`).

## Caching (`/v1/caches`)

`GET /v1/caches` / `PUT` `{cacheType: 1=NO_CACHE | 2=SINGLE_NODE (ehcache)}`. Caches users,
permissions, config, code values etc. per tenant. After direct-DB fiddling in dev, flush by
switching cache off/on or restarting.

## Entity field configuration

`/v1/fieldconfiguration/{entity}` (e.g. ADDRESS) — which fields show/are mandatory on configurable
UIs (drives the address module's field mix).

## Audit & cleanup jobs worth enabling in prod

- `Purge External Events`, `Purge Processed Commands` (+ their `purge-*` global configs).
- Report mailing + campaign jobs only if used.

## Recipe: find any config knob

1. `GET /v1/configurations` and grep the name.
2. If not there, it's boot-time: search `application.properties` / `FINERACT_*` envs
   (`admin/operations.md` table).
3. If still not there, it's an entity setting (product/charge/etc.) — check the relevant
   `domains/` guide.
