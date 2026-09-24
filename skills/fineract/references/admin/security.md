# Security Configuration & Hardening (Fineract 1.14.0)

## Authentication modes (boot-time, mutually configured)

| Mode | Enable | Notes |
|---|---|---|
| HTTP Basic (default ON) | `FINERACT_SECURITY_BASICAUTH_ENABLED=true` | Send `Authorization: Basic base64(user:pass)` on every call. `POST /v1/authentication` (JSON body creds) returns the user's `base64EncodedAuthenticationKey` + roles/permissions — a convenience login for building clients, not a session. |
| OAuth2 resource server | `FINERACT_SECURITY_BASICAUTH_ENABLED=false`, `FINERACT_SECURITY_OAUTH_ENABLED=true`, `FINERACT_SERVER_OAUTH_RESOURCE_URL=<issuer, e.g. http://keycloak:9000/realms/fineract>` | Bearer JWTs validated against the issuer; token `sub` must equal a Fineract username (map a username→sub claim in the IdP). Fineract still enforces its own role/permission model per user. |
| Two-factor (add-on) | `FINERACT_SECURITY_2FA_ENABLED=true` | After basic/OAuth login: `GET /v1/twofactor` (delivery options) → `POST /v1/twofactor?deliveryMethod=email|sms` sends OTP → `POST /v1/twofactor/validate?token=<otp>` → returns TFA access token, then send header `Fineract-Platform-TFA-Token` on every call. `BYPASS_TWOFACTOR` permission exempts a role. Email/SMS delivery needs external services configured. |

JVM-property equivalents: `-Dfineract.security.basicauth.enabled=...` etc.

## Keycloak quick pairing (from the official docs)

Realm `fineract`; client `community-app` (client-auth on, direct access grants for testing); create
user matching the Fineract username; add a mapper putting the username into the token `sub` claim.
Get a token from `<issuer>/protocol/openid-connect/token` (password or auth-code grant) and call
Fineract with `Authorization: Bearer <token>`.

## Transport & headers

- TLS on by default (`FINERACT_SERVER_SSL_ENABLED=true`, self-signed bundled cert on 8443) —
  terminate real TLS at a proxy or install a proper keystore
  (`server.ssl.key-store*` properties). HTTP mode (dev only): set SSL enabled false → port 8080.
- HSTS: `FINERACT_SECURITY_HSTS_ENABLED` (default false — enable behind real TLS).
- CORS: `FINERACT_SECURITY_CORS_*` (default allows `*` origin patterns with credentials — TIGHTEN
  in production: explicit origins list).

## Authorization model recap

Server-side permission checks on every operation (`ACTION_ENTITY` codes), office-hierarchy data
scoping, optional maker-checker queuing, full command audit (`/v1/audits`). Details:
`domains/users-roles-permissions.md`.

## Hardening checklist (production)

1. **Change `mifos`/`password`** immediately; create named per-human users; disable or repurpose
   the default superuser.
2. Roles = least privilege; use `ALL_FUNCTIONS_READ` for auditors, never `ALL_FUNCTIONS` for
   operators; enable maker-checker on money-moving + user-admin permissions.
3. Rotate DB creds; set a strong non-default **tenant master password**
   (`FINERACT_DEFAULT_TENANTDB_MASTER_PASSWORD`) — it encrypts every tenant DB password in the
   registry.
4. Do not expose 8443 directly: reverse proxy (real cert, rate limits, WAF), restrict actuator
   (`FINERACT_MANAGEMENT_ENDPOINT_WEB_EXPOSURE_INCLUDE` — drop `prometheus` from public nets).
5. Lock CORS origins; enable HSTS; keep `FINERACT_INSECURE_HTTP_CLIENT=false` (it disables outbound
   TLS verification — dev only).
6. Enforce 2FA for staff, or front with OAuth2/OIDC SSO.
7. Password policy via `/v1/passwordpreferences`; `passwordNeverExpires` only for service accounts.
8. Keep the scheduler node internal; `Instance mode` split lets you keep write/batch instances off
   the public edge entirely.
9. Watch `/v1/audits` (or ship business events) into your SIEM.
10. Self-service surface (`/v1/self/*`): expose ONLY these paths to end-customer apps if you can
    filter at the proxy.

## Secrets inventory (never in a client / repo)

Registry DB creds (`FINERACT_HIKARI_*`), tenant DB creds + master password, S3/SMTP/SMS/FCM external
service creds, OAuth client secrets, keystore passwords.
