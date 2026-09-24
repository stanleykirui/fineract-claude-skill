# Users, Roles, Permissions, Maker-Checker (Fineract 1.14.0)

Tags: `Users`, `Roles`, `Permissions`, `Password preferences`, `Maker Checker (or 4-eye)
functionality`, `Fetch authenticated user details`, `Two Factor`, `Self User`, `Self User Details`,
`Self Service Registration`.

## Users

`/v1/users`: `{username, firstname, lastname, email, officeId, roles: [roleId...], staffId?,
sendPasswordToEmail, password?/repeatPassword?, passwordNeverExpires?, isSelfServiceUser?,
clients?: [clientId...] (self-service link)}`.
- Office scoping: a user sees their office + sub-offices.
- `POST /v1/users/{id}?command=` none — updates via PUT; `DELETE` deactivates.
- Own details: `GET /v1/userdetails` (roles + permissions of the caller — use this to drive UI
  RBAC).

## Roles & permissions

- `/v1/roles`: create `{name, description}`; `PUT /v1/roles/{id}/permissions`
  `{"permissions": {"READ_CLIENT": true, ...}}` toggles grants;
  commands `POST /v1/roles/{id}?command=enable|disable`.
- `/v1/permissions`: `GET` catalogue (hundreds). Code shape: `ACTION_ENTITY` e.g. `READ_LOAN`,
  `CREATE_CLIENT`, `APPROVE_LOAN`, `DISBURSE_LOAN`, plus special `ALL_FUNCTIONS`,
  `ALL_FUNCTIONS_READ`. Grouping field: `grouping` (e.g. portfolio, transaction_loan,
  organisation).
- Checker-relevant variants are the same code with maker-checker enabled (below), not separate
  codes; `_CHECKER` appears in the checker inbox filter dimension.

## Maker-checker (4-eye)

- Enable globally: global configuration `maker-checker` = true, then per-permission:
  `PUT /v1/permissions` `{"permissions": {"CREATE_CLIENT": true}}` — this payload toggles each
  permission's **maker-checker flag** (not the grant!).
- Flow: maker's write returns `commandId` (202-style queuing; no resourceId). Pending commands:
  `GET /v1/makercheckers?actionName=&entityName=&resourceId=&makerId=&makerDateTimeFrom=...`.
  Checker acts: `POST /v1/makercheckers/{auditId}?command=approve|reject`;
  `DELETE /v1/makercheckers/{auditId}` deletes the queued command.
- Checker inbox template (`/v1/makercheckers/searchtemplate`) lists action/entity names available.
- A user with `CHECKER_SUPER_USER`-like broad grants or the specific checker capability approves;
  the **maker cannot check their own command** unless config allows (`enable-same-maker-checker`).
- Audit trail of ALL commands (executed + queued): `/v1/audits` (`?actionName=&entityName=&makerId=
  &checkerId=&status=`) — every write in Fineract lands here with its JSON payload.

## Password policy

`/v1/passwordpreferences` — choose active validation policy (`GET .../template` lists policies).
User password reset: `PUT /v1/users/{id}` with `password`/`repeatPassword`, or
`sendPasswordToEmail` at creation.

## Two-factor (when `FINERACT_SECURITY_2FA_ENABLED=true`)

Tag `Two Factor`: `GET /v1/twofactor` delivery methods → `POST /v1/twofactor` (request OTP via
email/SMS) → `POST /v1/twofactor/validate` → returns an access token sent thereafter as header
`Fineract-Platform-TFA-Token`. Bypass permission: `BYPASS_TWOFACTOR`. Config keys under
`/v1/twofactor/configure`.

## Self-service users & registration

- Staff-created: `POST /v1/users` with `isSelfServiceUser: true` + `clients: [id]`.
- Self-registration (tag Self Service Registration): `POST /v1/self/registration` `{accountNumber,
  firstName, lastName, mobileNumber/email, authenticationMode: "email"|"mobile"}` sends a token,
  then `POST /v1/self/registration/user` `{requestId, authenticationToken, username, password}`
  creates the login bound to the matching client.
- Self login: `POST /v1/self/authentication` `{username, password}`; self endpoints then enforce
  the client linkage (a self user only reads their own accounts).

## Recipes

- **Read-only auditor role**: role with `ALL_FUNCTIONS_READ` = true.
- **Teller role**: READ_CLIENT, READ_SAVINGSACCOUNT, DEPOSIT/WITHDRAWAL savings transaction
  permissions, READ_PAYMENTTYPE; no approvals.
- **Enforce 4-eye on money**: enable maker-checker flags on `DISBURSE_LOAN`,
  `REPAYMENT_LOAN`, savings `DEPOSIT`/`WITHDRAWAL`, `CREATE_JOURNALENTRY`.

## Gotchas

- `PUT /v1/permissions` toggles maker-checker flags; `PUT /v1/roles/{id}/permissions` toggles
  grants. Mixing these up silently "does nothing".
- Super-user role (id 1) with `ALL_FUNCTIONS` bypasses maker-checker queuing for convenience in
  dev — test 4-eye flows with a normal role.
- Username min length 5; default password policy rejects weak passwords with
  `validation.msg.user.password...` codes.
- 401 vs 403: 401 = bad credentials/no session; 403 = authenticated but missing the named
  permission (the error message includes the required code).
