#!/usr/bin/env python3
import csv
import hashlib
import json
import os
import re
import sys
from pathlib import Path

LEVELS = {"impossible", "check", "test", "hook", "prose", "memory"}
COLUMNS = ["id", "rule", "level", "enforcer", "proof"]
RULES = ".claude/rules/dot-agent.md"
STAMP = re.compile(r"<!-- dot-agent \S+ sha256:([0-9a-f]{64}) .*-->")
SCHEMA = Path(__file__).resolve().parent / "schemas/launchpad.schema.json"
CI_RUN = re.compile(r"""^\s*(-\s+)?(run:\s*)?["']?(bash\s+)?(\./)?scripts/check --tests["']?\s*(#.*)?$""", re.M)
TYPES = {"object": dict, "array": list, "string": str, "boolean": bool}


def hand_edited(text):
    head, _, body = text.partition("\n")
    stamp = STAMP.fullmatch(head)
    return not stamp or stamp[1] != hashlib.sha256(body.encode()).hexdigest()


def errors(value, schema, at="launchpad.json"):
    if "const" in schema and (value != schema["const"] or type(value) is not type(schema["const"])):
        return [f"{at}: must be {schema['const']!r}"]
    if "enum" in schema and value not in schema["enum"]:
        return [f"{at}: must be one of {', '.join(schema['enum'])}"]
    kind = TYPES.get(schema.get("type"))
    if kind and not isinstance(value, kind):
        return [f"{at}: must be a {schema['type']}"]
    found = []
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0) or not re.search(schema.get("pattern", ""), value):
            found.append(f"{at}: {value!r} is not a valid value")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            found.append(f"{at}: needs at least {schema['minItems']} item(s)")
        if schema.get("uniqueItems") and len(set(map(json.dumps, value))) < len(value):
            found.append(f"{at}: items repeat")
        for index, item in enumerate(value):
            found += errors(item, schema.get("items", {}), f"{at}[{index}]")
    if isinstance(value, dict):
        found += [f"{at}: missing {key}" for key in schema.get("required", []) if key not in value]
        for key, item in value.items():
            sub = schema.get("properties", {}).get(key, schema.get("additionalProperties", {}))
            found += errors(item, sub if isinstance(sub, dict) else {}, f"{at}.{key}")
    return found


def launchpad_errors(root):
    path = root / "launchpad.json"
    if not path.is_file():
        return []
    try:
        value = json.loads(path.read_text())
    except ValueError as error:
        return [f"launchpad.json: not JSON: {error}"]
    return errors(value, json.loads(SCHEMA.read_text()))


def checks(root: Path):
    def read(p):
        f = root / p
        return f.read_text(errors="ignore") if f.is_file() else None

    readme, agents, claude = read("README.md"), read("AGENTS.md"), read("CLAUDE.md")
    yield "README.md", readme is not None
    yield "AGENTS.md", agents is not None
    link = root / "CLAUDE.md"
    yield "CLAUDE.md is @AGENTS.md or a symlink to it", (claude or "").strip() == "@AGENTS.md" or (
        link.is_symlink() and link.resolve() == (root / "AGENTS.md").resolve())
    yield "AGENTS.md where-to-look links GLOSSARY, CONSTRAINTS, VERIFY, scripts/check", bool(agents) and all(
        t in agents for t in ("GLOSSARY.md", "CONSTRAINTS.tsv", "VERIFY.md", "scripts/check"))
    tsv = read("CONSTRAINTS.tsv")
    ok = False
    if tsv:
        rows = list(csv.reader(tsv.splitlines(), delimiter="\t"))
        head, body = (rows[0] if rows else []), [r for r in rows[1:] if r]
        ok = head[:5] == COLUMNS and all(
            len(r) >= 3 and r[2] in LEVELS and (r[2] in {"prose", "memory"} or (len(r) >= 5 and r[4].strip()))
            for r in body)
    yield "CONSTRAINTS.tsv: columns, levels, proof above prose", ok
    check = root / "scripts/check"
    yield "scripts/check executable", check.is_file() and os.access(check, os.X_OK)
    yield "GLOSSARY.md", read("GLOSSARY.md") is not None
    yield "VERSION + RELEASES.md", read("VERSION") is not None and read("RELEASES.md") is not None
    verify = read("VERIFY.md")
    yield "VERIFY.md", verify is not None
    yield "VERIFY.md names an outside judge or 'no judge yet'", bool(verify) and bool(re.search(r"judge", verify, re.I))
    yield "private-boundary check", (root / "scripts/private-boundary.py").is_file()
    yield "template version stamped", bool(re.search(r"template[ -]?(version)?\s*\d", agents or "", re.I))
    wf = root / ".github/workflows"
    ci = list(wf.glob("*.y*ml")) if wf.is_dir() else []
    yield "CI runs scripts/check --tests", any(CI_RUN.search(p.read_text()) for p in ci)
    rules = read(RULES)
    yield f"{RULES} stamp matches its body (or no file)", rules is None or not hand_edited(rules)
    yield "launchpad.json matches template/schemas/launchpad.schema.json (or no file)", not launchpad_errors(root)


def main():
    as_json = "--json" in sys.argv
    repos = [a for a in sys.argv[1:] if a != "--json"]
    if not repos or {"-h", "--help"} & set(repos):
        print("usage: conform.py <repo>... [--json]   checks the 15 template items", file=sys.stderr)
        sys.exit(2)
    report, failed = [], False
    for arg in repos:
        root = Path(arg).expanduser().resolve()
        results = list(checks(root))
        passed = sum(ok for _, ok in results)
        report.append({"repo": str(root), "passed": passed, "total": len(results),
                       "checks": {name: ok for name, ok in results}})
        failed |= passed != len(results)
    if as_json:
        print(json.dumps(report, indent=2))
    else:
        for r in report:
            print(f"{Path(r['repo']).name}: {'PASS' if r['passed'] == r['total'] else 'FAIL'} {r['passed']}/{r['total']}")
            for name, ok in r["checks"].items():
                print(f"  {'ok  ' if ok else 'MISS'} {name}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
