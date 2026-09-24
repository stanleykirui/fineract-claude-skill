# Internals & Architecture (Fineract 1.14.0)

For contributors, custom-module authors, and anyone debugging behaviour below the API.

## Stack

Java 21 · Spring Boot 3 · **JAX-RS (Jersey)** resources (NOT Spring MVC — that's why springdoc
live-scan is empty and the OpenAPI spec is pre-generated) · EclipseLink JPA (static weaving — the
`--add-opens` JVM flags are required) · Liquibase migrations · MariaDB/PostgreSQL · Spring Batch
(COB) · ActiveMQ/JMS or Kafka (events, remote partitioning) · Avro (event payloads).

## Gradle modules (this source tree)

| Module | Role |
|---|---|
| `fineract-provider` | The deployable app: JAX-RS resources, Spring wiring, `application.properties`, Liquibase changelogs (`db/changelog/tenant-store` = registry, `.../tenant` = per-tenant schema) |
| `fineract-core` | Kernel: multi-tenancy, security, command processing, configuration, codes, offices/staff/orgs, infrastructure |
| `fineract-loan`, `fineract-savings`, `fineract-accounting`, `fineract-charge`, `fineract-rates`, `fineract-tax`, `fineract-document`, `fineract-report`, `fineract-branch` | Domain modules (entities + services per area) |
| `fineract-progressive-loan` (+ `-embeddable-schedule-generator`) | Progressive loan engine; the embeddable artifact computes schedules outside Fineract |
| `fineract-investor` | External asset owners (loan sales/transfers to investors) |
| `fineract-cob` | Close-of-business batch framework (Spring Batch, business steps, locking) |
| `fineract-command` | Newer command-pipeline infrastructure |
| `fineract-avro-schemas` | Avro definitions of all business events |
| `fineract-client` / `fineract-client-feign` | Generated Java API clients (from the OpenAPI spec) |
| `fineract-db`, `fineract-validation`, `fineract-doc`, `fineract-war`, `fineract-e2e-tests-*`, `integration-tests` | Support/build/test/docs |
| `custom/` | **Custom module system** — drop-in extension modules (below) |

## The command pipeline (why writes look the way they do)

Every write is a **JsonCommand** routed through the commands framework:
resource → `CommandWrapperBuilder` (action + entity + URL) → `PortfolioCommandSourceWritePlatformService`
→ permission check → maker-checker check (queue vs execute) → handler (annotated
`@CommandType(entity=..., action=...)`) → result envelope; the command source row lands in
`m_portfolio_command_source` (= `/v1/audits`). Idempotency keys dedupe at this layer. This is why:
- every write has an `actionName`/`entityName` in audits,
- maker-checker can intercept anything,
- replayed idempotent calls return stored results.

## Business events (reliable event framework)

Domain code raises typed events (`ClientCreateBusinessEvent`, `LoanApprovedBusinessEvent`,
`LoanTransactionMakeRepaymentPostBusinessEvent`, …). With `FINERACT_EXTERNAL_EVENTS_ENABLED=true`
they serialize to Avro (schemas in `fineract-avro-schemas`) into an **outbox table**
(`m_external_event`) in the same DB transaction, then a purger/publisher ships them to
JMS/Kafka — at-least-once, transactional with the business change. Per-type on/off:
`PUT /v1/externalevents/configuration`. Consumers: read the Avro schemas module for payload
contracts. (Contrast with legacy `/v1/hooks` webhooks: fire-and-forget.)

## COB architecture

`fineract-cob` runs per-tenant Spring Batch jobs over chunked loan partitions; **business steps**
(DB-registered, orderable via `GET/PUT /v1/jobs/LOAN_CLOSE_OF_BUSINESS/steps`) execute per loan.
Custom steps implement `LoanCOBBusinessStep` and register via changelog. Remote partitioning
(manager/worker instances) coordinates over the message broker. Loans get soft-locked
(`m_loan_account_locks`) during processing; the inline-COB API processes named loans synchronously.

## Custom modules (`custom/`) — extend without forking

Documented pattern (docs chapter `custom`): create `custom/<company>/<module>/{starter,core,service}`
Gradle projects; implement replacements or additions (services via Spring auto-configuration
`@ConditionalOnMissingBean` overrides, new REST resources, Liquibase `custom-changelog`, batch jobs,
COB business steps, loan transaction processors). Build produces a merged deployable
(`:custom:docker:jibDockerBuild` style targets). Database migrations for custom modules run from
their own changelog namespace. This is the sanctioned way to add company-specific behaviour.

## Persistence conventions

- Tables prefixed `m_` (master data), `acc_` (accounting), `x_` (extensions/datatables registry),
  `job`/batch tables for scheduler state.
- Datatables create REAL tables named as given — they live beside core tables in the tenant schema.
- Never write to tenant schemas directly in production; the command pipeline + audits are the
  contract. (Dev debugging: read-only queries are fine.)

## Request lifecycle (debugging map)

1. TLS/8443 → Jersey resource (`*ApiResource` classes in modules)
2. `Fineract-Platform-TenantId` filter resolves tenant → thread-local context + datasource
3. Spring Security (basic/OAuth/2FA) → `AppUser` loaded with permissions
4. Resource delegates: reads → `*ReadPlatformService` (often plain JDBC row mappers);
   writes → command pipeline (above)
5. JSON in/out via Google Gson (note: NOT Jackson for API payload parsing in most paths — date
   handling quirks originate here)

## Where to look in source for X

| Question | Location |
|---|---|
| What does endpoint X actually do? | `grep -r "Path(\"/x\")" fineract-*/src` → `*ApiResource` → handler/service |
| Validation rule / error code | `grep -r "<userMessageGlobalisationCode>"` — codes map to `DataValidatorBuilder` chains |
| Job implementation | `*JobRegisterService` / quartz config in `fineract-provider`, steps in `fineract-cob` or domain modules |
| Event payload | `fineract-avro-schemas/src/main/avro/**` |
| DB column meaning | Liquibase changelogs in `fineract-provider/src/main/resources/db/changelog/tenant/**` |
| API usage examples | `integration-tests/src/test/java/**` (REST-Assured, exhaustive) |
