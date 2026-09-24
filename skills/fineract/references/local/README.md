# Local overlay (site-specific notes) — gitignored

Files in this directory (except this README) are **ignored by git** and never published. Put your
deployment-specific knowledge here — hostnames, port remaps, credential *pointers* (never actual
secrets), operational quirks, environment topology — and the skill will read them alongside the
public guides (`SKILL.md` routes here first when files exist).

Suggested file: `deployment-notes.md`. Example structure:

```markdown
# <Site> Fineract deployment notes
## Topology (hosts, ports, proxies)
## How we run it (compose files, overrides, restart procedure)
## Tenants in use
## Credentials — POINTERS only (e.g. "see <path-or-vault>", never values)
## Local quirks & gotchas
```

Keep secrets in your secret store; reference their location here.
