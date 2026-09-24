# Operating Fineract 1.14.0 (env vars, deployment, observability, failures)

## Runtime layout

Spring Boot fat app `fineract-provider` listening on **8443 (TLS)**; context path
`/fineract-provider`; API under `/fineract-provider/api/v1`; actuator under
`/fineract-provider/actuator` (default exposed: `health,info,prometheus` via
`FINERACT_MANAGEMENT_ENDPOINT_WEB_EXPOSURE_INCLUDE`). Needs: registry DB + tenant DB(s)
(MariaDB 10.6+/11 or PostgreSQL), optional ActiveMQ/Kafka for events & remote partitioning.

## Env vars that matter (defaults from application.properties)

| Group | Vars |
|---|---|
| Registry DB pool | `FINERACT_HIKARI_JDBC_URL` (e.g. `jdbc:mariadb://db:3306/fineract_tenants`), `FINERACT_HIKARI_USERNAME`, `FINERACT_HIKARI_PASSWORD`, `FINERACT_HIKARI_DRIVER_SOURCE_CLASS_NAME`, `FINERACT_HIKARI_{MINIMUM_IDLE,MAXIMUM_POOL_SIZE,IDLE_TIMEOUT,CONNECTION_TIMEOUT,TEST_QUERY,AUTO_COMMIT}` + `FINERACT_HIKARI_DS_PROPERTIES_*` |
| Default tenant bootstrap | `FINERACT_DEFAULT_TENANTDB_{HOSTNAME,PORT,UID,PWD,NAME,IDENTIFIER,TIMEZONE,DESCRIPTION,CONN_PARAMS,MASTER_PASSWORD}` (+ `_RO_*` read-replica set) — defaults: identifier `default`, db `fineract_default`, timezone `Asia/Kolkata`, master password `fineract` |
| Instance mode | `FINERACT_MODE_READ_ENABLED`, `FINERACT_MODE_WRITE_ENABLED`, `FINERACT_MODE_BATCH_WORKER_ENABLED`, `FINERACT_MODE_BATCH_MANAGER_ENABLED` (all default true) |
| Security | `FINERACT_SECURITY_BASICAUTH_ENABLED`, `FINERACT_SECURITY_OAUTH_ENABLED`, `FINERACT_SECURITY_2FA_ENABLED`, `FINERACT_SERVER_OAUTH_RESOURCE_URL`, `FINERACT_SECURITY_CORS_*`, `FINERACT_SECURITY_HSTS_ENABLED`, `FINERACT_SERVER_SSL_ENABLED` |
| Events | `FINERACT_EXTERNAL_EVENTS_ENABLED` (+ `FINERACT_EXTERNAL_EVENTS_PRODUCER_JMS_*` broker config, Kafka variants) |
| Idempotency | `FINERACT_IDEMPOTENCY_KEY_HEADER_NAME` (default `Idempotency-Key`) |
| Node identity | `FINERACT_NODE_ID` (unique per instance in a cluster) |
| JVM | `JAVA_TOOL_OPTIONS` — upstream compose uses `-Xmx1G -XX:MaxRAMPercentage=80 -XX:+UseContainerSupport` + `--add-opens` flags (required by EclipseLink weaving — keep them) |

Any `application.properties` key can also be set Spring-style
(`SPRING_APPLICATION_JSON`, `-D` flags, etc.).

## Compose stacks in the source tree

| File | Stack |
|---|---|
| `docker-compose.yml` | MariaDB + Fineract (minimal) |
| `docker-compose-development.yml` | + Grafana/Loki/Prometheus/Tempo observability (needs the Loki Docker log-driver plugin: `docker plugin install grafana/loki-docker-driver:latest --alias loki --grant-all-permissions`) |
| `docker-compose-postgresql*.yml` | PostgreSQL variants (+ ActiveMQ / Kafka flavours for events & partitioned COB) |
| `docker-compose-community-app.yml` / `-web-app.yml` | adds the legacy community web UI |

Health gate used by compose: TCP 8443 up; real readiness =
`GET /fineract-provider/actuator/health` → `{"status":"UP"}`.

## Observability

- Prometheus scrape: `/fineract-provider/actuator/prometheus`.
- Dev stack ships Grafana (3000), Loki logs, Tempo traces (OTel; `OTEL_SERVICE_NAME=fineract`).
- Logback override mount point in compose: `/app/logback-override.xml`.
- Job outcomes: `GET /v1/jobs/{id}/runhistory` (stack traces of failed jobs live here, not always
  in stdout).

## Upgrades

Fineract migrates itself: deploy new version → write instance runs Liquibase on registry + every
tenant. Take DB backups first; large tenants can migrate for a long time on first boot of a new
version. Never run two different versions against the same DBs simultaneously (except
read-instances during a rolling window, at your own risk).

## Common startup/ops failures

| Symptom | Cause / fix |
|---|---|
| Health DOWN for minutes on first boot | Liquibase creating registry + tenant schemas — normal; tail logs, wait |
| `Invalid master password` / tenant fails to load | `schema_password` in registry not decryptable with current `FINERACT_DEFAULT_TENANTDB_MASTER_PASSWORD` — re-encrypt (see `admin/tenancy-provisioning.md`) |
| `Access denied for user` on boot | Registry/tenant DB creds wrong (`FINERACT_HIKARI_*` vs `FINERACT_DEFAULT_TENANTDB_*` — two different credential sets!) |
| Boot fails: `error looking up logging plugin loki` | Dev compose without Loki plugin installed — install it or strip the `logging:` blocks |
| 400 `Invalid tenant identifier` on every call | Missing/typo'd `Fineract-Platform-TenantId` header, or tenant not in registry |
| Port 8443 conflict | Another stack owns it — remap with a compose override, don't edit upstream files |
| Writes 409 `LoanIsLocked` at night | Loan COB running — retry after, or inline-COB the loan (`domains/batch-cob-jobs.md`) |
| Jobs never run | Scheduler stopped (`GET /v1/scheduler`), instance not batch-enabled, or (business-date mode) COB date unset |
| OOM under load | Default `-Xmx1G` — raise `JAVA_TOOL_OPTIONS`, watch Hikari pool vs DB `max_connections` |
| API 403 with permission code | Role lacks `ACTION_ENTITY` permission — not an ops issue; grant it |

## Backup essentials

Registry DB + all tenant DBs + (if S3 docs enabled) the bucket. Consistent point-in-time across
registry and tenant schemas matters for restore (identifiers ↔ schemas must agree).
