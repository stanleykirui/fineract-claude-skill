# fineract-claude-skill

A [Claude Code](https://claude.com/claude-code) **skill** for [Apache Fineract](https://fineract.apache.org/)
**1.14.0** — the open-source core banking / microfinance platform. It gives Claude grounded, version-pinned
knowledge of:

- **The complete REST API** — an OpenAPI 3.0 spec captured from a live 1.14.0 build
  (**563 paths · 879 operations · 1,476 schemas · 151 tags**) plus the legacy narrative API reference,
  queried on demand through a zero-dependency lookup script (no megabytes ever loaded into context).
- **Usage conventions** — tenancy header, auth, `dateFormat`/`locale`, the `?command=` pattern,
  idempotency keys, maker-checker, batch API, error envelope, pagination, templates.
- **Admin & operations** — multi-tenant provisioning (registry DB, encrypted tenant DB passwords),
  global configuration, scheduler jobs & Loan COB, security modes (Basic/OAuth2/2FA), instance types
  (read/write/batch), Docker deployment, troubleshooting.
- **Curated domain guides** — clients/groups/centers, loans (incl. progressive loans), savings & term
  deposits, shares, accounting/GL, organisation, users/roles/permissions, data tables & reports.

Everything lives in [`skills/fineract/`](skills/fineract/) — a self-contained folder you can drop into
any Claude setup.

## Install

### Option 1 — Claude Code plugin (recommended)

```
/plugin marketplace add stanleykirui/fineract-claude-skill
/plugin install fineract@fineract-claude-skill
```

### Option 2 — personal skill (all your projects)

```bash
git clone https://github.com/stanleykirui/fineract-claude-skill.git
# copy (or symlink/junction) the skill folder into your personal skills dir:
cp -r fineract-claude-skill/skills/fineract ~/.claude/skills/fineract
```

Windows (junction keeps the clone as the single source of truth):

```powershell
New-Item -ItemType Junction -Path "$env:USERPROFILE\.claude\skills\fineract" -Target "C:\path\to\fineract-claude-skill\skills\fineract"
```

### Option 3 — project skill (one repo)

```bash
cp -r fineract-claude-skill/skills/fineract <your-repo>/.claude/skills/fineract
```

The lookup script needs **Python 3.8+** (stdlib only — no pip installs).

## Use

Just ask Fineract questions in Claude Code — the skill triggers itself. Examples:

- *“How do I approve and disburse a loan through the Fineract API?”*
- *“What fields does POST /v1/clients accept?”*
- *“Why am I getting `Invalid tenant identifier`?”*
- *“How do I create a new tenant with its own database?”*
- *“Set up the Loan COB job on a separate batch instance.”*

You can also run the lookup tool directly:

```bash
python skills/fineract/scripts/api_lookup.py "loan transactions"
python skills/fineract/scripts/api_lookup.py --op "POST /v1/loans/{loanId}/transactions"
python skills/fineract/scripts/api_lookup.py --schema PostClientsRequest
python skills/fineract/scripts/api_lookup.py --legacy authenticationbasic
```

## Version pinning

Everything here describes **Apache Fineract 1.14.0**. Other versions differ (endpoints appear/disappear,
schemas change). To re-pin against your own build, replace the two files in `skills/fineract/api/`:

```bash
# 1. the OpenAPI spec, served by every running Fineract at:
curl -k https://localhost:8443/fineract-provider/fineract.json -o skills/fineract/api/fineract-<ver>.openapi.json
# 2. the legacy narrative doc, from the Fineract source tree:
#    fineract-provider/src/main/resources/static/legacy-docs/apiLive.htm
```

then update the two filename constants at the top of `scripts/api_lookup.py`.

## Site-specific overlay (optional)

`skills/fineract/references/local/` is **gitignored** (except its README). Put your own deployment
notes there — ports, hostnames, operational quirks — and the skill will consult them without them ever
being published. See [`skills/fineract/references/local/README.md`](skills/fineract/references/local/README.md).

## License

Apache License 2.0 — see [LICENSE](LICENSE). Includes documentation and API-specification content
derived from Apache Fineract (see [NOTICE](NOTICE)). Not affiliated with or endorsed by the Apache
Software Foundation.
