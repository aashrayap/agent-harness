#!/usr/bin/env python3
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATTERN = re.compile(r"(\d+)\.(\d+)\.(\d+)")
RELEASE = re.compile(r"^## (\d+\.\d+\.\d+) ", re.M)


def parse(text: str, where: str) -> tuple[int, int, int]:
    match = PATTERN.fullmatch(text.strip())
    if not match:
        sys.exit(f"check-version-bump: {where} VERSION {text.strip()!r} is not MAJOR.MINOR.PATCH")
    return tuple(int(part) for part in match.groups())


def show(ref: str, name: str) -> str | None:
    shown = subprocess.run(["git", "-C", str(ROOT), "show", f"{ref}:{name}"],
                           capture_output=True, text=True)
    return shown.stdout if shown.returncode == 0 else None


def taken(refs: list[str]) -> dict[str, str]:
    found = {}
    for ref in refs:
        version = show(ref, "VERSION")
        if version is not None:
            found.setdefault(".".join(map(str, parse(version, ref))), f"VERSION on {ref}")
        for heading in RELEASE.findall(show(ref, "RELEASES.md") or ""):
            found.setdefault(heading, f"RELEASES.md on {ref}")
    return found


def main() -> int:
    base_ref = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    current = parse((ROOT / "VERSION").read_text(), "this branch's")
    version = ".".join(map(str, current))
    refs = list(dict.fromkeys([base_ref, "origin/main"]))
    bases = [parse(text, ref) for ref in refs if (text := show(ref, "VERSION")) is not None]
    if not bases:
        print(f"check-version-bump: {base_ref} has no VERSION yet; {version} starts it")
        return 0
    base = max(bases)
    if current <= base:
        print(f"check-version-bump: FAIL — bump VERSION above {'.'.join(map(str, base))} "
              f"(found {version})")
        return 1
    used = taken(refs)
    if version in used:
        print(f"check-version-bump: FAIL — {version} is already taken by {used[version]}; "
              "pick the next free version")
        return 1
    releases = ROOT / "RELEASES.md"
    text = releases.read_text(encoding="utf-8") if releases.is_file() else ""
    headings = RELEASE.findall(text)
    if version not in headings:
        print(f"check-version-bump: FAIL — add a '## {version} — YYYY-MM-DD' entry with New: and"
              " Setup: lines to RELEASES.md")
        return 1
    if headings.count(version) > 1:
        print(f"check-version-bump: FAIL — RELEASES.md has more than one '## {version}' entry")
        return 1
    print(f"check-version-bump: PASS {'.'.join(map(str, base))} -> {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
