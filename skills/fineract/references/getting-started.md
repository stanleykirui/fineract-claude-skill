# Getting started with Apache Fineract 1.14.0

## What it is

Multi-tenant core banking platform: clients/groups, loan & savings/deposit/share products and accounts,
double-entry accounting, reporting, scheduler jobs, self-service APIs. Java 21 + Spring Boot; REST API
under JAX-RS (Jersey); persistence via EclipseLink + Liquibase migrations; MariaDB (default) or
PostgreSQL. One **registry database** (`fineract_tenants`) lists tenants; each tenant gets its **own
schema/database** (default tenant DB: `fineract_default`).

## Run it (Docker, recommended)

From a Fineract source checkout:

```bash
docker compose up -d          # docker-compose.yml = MariaDB + Fineract
# or the full dev stack (adds Grafana/Loki/Prometheus/Tempo observability):
docker compose -f docker-compose-development.yml up -d
```

- Image: `apache/fineract:latest` (or build your own — below). API on **https://localhost:8443**.
- First boot runs Liquibase migrations for the registry + default tenant — health can stay DOWN for
  several minutes. Watch: `docker compose logs -f fineract`.
- Postgres variants exist: `docker-compose-postgresql.yml` etc.

### Build the image from source (Jib — no Dockerfile)

```bash
./gradlew :fineract-provider:jibDockerBuild -x test
docker tag fineract:latest apache/fineract:latest   # compose expects this name
```

Gradle needs Java 21 and serious resources (upstream recommends 16 GB RAM / 8 cores for full builds).
Plain jar: `./gradlew :fineract-provider:bootJar` → `java -jar fineract-provider/build/libs/fineract-provider.jar`
(needs a reachable MariaDB and the `FINERACT_HIKARI_*` / `FINERACT_DEFAULT_TENANTDB_*` env vars, see
`admin/operations.md`).

## Smoke-test it

```bash
# health (no auth)
curl -k https://localhost:8443/fineract-provider/actuator/health

# first authenticated call — offices list
curl -k -u mifos:password -H "Fineract-Platform-TenantId: default" \
  "https://localhost:8443/fineract-provider/api/v1/offices"

# login endpoint (credentials in JSON BODY, not query params — changed by FINERACT-726)
curl -k -X POST "https://localhost:8443/fineract-provider/api/v1/authentication?tenantIdentifier=default" \
  -H "Content-Type: application/json" -d '{"username":"mifos","password":"password"}'
```

Defaults: superuser **`mifos` / `password`**, tenant **`default`**. TLS is a self-signed cert →
`curl -k`, or front it with a real cert/proxy in production.

Useful UIs on a running instance:
- Swagger UI: `https://localhost:8443/fineract-provider/swagger-ui/index.html`
  (spec JSON itself: `https://localhost:8443/fineract-provider/fineract.json`)
- Legacy API reference: `https://localhost:8443/fineract-provider/legacy-docs/apiLive.htm`
- Actuator: `/fineract-provider/actuator/{health,info,prometheus}`

## A minimal end-to-end flow (client → loan)

```bash
B="https://localhost:8443/fineract-provider/api/v1"
H1='Fineract-Platform-TenantId: default'; AUTH='-u mifos:password'

# 1. create a client (activated immediately)
curl -k $AUTH -H "$H1" -H 'Content-Type: application/json' -X POST "$B/clients" -d '{
  "officeId": 1, "firstname": "Jane", "lastname": "Doe", "legalFormId": 1,
  "active": true, "activationDate": "24 September 2026",
  "dateFormat": "dd MMMM yyyy", "locale": "en"}'

# 2. inspect what a loan application needs
curl -k $AUTH -H "$H1" "$B/loans/template?clientId=1&templateType=individual"

# 3. submit → approve → disburse (three separate steps; approve/disburse are ?command= POSTs)
curl -k $AUTH -H "$H1" -X POST "$B/loans"                     -d '{...application...}'
curl -k $AUTH -H "$H1" -X POST "$B/loans/1?command=approve"   -d '{"approvedOnDate":"24 September 2026","dateFormat":"dd MMMM yyyy","locale":"en"}'
curl -k $AUTH -H "$H1" -X POST "$B/loans/1?command=disburse"  -d '{"actualDisbursementDate":"24 September 2026","transactionAmount":1000,"dateFormat":"dd MMMM yyyy","locale":"en"}'
```

A loan application needs an existing **loan product** (`POST /v1/loanproducts` — admin-side, many
fields; use `GET /v1/loanproducts/template` and see `domains/loans.md`).

## Where things live in the source tree

| Path | What |
|---|---|
| `fineract-provider/` | The runnable Spring Boot app (config in `src/main/resources/application.properties`) |
| `fineract-core/`, `fineract-loan/`, `fineract-savings/`… | Domain modules (see `architecture.md`) |
| `fineract-client/` | Generated Java client from the OpenAPI spec |
| `fineract-doc/src/docs/en/` | Official AsciiDoc documentation (150 files) |
| `config/docker/env/*.env` | Canonical env-var examples for compose |
| `integration-tests/` | REST-Assured integration tests — great as API usage examples |
