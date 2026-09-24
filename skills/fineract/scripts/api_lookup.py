#!/usr/bin/env python3
"""Look up Apache Fineract 1.14.0 API endpoints, schemas, and legacy docs.

Data files (in ../api/ relative to this script):
  fineract-1.14.0.openapi.json  - OpenAPI 3.0 spec captured from a running 1.14.0 instance
  apiLive-1.14.0.htm            - legacy narrative API reference (744 anchored sections)

Usage:
  api_lookup.py <keyword>                 search operations (path/summary/tag/operationId)
  api_lookup.py --op "POST /v1/loans"     full detail for one operation (also accepts operationId)
  api_lookup.py --schema <Name>           resolved fields of a component schema (fuzzy match)
  api_lookup.py --tag "Loan Products"     all operations under a tag
  api_lookup.py --tags [filter]           list tags
  api_lookup.py --legacy <keyword>        extract matching section(s) from the legacy doc as text
  api_lookup.py --legacy-list [filter]    list legacy doc anchors
Options: --limit N (default 40), --depth N (schema resolve depth, default 1)

Python 3.8+, stdlib only.
"""
import argparse
import json
import re
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parent.parent / "api"
SPEC_FILE = API_DIR / "fineract-1.14.0.openapi.json"
LEGACY_FILE = API_DIR / "apiLive-1.14.0.htm"
METHODS = ("get", "post", "put", "delete", "patch", "options", "head")


def load_spec():
    if not SPEC_FILE.exists():
        sys.exit(f"spec not found: {SPEC_FILE}")
    return json.loads(SPEC_FILE.read_text(encoding="utf-8"))


def iter_ops(spec):
    for path, item in spec.get("paths", {}).items():
        for method in METHODS:
            op = item.get(method)
            if isinstance(op, dict):
                yield method.upper(), path, op


def one_line(text, width=110):
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= width else text[: width - 3] + "..."


def ref_name(ref):
    return ref.rsplit("/", 1)[-1]


def type_of(schema, spec, depth=0, max_depth=1):
    """Compact human-readable type for a schema node."""
    if not isinstance(schema, dict):
        return "?"
    if "$ref" in schema:
        name = ref_name(schema["$ref"])
        if depth < max_depth:
            target = spec["components"]["schemas"].get(name)
            if target and target.get("type") == "object":
                return name
        return name
    t = schema.get("type")
    if t == "array":
        return f"array<{type_of(schema.get('items', {}), spec, depth, max_depth)}>"
    if t == "object" and "additionalProperties" in schema:
        return f"map<string,{type_of(schema['additionalProperties'], spec, depth, max_depth)}>"
    fmt = schema.get("format")
    out = t or "object"
    if fmt:
        out += f"({fmt})"
    if schema.get("enum"):
        out += " enum[" + ",".join(str(e) for e in schema["enum"][:6]) + "]"
    return out


def print_schema(name, spec, depth=1, indent=""):
    schemas = spec.get("components", {}).get("schemas", {})
    schema = schemas.get(name)
    if schema is None:
        matches = [n for n in schemas if name.lower() in n.lower()]
        if not matches:
            print(f"no schema matching '{name}'")
            return
        if len(matches) > 1 and name not in matches:
            print(f"'{name}' matches {len(matches)} schemas:")
            for m in sorted(matches)[:40]:
                print(f"  {m}")
            return
        name = matches[0] if name not in matches else name
        schema = schemas[name]
    print(f"{indent}{name}:")
    _print_schema_body(schema, spec, depth, indent + "  ", seen={name})


