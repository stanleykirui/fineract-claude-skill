# Multi-tenancy & Tenant Provisioning (Fineract 1.14.0)

## Model

- **Registry DB** `fineract_tenants` (name configurable) holds tables `tenants`,
  `tenant_server_connections`, `timezones`. Each row in `tenants` = one tenant: `identifier`
  (the value clients send in `Fineract-Platform-TenantId`), `name`, `timezone_id`,
  `oltp_id`/`report_id` → FK to `tenant_server_connections`.
- **`tenant_server_connections`** = where that tenant's data lives: `schema_server`,
  `schema_server_port`, `schema_name`, `schema_username`, `schema_password` (**encrypted**, below),
  `schema_connection_parameters`, connection-pool tuning columns, plus optional read-only replica
  fields.
- Each tenant gets its **own schema/database** (default: `fineract_default`). Full isolation — no
  shared tables between tenants.
- On startup, the **write instance** runs Liquibase: first the registry (`tenant-store` changelog),
  then EVERY tenant schema listed in the registry (`tenant` changelog). New empty schemas get fully
  created; existing ones migrate.

## There is NO tenant REST API

Upstream 1.14 has no `/tenants` endpoint (verify: `api_lookup.py "tenant"` → nothing). Provisioning
is an infrastructure operation:

1. Create the DB/schema and a DB user with rights on it:
   ```sql
   CREATE DATABASE `fineract_acme`;
   ```
2. Encrypt the tenant DB password with the platform's **master password**
   (`FINERACT_DEFAULT_TENANTDB_MASTER_PASSWORD` / `fineract.tenant.master-password`, default
   `fineract`; algorithm `fineract.tenant.encrytion` — note the upstream property typo — default
   `AES/CBC/PKCS5Padding`). The class `org.apache.fineract.infrastructure.core.service.database.DatabasePasswordEncryptor`
   has a runnable `main(masterPassword, plainPassword)` that prints the encrypted Base64 password
   AND the BCrypt master-password hash the row also stores.
3. Insert into the registry:
   ```sql
   INSERT INTO tenant_server_connections (schema_server, schema_name, schema_server_port,
     schema_username, schema_password, master_password_hash, auto_update, ...)
   VALUES ('db', 'fineract_acme', '3306', 'root', '<encrypted-b64>', '<bcrypt-hash>', true, ...);
   INSERT INTO tenants (identifier, name, timezone_id, oltp_id, report_id, ...)
   VALUES ('acme', 'Acme SACCO', <tz-id>, <conn-id>, <conn-id>, ...);
   ```
4. Restart (or start) a write instance → Liquibase materializes the new schema with seed data
   (superuser `mifos`/`password`, Head Office, permissions, jobs...).
5. Call it: `Fineract-Platform-TenantId: acme`.

If the encrypted password / master hash don't match what the running instance's master password
decrypts, startup fails for that tenant (`Invalid master password` style errors) — encryption
parity between whoever provisions and the Fineract runtime is the classic pitfall.

## Default-tenant bootstrap envs

The default tenant is auto-created at first boot from env: `FINERACT_DEFAULT_TENANTDB_{HOSTNAME,
PORT,UID,PWD,NAME,IDENTIFIER,TIMEZONE,DESCRIPTION,CONN_PARAMS,MASTER_PASSWORD}` (see
`admin/operations.md`). The registry connection itself: `FINERACT_HIKARI_JDBC_URL`,
`FINERACT_HIKARI_USERNAME`, `FINERACT_HIKARI_PASSWORD`.

## Read replicas per tenant

`tenant_server_connections` readonly columns (`readonly_schema_server`, etc. — populated via
`FINERACT_DEFAULT_TENANTDB_RO_*` for the default tenant) let read instances route tenant reads to a
replica. Empty = reads go to the primary.

## Request routing recap

Every request resolves its tenant from `Fineract-Platform-TenantId` header (or
`?tenantIdentifier=`), looks up the registry (cached), and opens/uses that tenant's datasource.
Wrong identifier → 400 `error.msg.tenant.identifier.invalid` style. The header is trusted — put an
auth layer in front if clients must not choose their tenant freely.

## Timezones

`tenants.timezone_id` → `timezones` table. All "today" computations (jobs, maturity, overdue) use
the tenant timezone (unless business dates are enabled — see `domains/batch-cob-jobs.md`).

## Operational cautions

- Registry rows are read at startup and cached; adding a tenant typically requires a restart of
  each instance (no hot-reload API upstream).
- Backups must cover the registry AND every tenant schema atomically enough for restore sanity.
- One runaway tenant can exhaust shared instance resources — pool columns per connection row are
  the lever.
- Cross-tenant queries don't exist at the API; analytics across tenants = external ETL.
