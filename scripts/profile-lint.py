#!/usr/bin/env python3
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
failures: list[str] = []
NOT_PORTABLE = (
    (re.compile(r"/Users/"), "absolute /Users/ path is not portable"),
    (re.compile(r"bypassPermissions|skipDangerousModePermissionPrompt|dangerously|"
                r"approval_policy\s*=\s*\"never\"|danger-full-access"), "permission bypass in tracked config"),
    (re.compile(r"trust_level|hasTrustDialogAccepted|additionalDirectories|^\s*\[projects\.", re.M),
     "trusted-project allowlist in tracked config"),
)
SKILL_NAME = re.compile(r"[a-z0-9][a-z0-9-]*")
SETTINGS = re.compile(r"^(claude|codex)/[^/]+\.(json|toml)$")


def config_problems(relative: str, text: str) -> list[str]:
    checks = NOT_PORTABLE if SETTINGS.match(relative) else NOT_PORTABLE[:1]
    return [f"{relative}: {why}" for pattern, why in checks if pattern.search(text)]


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"  FAIL  {msg}")


def main() -> int:
    base = (ROOT / "AGENTS.md").read_text()
    profiles = {}
    for d in sorted((ROOT / "profiles").iterdir()):
        if not d.is_dir():
            continue
        markers = [l.strip() for l in (d / "markers").read_text().splitlines()
                   if l.strip()] if (d / "markers").is_file() else []
        if (d / "AGENTS.md").is_file() and not markers:
            fail(f"profiles/{d.name}: AGENTS.md fragment without a markers file")
        profiles[d.name] = markers

        path = d / "provided-skills"
        if path.is_file():
            for name in (l.strip() for l in path.read_text().splitlines() if l.strip()):
                if not SKILL_NAME.fullmatch(name):
                    fail(f"profiles/{d.name}/provided-skills: invalid skill name {name!r}")

    for name, markers in profiles.items():
        for marker in markers:
            if marker in base:
                fail(f"leak: {name} marker {marker!r} appears in shared AGENTS.md")
            for other in profiles:
                other_fragment = ROOT / "profiles" / other / "AGENTS.md"
                if other != name and other_fragment.is_file() \
                        and marker in other_fragment.read_text():
                    fail(f"leak: {name} marker {marker!r} appears in profiles/{other}/AGENTS.md")

    config_paths = [ROOT / "AGENTS.md", ROOT / "setup.sh"]
    for directory in ("claude", "codex", "profiles"):
        config_paths.extend(path for path in (ROOT / directory).rglob("*") if path.is_file())
    for path in sorted(config_paths):
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        for problem in config_problems(str(path.relative_to(ROOT)), text):
            fail(problem)

    if failures:
        print(f"profile-lint: FAIL ({len(failures)})")
        return 1
    print("profile-lint: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
