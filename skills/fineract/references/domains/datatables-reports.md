# Data Tables, Codes, Reports, Audits, Documents (Fineract 1.14.0)

Tags: `Data Tables` (16 ops), `Entity Data Table`, `Entity Field Configuration`, `Codes`,
`Code Values`, `Reports`, `Run Reports`, `Report Mailing Jobs`, `List Report Mailing Job History`,
`Audits`, `AdhocQuery Api`, `Bulk Import`, `Documents`, `User Generated Documents`, `Notes`,
`Survey`, `Spm-Surveys`, `SPM API - LookUp Table`, `Score Card`, `Poverty Line`, `Likelihood`,
`Mix Report/Mapping/Taxonomy`.

## Data tables (custom fields without code changes)

Extend any core entity (`m_client`, `m_loan`, `m_savings_account`, `m_group`, `m_office`…) with
custom tables:

- `POST /v1/datatables` `{datatableName, apptableName: "m_client", multiRow: false, columns:
  [{name, type: String|Number|Decimal|Boolean|Date|DateTime|Text|Dropdown, length?, mandatory?,
  code? (for Dropdown → code values), unique?, indexed?}]}` — creates a real SQL table
  (`x_registered_table` registry).
- `PUT /v1/datatables/{datatableName}` alter · `DELETE` drop ·
  `POST /v1/datatables/register/{datatable}/{apptable}` / `.../deregister/...`.
- Row CRUD: `POST /v1/datatables/{datatable}/{apptableId}` insert (one-row tables upsert),
  `GET` read (`?genericResultSet=true` for column metadata form-building),
  `PUT /v1/datatables/{datatable}/{apptableId}` (one-row) or `.../{datatableId}` (multi-row),
  `DELETE` variants likewise.
- Query without id: `GET /v1/datatables/{datatable}/query?columnFilter=&valueFilter=&resultColumns=`.
- Inline at client creation: `datatables: [{registeredTableName, data: {...}}]` in `POST /v1/clients`.
- **Entity datatable checks** (`/v1/entityDatatableChecks`): force a datatable to be filled at an
  entity lifecycle point (`status: create|approve|activate|disburse...` per entity) — validation
  gates.

## Codes & code values (managed dropdowns)

- `/v1/codes` — system + custom lookup lists; `/v1/codes/{codeId}/codevalues` CRUD values
  `{name, position, description, isActive}`.
- System codes drive dropdowns like `Customer Identifier` (client identifier types), `Gender`,
  `ClientType`, `ClientClassification`, `LoanCollateral`, `LoanRescheduleReason`, `GROUPROLE`,
  `AddressType`, etc. Add values, don't rename system codes.

## Reports

Fineract ships table/chart/pentaho report definitions in-DB:

- Catalogue CRUD: `/v1/reports` `{reportName, reportType: Table|Chart|Pentaho|SMS, reportSubType?,
  reportSql? (with ${param} placeholders), reportParameters: [{parameterId, reportParameterName}],
  useReport: true}`. Self-service-visible reports: flag `isSelfServiceUserReport`.
- Execute: `GET /v1/runreports/{reportName}?R_officeId=1&R_loanOfficerId=-1&...` — `R_`-prefixed
  params; `&parameterType=true` runs a parameter (dropdown) query;
  `&exportCSV=true` CSV, Pentaho adds `&output-type=PDF|XLS|XLSX|CSV`. Table reports return the
  generic resultset `{columnHeaders, data}`.
- Report parameters come from the FullParameterList system report; standard params: R_officeId,
  R_loanOfficerId, R_currencyId, R_fundId, R_loanProductId, R_startDate, R_endDate...
- **Report mailing jobs** (`/v1/reportmailingjobs`): schedule a report to email recipients on a
  recurrence; history via `/v1/reportmailingjobs/{id}/runhistory` (tag List Report Mailing Job
  History).
- **AdhocQuery** (`/v1/adhocquery`): saved SQL snippets run by the "Generate AdhocClient Schedule"
  machinery (email/reporting utility; superuser realm).

## Audits

`/v1/audits?actionName=&entityName=&resourceId=&makerId=&checkerId=&makerDateTimeFrom=&makerDateTimeTo=
&status=&officeId=&paged=true` — every command (executed, queued, rejected) with its full JSON
payload (`GET /v1/audits/{auditId}`). This is the forensic log for "who changed what when".
`/v1/audits/searchtemplate` lists filterable action/entity names.

## Documents & generated documents

- Attachments on any entity: `/v1/{entityType}/{entityId}/documents` (multipart `file`, `name`,
  `description`); download via `.../documents/{documentId}/attachment`.
- **User generated documents** (tag User Generated Documents, `/v1/templates`): mustache-style
  document templates (entity: client/loan; type: Document/E-Mail/SMS) rendered with entity data —
  `POST /v1/templates/{templateId}` with `{...entity ids...}` returns merged HTML.

## Bulk import (spreadsheet migration)

`/v1/{entity}/downloadtemplate` (e.g. `/v1/clients/downloadtemplate?officeId=&staffId=`) → XLS
template; fill; `POST /v1/{entity}/uploadtemplate` multipart → import summary at
`/v1/imports?entityType=...` (tag Bulk Import). Supported: offices, clients, groups, centers,
staff, users, loans, savings, FD/RD accounts, share accounts, GL accounts, journal entries,
chart of accounts, guarantors...

## SPM / surveys (social performance)

- Simple field surveys: `/v1/surveys` + `POST /v1/surveys/scorecards/...` (Score Card tag) — e.g.
  PPI poverty scorecards; lookup tables `/v1/surveys/{surveyId}/lookuptables`; poverty
  line/likelihood tags support PPI scoring.
- Full SPM framework endpoints: `/v1/surveys` (Spm-Surveys tag) with components/questions.
- MIX reporting (microfinance industry XBRL): `/v1/mixreport`, `/v1/mixmapping`,
  `/v1/mixtaxonomy`.

## Gotchas

- Datatable names are the actual SQL table names — no spaces; convention `<entity> <purpose>` was
  historic, prefer snake_case; renaming via PUT rewrites the table.
- `genericResultSet=true` responses wrap values as strings with column metadata — parse types from
  `columnHeaders`.
- Report SQL runs against the tenant schema with the API user's office scoping only if the SQL
  includes the standard office-hierarchy join snippets (copy from stock reports).
- Pentaho reports need the plugin/runtime present in the deployment; Table reports are pure SQL and
  always work.
- Audits grow fast; filter server-side, never pull unpaged.