def _print_schema_body(schema, spec, depth, indent, seen):
    if "$ref" in schema:
        print(f"{indent}$ref: {ref_name(schema['$ref'])}")
        return
    required = set(schema.get("required", []))
    props = schema.get("properties", {})
    if not props:
        print(f"{indent}(type: {type_of(schema, spec)})")
        return
    for prop, node in props.items():
        star = "*" if prop in required else ""
        desc = one_line(node.get("description", ""), 60) if isinstance(node, dict) else ""
        tail = f"  # {desc}" if desc else ""
        tname = type_of(node, spec, 0, 0)
        print(f"{indent}{prop}{star}: {tname}{tail}")
        # expand nested object refs one level if depth allows
        if depth > 0 and isinstance(node, dict):
            target = None
            if "$ref" in node:
                target = spec["components"]["schemas"].get(ref_name(node["$ref"]))
                tkey = ref_name(node["$ref"])
            elif node.get("type") == "array" and "$ref" in node.get("items", {}):
                tkey = ref_name(node["items"]["$ref"])
                target = spec["components"]["schemas"].get(tkey)
            else:
                target, tkey = None, None
            if target and tkey not in seen and target.get("properties"):
                seen.add(tkey)
                _print_schema_body(target, spec, depth - 1, indent + "  ", seen)


def cmd_search(query, spec, limit, tag=None):
    q = query.lower() if query else ""
    rows = []
    for method, path, op in iter_ops(spec):
        tags = op.get("tags", [])
        if tag and not any(tag.lower() == t.lower() for t in tags):
            continue
        hay = " ".join([path, op.get("summary", ""), op.get("operationId", ""), " ".join(tags)]).lower()
        if q and q not in hay:
            continue
        rows.append((method, path, one_line(op.get("summary", ""), 70), tags[0] if tags else ""))
    rows.sort(key=lambda r: (r[1], r[0]))
    for method, path, summary, t in rows[:limit]:
        print(f"{method:6} {path:60} {summary}  [{t}]")
    if len(rows) > limit:
        print(f"... {len(rows) - limit} more (use --limit or narrow the query)")
    if not rows:
        print(f"no operations matching '{query}'" + (f" in tag '{tag}'" if tag else ""))


def cmd_op(target, spec, depth):
    target_norm = target.strip()
    m = re.match(r"^(GET|POST|PUT|DELETE|PATCH|OPTIONS|HEAD)\s+(.+)$", target_norm, re.I)
    found = None
    for method, path, op in iter_ops(spec):
        if m:
            if method == m.group(1).upper() and path.rstrip("/") == m.group(2).strip().rstrip("/"):
                found = (method, path, op)
                break
        elif op.get("operationId", "").lower() == target_norm.lower():
            found = (method, path, op)
            break
    if not found:
        print(f"operation not found: '{target}' — try a search first:")
        cmd_search(target_norm.split()[-1].strip("/").split("/")[-1], spec, 15)
        return
    method, path, op = found
    print(f"{method} {path}")
    if op.get("summary"):
        print(f"summary: {op['summary']}")
    if op.get("tags"):
        print(f"tag: {', '.join(op['tags'])}")
    if op.get("operationId"):
        print(f"operationId: {op['operationId']}")
    if op.get("description"):
        print("description:")
        for line in re.sub(r"\n{3,}", "\n\n", op["description"].strip()).splitlines():
            print(f"  {line}")
    params = op.get("parameters", [])
    if params:
        print("parameters:")
        for p in params:
            req = "*" if p.get("required") else ""
            print(f"  {p.get('name')}{req} ({p.get('in')}): {type_of(p.get('schema', {}), spec)}"
                  + (f"  # {one_line(p.get('description',''), 60)}" if p.get("description") else ""))
    body = op.get("requestBody", {})
    content = body.get("content", {})
    for ctype, media in content.items():
        schema = media.get("schema", {})
        print(f"requestBody ({ctype}):")
        if "$ref" in schema:
            print_schema(ref_name(schema["$ref"]), spec, depth, "  ")
        else:
            _print_schema_body(schema, spec, depth, "  ", set())
    for code, resp in op.get("responses", {}).items():
        rschema = ""
        for media in resp.get("content", {}).values():
            s = media.get("schema", {})
            rschema = type_of(s, spec, 0, 0)
            break
        print(f"response {code}: {rschema}  {one_line(resp.get('description',''), 60)}")
    if depth > 0:
        for code, resp in op.get("responses", {}).items():
            if not code.startswith("2"):
                continue
            for media in resp.get("content", {}).values():
                s = media.get("schema", {})
                name = ref_name(s["$ref"]) if "$ref" in s else (
                    ref_name(s["items"]["$ref"]) if s.get("type") == "array" and "$ref" in s.get("items", {}) else None)
                if name:
                    print(f"response schema:")
                    print_schema(name, spec, depth - 1, "  ")
                break
            break


