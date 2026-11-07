#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True

try:
    import tomllib
except ModuleNotFoundError:
    import toml_compat as tomllib


def dot_agent_home() -> Path:
    return Path(os.environ.get("DOT_AGENT_HOME", Path(__file__).resolve().parents[1])).expanduser()


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def summarize(value: object) -> str:
    text = value if isinstance(value, str) else json.dumps(value, sort_keys=True)
    return text if len(text) <= 72 else text[:69] + "..."


def walk(tracked: object, runtime: object, path: str, missing: list[str], extras: list[str]) -> None:
    if isinstance(tracked, dict) and isinstance(runtime, dict):
        for key, value in tracked.items():
            if key not in runtime:
                missing.append(f"{path}{key}")
            else:
                walk(value, runtime[key], f"{path}{key}.", missing, extras)
        for key in runtime:
            if key not in tracked:
                extras.append(f"{path}{key}")
        return
    if isinstance(tracked, list) and isinstance(runtime, list):
        label = path.rstrip(".")
        for item in tracked:
            if item not in runtime:
                missing.append(f"{label}[] {summarize(item)}")
        for item in runtime:
            if item not in tracked:
                extras.append(f"{label}[] {summarize(item)}")
        return
    if tracked != runtime:
        missing.append(f"{path.rstrip('.')} expected {summarize(tracked)}")
        extras.append(f"{path.rstrip('.')} (runtime override: {summarize(runtime)})")


def load_toml(path: Path) -> object:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def audit_config(label: str, tracked_path: Path, runtime_path: Path) -> bool:
    print(f"{label} Drift Audit")

    for required in (tracked_path, runtime_path):
        if not required.is_file():
            print(f"WARN: missing config file: {required}")
            return False

    try:
        tracked = load_toml(tracked_path)
        runtime = load_toml(runtime_path)
    except Exception as error:
        print(f"WARN: could not read config: {error}")
        return False

    missing: list[str] = []
    extras: list[str] = []
    walk(tracked, runtime, "", missing, extras)

    for entry in missing:
        print(f"WARN: tracked but not live in runtime: {entry}")
    for entry in extras:
        print(f"INFO: runtime-only (local override or stale removal): {entry}")

    if missing:
        print(f"WARN: {len(missing)} tracked config item(s) not live; run ~/.dot-agent/setup.sh")
        return False

    print(f"OK: all tracked {label.lower()} entries are live in runtime ({len(extras)} runtime-local entries).")
    return True


def main() -> int:
    tracked = dot_agent_home() / "codex" / "config.toml"
    return 0 if audit_config("Codex Config", tracked, codex_home() / "config.toml") else 1


if __name__ == "__main__":
    sys.exit(main())
