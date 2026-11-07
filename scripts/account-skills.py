#!/usr/bin/env python3
import argparse
import hashlib
import io
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".claude/skills"
OUT = ROOT / "state/account-skills"
ALLOWED = ("name", "description", "license", "compatibility", "metadata", "allowed-tools")
QUOTED = ("name", "description")
NAME = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
MAX_NAME, MAX_DESCRIPTION = 64, 200
RESERVED = re.compile(r"anthropic|claude")
SKIP = {
}
EPOCH = (1980, 1, 1, 0, 0, 0)


def split_frontmatter(text):
    text = text.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md has no frontmatter")
    head, _, body = text[4:].partition("\n---\n")
    fields, key = {}, None
    for line in head.splitlines():
        match = re.match(r"([A-Za-z][\w-]*):(.*)$", line)
        if match and not line.startswith((" ", "\t")):
            key = match.group(1)
            fields[key] = match.group(2).strip()
        elif key:
            fields[key] += "\n" + line
    return fields, body


def scalar(value):
    value = value.strip()
    if value and value[0] in ">|":
        lines = [line.strip() for line in value.splitlines()[1:]]
        return (" " if value[0] == ">" else "\n").join(line for line in lines if line)
    if len(value) > 1 and value[0] == value[-1] == '"':
        return json.loads(value)
    if len(value) > 1 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    return value


def frontmatter(fields):
    return "---\n" + "".join(f"{key}: {json.dumps(value) if key in QUOTED else value}\n"
                              for key, value in fields.items()) + "---\n"


def convert(name, text):
    fields, body = split_frontmatter(text)
    dropped = [key for key in fields if key not in ALLOWED]
    kept = {key: scalar(value) if key in QUOTED else value for key, value in fields.items() if key in ALLOWED}
    hint = re.sub(r"[<>]", "", scalar(fields.get("argument-hint", ""))).strip()
    folded = f"{kept.get('description', '').rstrip()} Arguments: {hint}"
    if hint and len(folded) <= MAX_DESCRIPTION:
        kept["description"] = folded
    problems = []
    if kept.get("name") != name or not NAME.fullmatch(name) or len(name) > MAX_NAME or RESERVED.search(name):
        problems.append(f"name must be the folder name, lowercase-hyphen, at most {MAX_NAME} characters, "
                        "without anthropic or claude")
    description = kept.get("description", "")
    if not 0 < len(description) <= MAX_DESCRIPTION or re.search(r"[<>]", description):
        problems.append(f"description must be 1 to {MAX_DESCRIPTION} characters with no < or >, has {len(description)}")
    return frontmatter(kept) + body, {
        "dropped": dropped,
        "argument_hint_folded": kept.get("description") == folded,
        "loses_manual_only": fields.get("disable-model-invocation", "").strip().lower() == "true",
        "problems": problems,
    }


def committed(folder):
    listed = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", "--", str(folder)],
                            capture_output=True, text=True, check=True).stdout.split("\0")
    return sorted(ROOT / path for path in listed if path and (ROOT / path).is_file())


def archive(folder):
    name = folder.name
    report = None
    digest = hashlib.sha256()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipped:
        for path in committed(folder):
            data = path.read_bytes()
            if path.relative_to(folder).as_posix() == "SKILL.md":
                text, report = convert(name, data.decode("utf-8"))
                data = text.encode("utf-8")
            info = zipfile.ZipInfo(f"{name}/{path.relative_to(folder).as_posix()}", EPOCH)
            info.external_attr = (0o755 if path.stat().st_mode & 0o111 else 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zipped.writestr(info, data)
            digest.update(f"{info.filename}\0{info.external_attr}\0{len(data)}\0".encode() + data)
    if report is None:
        raise ValueError(f"{name} has no SKILL.md")
    return buffer.getvalue(), {"sha256": digest.hexdigest(), **report}


def build(source=SOURCE):
    version = (ROOT / "VERSION").read_text().strip()
    skills, skipped, zips = [], [], {}
    for folder in sorted(p for p in source.iterdir() if p.is_dir()):
        if folder.name in SKIP:
            skipped.append({"name": folder.name, "why": SKIP[folder.name]})
            continue
        data, report = archive(folder)
        zips[folder.name] = data
        skills.append({"name": folder.name, **report})
    return {"version": version, "skills": skills, "skipped": skipped}, zips


def write(out, manifest, zips):
    folder = out / manifest["version"]
    folder.mkdir(parents=True, exist_ok=True)
    for stale in folder.glob("*.zip"):
        if stale.stem not in zips:
            stale.unlink()
    for name, data in zips.items():
        (folder / f"{name}.zip").write_bytes(data)
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return folder


def check(out, manifest):
    uploaded_path = out / "uploaded.json"
    if not uploaded_path.is_file():
        return [f"nothing recorded as uploaded: upload the zips, then run `record`"]
    uploaded = json.loads(uploaded_path.read_text())
    found = []
    have = {skill["name"]: skill["sha256"] for skill in uploaded.get("skills", [])}
    for skill in manifest["skills"]:
        if skill["name"] not in have:
            found.append(f"{skill['name']} is not uploaded")
        elif have[skill["name"]] != skill["sha256"]:
            found.append(f"{skill['name']} changed since it was uploaded")
    found += [f"{name} was uploaded but is no longer built" for name in have
              if name not in {skill["name"] for skill in manifest["skills"]}]
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build claude.ai account-skill zips from dot-agent's skills and "
                                                 "say when the uploaded copies fall behind.")
    parser.add_argument("verb", choices=("build", "record", "check"),
                        help="build: write the zips; record: mark the built set as uploaded; check: compare them")
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    manifest, zips = build()
    problems = [f"{skill['name']}: {p}" for skill in manifest["skills"] for p in skill["problems"]]
    result = {"ok": not problems, "version": manifest["version"], "problems": problems}
    if args.verb == "build":
        result["folder"] = str(write(args.out, manifest, zips))
        result["skills"], result["skipped"] = manifest["skills"], manifest["skipped"]
    elif args.verb == "record":
        built = args.out / manifest["version"] / "manifest.json"
        if not built.is_file():
            result["problems"].append(f"no {built}: run build, upload its zips, then record")
        else:
            (args.out / "uploaded.json").write_text(built.read_text())
        result["ok"] = not result["problems"]
    else:
        result["behind"] = check(args.out, manifest)
        uploaded = args.out / "uploaded.json"
        if uploaded.is_file():
            result["uploaded_version"] = json.loads(uploaded.read_text()).get("version")
        result["ok"] = result["ok"] and not result["behind"]
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for line in result["problems"] + result.get("behind", []):
            print(f"ERROR: {line}")
        if args.verb == "build":
            print(f"wrote {len(zips)} zips to {result['folder']}; skipped {len(manifest['skipped'])}")
        print(f"account-skills {args.verb}: " + ("PASS" if result["ok"] else "FAIL"))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