def cmd_tags(spec, filt, limit):
    counts = {}
    for _, _, op in iter_ops(spec):
        for t in op.get("tags", []):
            counts[t] = counts.get(t, 0) + 1
    for t in sorted(counts):
        if filt and filt.lower() not in t.lower():
            continue
        print(f"{counts[t]:4}  {t}")


ANCHOR_RE = re.compile(r'<a id="([^"]+)" name="[^"]*" class="old-syle-anchor">')


def strip_html(fragment):
    fragment = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", fragment, flags=re.S | re.I)
    fragment = re.sub(r"</?(tr|table|div|p|h[1-6]|li|ul|ol|br)[^>]*>", "\n", fragment, flags=re.I)
    fragment = re.sub(r"</td>\s*<td[^>]*>", " | ", fragment, flags=re.I)
    fragment = re.sub(r"<[^>]+>", "", fragment)
    fragment = fragment.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in fragment.splitlines()]
    out, blank = [], 0
    for ln in lines:
        if ln:
            out.append(ln)
            blank = 0
        else:
            blank += 1
            if blank == 1:
                out.append("")
    return "\n".join(out).strip()


def legacy_sections():
    if not LEGACY_FILE.exists():
        sys.exit(f"legacy doc not found: {LEGACY_FILE}")
    html = LEGACY_FILE.read_text(encoding="utf-8", errors="replace")
    anchors = list(ANCHOR_RE.finditer(html))
    for i, mt in enumerate(anchors):
        end = anchors[i + 1].start() if i + 1 < len(anchors) else len(html)
        yield mt.group(1), html[mt.end():end]


def cmd_legacy(key, limit_chars=12000):
    key_l = key.lower()
    exact, partial = [], []
    for anchor, body in legacy_sections():
        if anchor.lower() == key_l:
            exact.append((anchor, body))
        elif key_l in anchor.lower():
            partial.append((anchor, body))
    picks = exact or partial
    if not picks:
        print(f"no legacy section matching '{key}'. Anchors containing similar text:")
        cmd_legacy_list(key[:4])
        return
    if len(picks) > 3:
        print(f"'{key}' matches {len(picks)} sections — pick one anchor:")
        for anchor, _ in picks:
            print(f"  {anchor}")
        return
    for anchor, body in picks:
        text = strip_html(body)
        print(f"===== [{anchor}] =====")
        print(text[:limit_chars])
        if len(text) > limit_chars:
            print(f"... (truncated at {limit_chars} chars — section is {len(text)} chars)")


def cmd_legacy_list(filt):
    names = [a for a, _ in legacy_sections()]
    for n in names:
        if not filt or filt.lower() in n.lower():
            print(n)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query", nargs="?", help="keyword search over operations")
    ap.add_argument("--op", help='operation detail: "METHOD /v1/path" or operationId')
    ap.add_argument("--schema", help="show a component schema (fuzzy name match)")
    ap.add_argument("--tag", help="filter/list operations by tag")
    ap.add_argument("--tags", nargs="?", const="", default=None, help="list tags (optional filter)")
    ap.add_argument("--legacy", help="extract legacy doc section(s) by anchor/keyword")
    ap.add_argument("--legacy-list", nargs="?", const="", default=None, help="list legacy anchors (optional filter)")
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--depth", type=int, default=1, help="schema resolve depth")
    args = ap.parse_args()

    if args.legacy_list is not None:
        cmd_legacy_list(args.legacy_list)
        return
    if args.legacy:
        cmd_legacy(args.legacy)
        return
    spec = load_spec()
    if args.tags is not None:
        cmd_tags(spec, args.tags, args.limit)
    elif args.schema:
        print_schema(args.schema, spec, args.depth)
    elif args.op:
        cmd_op(args.op, spec, args.depth)
    elif args.query or args.tag:
        cmd_search(args.query or "", spec, args.limit, args.tag)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
