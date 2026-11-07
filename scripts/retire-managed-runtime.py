#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid

sys.dont_write_bytecode = True
from toml_edit import line_editable, strict_loads


DESCRIPTION = (
    "Converge exact harness ownership; never remove a runtime home or its history. "
    "The frozen manifest identifies former settings, files, skill payloads and LaunchAgents. "
    "Unknown contents stay in place. Every mutation has a recovery copy outside setup pruning. "
    "The only services touched are the retired LaunchAgents the manifest names; "
    "no credentials, conversations or external APIs are touched."
)
HOOK_HOME = "/.dot-agent/claude/hooks/"
CODEX_PINS = (("", "model"), ("", "model_reasoning_effort"), ("features", "multi_agent_v2"),
              ("agents", "default_subagent_model"), ("agents", "default_subagent_reasoning_effort"))
RETIRED_CLAUDE_ENV = ("CLAUDE_CODE_SUBAGENT_MODEL_FORCE",)
CLOUD_RULES = "**/.claude/rules/dot-agent.md"
PLUGIN_DIRS = "CLAUDE_CODE_PLUGIN_DIRS"


def locate(lines: list[str], table: str, key: str) -> tuple[int | None, int | None]:
    start = 0
    if table:
        start = next((i + 1 for i, line in enumerate(lines) if line.strip() == f"[{table}]"), None)
        if start is None:
            return None, None
    end = next((i for i in range(start, len(lines)) if lines[i].lstrip().startswith("[")), len(lines))
    pattern = re.compile(r"^\s*" + re.escape(key) + r"\s*=")
    return start, next((i for i in range(start, end) if pattern.match(lines[i])), None)


class Migration:
    def __init__(self, source: Path, home: Path, state: Path, *, check: bool = False,
                 runtime: str = "codex"):
        self.source, self.home, self.state = source, home, state
        self.check = check
        self.claude_runtime = runtime in ("all", "claude")
        self.codex_runtime = runtime in ("all", "codex")
        self.manifest = json.loads(
            (source / "scripts/fixtures/retired-runtime.json").read_text())
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        self.backups = state / "backups/retirement" / (stamp + "-" + uuid.uuid4().hex[:8])
        self.changed = []
        self.set_aside_launchagents = {}

    def backup(self, path: Path, *, move: bool = False) -> None:
        self.require_local_parent(path)
        relative = path.relative_to(self.home)
        destination = self.backups / relative
        if self.check:
            self.changed.append(str(relative))
            print(f"STALE managed target: {relative}")
            return
        if not move and (destination.exists() or destination.is_symlink()):
            return
        self.private_recovery_directory(destination.parent)
        if move and path.is_symlink():
            resolved_copy = destination.with_name(destination.name + ".resolved")
            if path.is_file():
                copy_private_file(path, resolved_copy)
            elif path.is_dir():
                shutil.copytree(path, resolved_copy, copy_function=copy_private_file)
                protect_recovery_directories(resolved_copy)
        if move:
            shutil.move(str(path), str(destination))
        elif path.is_symlink():
            destination.symlink_to(os.readlink(path))
            if path.is_file():
                copy_private_file(path, destination.with_name(destination.name + ".resolved"))
        elif path.is_dir():
            shutil.copytree(path, destination, copy_function=copy_private_file)
        else:
            copy_private_file(path, destination)
        if destination.is_dir() and not destination.is_symlink():
            protect_recovery_directories(destination)
        self.changed.append(str(relative))
        print(f"{'Retired' if move else 'Backed up'} {relative} → {destination}")

    def private_recovery_directory(self, path: Path) -> None:
        self.require_local_parent(path)
        missing = []
        current = path
        while not current.exists():
            missing.append(current)
            current = current.parent
        for directory in reversed(missing):
            directory.mkdir(mode=0o700)
        for directory in (path, *path.parents):
            if directory == self.state:
                break
            directory.chmod(0o700)

    def require_local_parent(self, path: Path) -> None:
        for parent in path.parents:
            if parent == self.home:
                return
            if parent.is_symlink():
                raise ValueError(f"Refusing mutation through symlinked runtime directory: {parent}")
        raise ValueError(f"Runtime target is outside the selected home: {path}")

    def write_json(self, path: Path, value: object) -> None:
        self.require_local_parent(path)
        new = json.dumps(value, indent=2) + "\n"
        if path.exists() or path.is_symlink():
            if not path.is_symlink() and path.read_text() == new:
                return
            self.backup(path)
            if self.check:
                return
        if self.check:
            self.changed.append(str(path.relative_to(self.home)))
            print(f"STALE managed target: {path.relative_to(self.home)}")
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        replace_private_text(path, new)

    def retire_link(self, path: Path, target: Path) -> None:
        if path.is_symlink() and Path(os.readlink(path)) == target:
            self.backup(path, move=True)

    def retire_claude(self) -> None:
        settings = self.home / ".claude/settings.json"
        owned = self.manifest["claude_settings"]
        if self.claude_runtime:
            owned = {key: value for key, value in owned.items() if key in ("statusLine", "hooks")}
            if settings.is_symlink():
                before = json.loads(settings.read_text()) if settings.is_file() else {}
                if self.locked(subtract_owned(before, owned)) != before:
                    raise ValueError(f"BLOCKED: {settings} is a symlink; replace it with a regular file")
        links = {
            ".claude/CLAUDE.md": self.state / "generated/AGENTS.md",
            ".claude/.gitignore": self.source / "claude/.gitignore",
            ".claude/statusline-enhanced.sh": self.source / "claude/statusline-enhanced.sh",
            ".claude/keybindings.json": self.source / "claude/keybindings.json",
            ".claude/docs/harness-runtime-reference.md": self.state / "generated/docs/harness-runtime-reference.md",
            ".claude/docs/peer-runtime-proxy.md": self.state / "generated/docs/peer-runtime-proxy.md",
            ".codex/docs/peer-runtime-proxy.md": self.state / "generated/docs/peer-runtime-proxy.md",
            ".codex/hooks.json": self.source / "codex/hooks.json",
            ".local/bin/claude-gpt": self.source / "claude/claude-gpt",
            ".local/bin/cliproxyctl": self.source / "proxy/cliproxyctl",
        }
        for relative, target in links.items():
            self.retire_link(self.home / relative, target)
        for entry in self.manifest["skill_entries"]:
            parts = Path(entry).parts
            name = parts[2]
            directory = self.home / ".claude/skills" / name
            source_dir = self.source / Path(*parts[:3])
            self.retire_link(directory / "SKILL.md", self.source / entry)
            for support in ("scripts", "assets", "references", "shared", "agents"):
                self.retire_link(directory / support, source_dir / support)
            if directory.is_dir() and not directory.is_symlink() and not any(directory.iterdir()) and not self.check:
                self.require_local_parent(directory)
                directory.rmdir()
        if settings.is_file():
            before = json.loads(settings.read_text())
            after = subtract_owned(before, owned)
            if after != before:
                self.write_json(settings, after)
        for relative in (".local/bin/cli-proxy-api",
                         "Library/LaunchAgents/me.dot-agent.cliproxyapi.plist"):
            if (self.home / relative).exists():
                print(f"Preserved unverified legacy target for owner inspection: {relative}")

    def source_skills(self) -> dict[str, Path]:
        return {p.parent.name: p.parent for p in (self.source / "skills").glob("*/*/SKILL.md")}

    def profile_list(self, name: str) -> set[str]:
        marker = self.state / "machine-profile"
        if not marker.is_file():
            return set()
        path = self.source / "profiles" / marker.read_text().strip() / name
        if not path.is_file():
            return set()
        return {line.strip() for line in path.read_text().splitlines() if line.strip()}

    def provided_skills(self) -> set[str]:
        return self.profile_list("provided-skills")

    def active_skills(self) -> set[str]:
        return set(self.source_skills()) - self.provided_skills()

    def managed_registry(self, runtime: str) -> dict:
        path = self.state / f"managed-{runtime}-skills.json"
        entries = json.loads(path.read_text()) if path.is_file() else {}
        if any(not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name) for name in entries):
            raise ValueError("Invalid managed skill name")
        return entries

    def retire_codex_skills(self) -> None:
        provided = self.provided_skills()
        active = self.active_skills() if self.codex_runtime else set()
        known_payloads = {Path(entry).parts[2]: [] for entry in self.manifest["skill_entries"]}
        for name, payloads in self.manifest["retired_payloads"].items():
            known_payloads.setdefault(name, []).extend(payloads)
        if not self.codex_runtime:
            for name, directory in self.source_skills().items():
                known_payloads.setdefault(name, []).append(source_payload_signature(directory))
        for name, payload in self.managed_registry("codex").items():
            known_payloads.setdefault(name, [])
            if isinstance(payload, dict):
                known_payloads[name].append(payload)
        unresolved = []
        for name, known in known_payloads.items():
            if name in active:
                continue
            path = self.home / ".codex/skills" / name
            actual = payload_signature(path)
            if actual is not None and actual in known:
                self.backup(path, move=True)
            elif name in provided:
                continue
            elif path.exists() or path.is_symlink():
                print(f"Preserved edited or unverified retired skill: {path}")
                unresolved.append(str(path))
        if unresolved and self.codex_runtime:
            raise ValueError("BLOCKED: unresolved retired skills remain callable or unverified; "
                             "inspect and resolve these preserved targets before setup can succeed: "
                             + ", ".join(unresolved))

    def retire_codex_runtime(self) -> None:
        generated = self.state / "generated"
        for relative, target in {
            ".codex/AGENTS.md": generated / "AGENTS.md",
            ".codex/docs/harness-runtime-reference.md": generated / "docs/harness-runtime-reference.md",
        }.items():
            self.retire_link(self.home / relative, target)

    def linked_into_source(self, path: Path) -> bool:
        skills = self.source / "skills"
        if path.is_symlink():
            return Path(os.readlink(path)).is_relative_to(skills)
        if not path.is_dir():
            return False
        entries = list(path.iterdir())
        return bool(entries) and all(
            entry.is_symlink() and Path(os.readlink(entry)).is_relative_to(skills) for entry in entries)

    def retire_claude_skills(self) -> None:
        root = self.home / ".claude/skills"
        if not root.is_dir():
            return
        sources, active = self.source_skills(), self.active_skills()
        provided = self.provided_skills()
        known = self.managed_registry("claude")
        blocked = []
        for path in sorted(root.iterdir()):
            name = path.name
            if name not in sources and (name not in known or (
                    path.is_symlink() and not self.linked_into_source(path))):
                continue
            actual = payload_signature(path)
            owned = self.linked_into_source(path) or (actual is not None and (
                actual == known.get(name)
                or (name in sources and actual == source_payload_signature(sources[name]))))
            if owned and name in active:
                continue
            if owned:
                self.backup(path, move=True)
                continue
            if name in provided:
                continue
            print(f"Preserved owner or edited Claude skill with a managed name: {path}")
            blocked.append(str(path))
        if blocked:
            raise ValueError("BLOCKED: rename or resolve these Claude skills before setup can "
                             "install or retire managed copies: " + ", ".join(blocked))

    def claude_instructions(self) -> None:
        path = self.home / ".claude/CLAUDE.md"
        generated = self.state / "generated/AGENTS.md"
        line = f"@{generated}"
        forms = {line}
        if generated.is_relative_to(self.home):
            forms.add(f"@~/{generated.relative_to(self.home)}")
        def first(text: str) -> str:
            return next(iter(text.splitlines()), "").strip()
        if path.is_symlink():
            if path.is_file() and first(path.read_text(errors="surrogateescape")) in forms:
                return
            raise ValueError(f"BLOCKED: {path} is a symlink; start its target with {line} "
                             "or replace it with a regular file")
        text = path.read_text(errors="surrogateescape") if path.is_file() else None
        if text is not None and first(text) in forms:
            return
        rest = "" if text is None else "".join(
            kept for kept in text.splitlines(keepends=True) if kept.strip() not in forms).lstrip("\r\n")
        new = line + "\n" + ("\n" + rest if rest else "")
        if text is not None:
            self.backup(path)
            if not self.check:
                with path.open("w", encoding="utf-8", errors="surrogateescape") as handle:
                    handle.write(new)
            return
        self.require_local_parent(path)
        if self.check:
            self.changed.append(str(path.relative_to(self.home)))
            print(f"STALE managed target: {path.relative_to(self.home)}")
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new)
        path.chmod(0o644)

    def locked(self, settings: dict) -> dict:
        after = dict(settings)
        for key, value in json.loads((self.source / "claude/model-lock.json").read_text()).items():
            after[key] = locked_value(after.get(key), value)
        if isinstance(after.get("env"), dict):
            after["env"] = {name: item for name, item in after["env"].items() if name not in RETIRED_CLAUDE_ENV}
        excludes = after.get("claudeMdExcludes", [])
        if isinstance(excludes, list) and CLOUD_RULES not in excludes:
            after["claudeMdExcludes"] = excludes + [CLOUD_RULES]
        after = with_mods(after, mod_dirs(self.source))
        return with_hooks(after, json.loads((self.source / "claude/hooks.json").read_text()))

    def claude_settings(self) -> None:
        path = self.home / ".claude/settings.json"
        before = json.loads(path.read_text()) if path.is_file() else {}
        after = self.locked(before)
        if after == before:
            return
        mode = stat.S_IMODE(path.stat().st_mode) if path.is_file() else None
        self.write_json(path, after)
        if mode is not None and not self.check:
            path.chmod(mode)

    def record_skills(self, runtime: str = "codex") -> None:
        entries = {}
        provided = self.provided_skills()
        for source in (self.source / "skills").glob("*/*/SKILL.md"):
            if source.parent.name in provided:
                continue
            directory = self.home / f".{runtime}/skills" / source.parent.name
            if (directory / "SKILL.md").is_file():
                signature = payload_signature(directory)
                if signature is None:
                    raise ValueError(f"Cannot record unverified skill payload: {directory}")
                entries[source.parent.name] = signature
        self.state.mkdir(parents=True, exist_ok=True)
        registry = self.state / f"managed-{runtime}-skills.json"
        text = json.dumps(entries, indent=2, sort_keys=True) + "\n"
        if not registry.is_file() or registry.read_text() != text:
            registry.write_text(text)

    def codex_config(self) -> None:
        config = self.home / ".codex/config.toml"
        self.require_local_parent(config)
        source = (self.source / "codex/config.toml").read_text()
        managed = line_editable(source)
        text = without_generated_keymap(config.read_text(), self.manifest["codex_keymap"])
        current = line_editable(text)
        source_lines, lines = source.splitlines(), text.splitlines()
        expected = copy.deepcopy(current)
        edited = False
        for table, key in CODEX_PINS:
            wanted = source_lines[locate(source_lines, table, key)[1]].strip()
            value = managed[table][key] if table else managed[key]
            owner = current.get(table, {}).get(key) if table else current.get(key)
            if isinstance(owner, dict) and isinstance(value, dict) and owner.keys() - value.keys():
                raise ValueError(f"BLOCKED: {config} [{table}] {key} has owner keys; merge them by hand")
            (expected.setdefault(table, {}) if table else expected)[key] = value
            start, index = locate(lines, table, key)
            if start is None:
                lines += ["", f"[{table}]", wanted]
            elif index is None:
                lines.insert(start, wanted)
            elif strict_loads(lines[index]) != strict_loads(wanted):
                lines[index] = wanted
            else:
                continue
            edited = True
        if edited:
            text = "\n".join(lines) + "\n"
        if strict_loads(text) != expected:
            raise ValueError("Config transformation changed non-managed values; config was not changed")
        if config.read_text() != text:
            self.backup(config)
            if not self.check:
                replace_private_text(config, text)
        hooks = self.home / ".codex/hooks.json"
        if hooks.is_file():
            before = json.loads(hooks.read_text())
            after = remove_owned_hooks(before)
            if after != before:
                self.write_json(hooks, after)

    def retire_files(self) -> None:
        for relative, digest in self.manifest["retired_files"].items():
            path = self.home / relative
            if path.is_file() and not path.is_symlink() \
                    and sha256(path.read_bytes()).hexdigest() == digest:
                self.backup(path, move=True)
            elif path.exists() or path.is_symlink():
                print(f"Kept {relative}: it differs from the retired managed copy")

    def retire_launchagents(self) -> None:
        for label, folder in self.manifest["retired_launchagents"].items():
            plist = self.home / "Library/LaunchAgents" / f"{label}.plist"
            if plist.is_symlink() or not plist.is_file():
                continue
            try:
                with plist.open("rb") as handle:
                    data = plistlib.load(handle)
            except (OSError, ValueError, plistlib.InvalidFileException):
                data = None
            root = self.home / ".dot-agent" / folder
            arguments = data.get("ProgramArguments") if isinstance(data, dict) else None
            if data is None or data.get("Label") != label or not isinstance(arguments, list) \
                    or not any(isinstance(item, str) and Path(item).is_relative_to(root)
                               for item in arguments):
                print(f"Preserved unverified LaunchAgent for owner inspection: {plist}")
                continue
            relative = str(plist.relative_to(self.home))
            if self.check:
                self.changed.append(relative)
                print(f"STALE managed target: {relative}")
                continue
            if not boot_out(label):
                print(f"Kept {plist}: launchctl could not stop {label}; "
                      "log out or reboot, then rerun setup")
                continue
            folder_path = self.state / "retired-launchagents"
            self.private_recovery_directory(folder_path)
            destination = folder_path / plist.name
            if destination.exists() or destination.is_symlink():
                destination = folder_path / f"{plist.name}.{self.backups.name}"
            shutil.move(str(plist), str(destination))
            destination.chmod(0o600)
            self.changed.append(relative)
            self.set_aside_launchagents[relative] = str(destination)
            print(f"Retired LaunchAgent {label} → {destination}")

    def report(self) -> None:
        if self.changed and not self.check:
            self.private_recovery_directory(self.backups)
            replace_private_text(self.backups / "receipt.json", json.dumps(
                {"version": 1, "changed": self.changed, "moved": self.set_aside_launchagents,
                 "restore": "Inspect each saved target, then restore exact paths while setup is stopped."},
                indent=2) + "\n")


def boot_out(label: str) -> bool:
    launchctl = shutil.which("launchctl")
    if not launchctl:
        return True
    target = f"gui/{os.getuid()}/{label}"
    try:
        if subprocess.run([launchctl, "bootout", target],
                          capture_output=True, timeout=30).returncode == 0:
            return True
        return subprocess.run([launchctl, "print", target],
                              capture_output=True, timeout=30).returncode != 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def replace_private_text(path: Path, text: str) -> None:
    mode = stat.S_IMODE(path.stat().st_mode) & 0o600 if path.exists() else 0o600
    descriptor, temporary = tempfile.mkstemp(prefix=".dot-agent-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            os.fchmod(handle.fileno(), mode)
            handle.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def copy_private_file(source, destination):
    source, destination = Path(source), Path(destination)
    mode = stat.S_IMODE(source.stat().st_mode) & 0o600
    descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with source.open("rb") as original, os.fdopen(descriptor, "wb") as copied:
        os.fchmod(copied.fileno(), mode)
        shutil.copyfileobj(original, copied)
    return str(destination)


def protect_recovery_directories(root: Path) -> None:
    root.chmod(0o700)
    for path in root.rglob("*"):
        if path.is_dir() and not path.is_symlink():
            path.chmod(0o700)


def locked_value(current: object, value: object) -> object:
    if not isinstance(value, dict) or not isinstance(current, dict):
        return value
    return {**current, **{key: locked_value(current.get(key), item) for key, item in value.items()}}


def payload_signature(directory: Path) -> dict | None:
    if not directory.is_dir() or directory.is_symlink():
        return None
    result = {}
    for path in directory.rglob("*"):
        relative = path.relative_to(directory)
        if "__pycache__" in relative.parts or path.suffix in (".pyc", ".pyo"):
            continue
        if path.is_symlink():
            return None
        if path.is_dir():
            result[str(relative) + "/"] = "directory"
        elif path.is_file():
            result[str(relative)] = sha256(path.read_bytes()).hexdigest()
        else:
            return None
    return result


def source_payload_signature(directory: Path) -> dict | None:
    entry = directory / "codex/SKILL.md"
    if entry.is_file():
        result = payload_signature(entry.parent)
        if result is None:
            return None
    else:
        entry = directory / "SKILL.md"
        if not entry.is_file() or entry.is_symlink():
            return None
        result = {"SKILL.md": sha256(entry.read_bytes()).hexdigest()}
    for root_file in sorted(directory.glob("*.md")):
        if root_file.name != "SKILL.md" and root_file.is_file() and not root_file.is_symlink():
            result[root_file.name] = sha256(root_file.read_bytes()).hexdigest()
    for name in ("scripts", "assets", "references", "shared", "agents", "playbooks", "principles"):
        support = directory / name
        if support.is_dir():
            contents = payload_signature(support)
            if contents is None:
                return None
            if contents:
                result[name + "/"] = "directory"
                result.update({name + "/" + key: value for key, value in contents.items()})
    return result


def subtract_owned(existing: object, owned: object) -> object:
    if isinstance(existing, dict) and isinstance(owned, dict):
        if owned.get("type") == "command":
            return {} if existing == owned else existing
        result = dict(existing)
        for key, value in owned.items():
            if key not in result:
                continue
            if result[key] == value:
                del result[key]
            elif isinstance(result[key], (dict, list)):
                result[key] = subtract_owned(result[key], value)
        return result
    if isinstance(existing, list) and isinstance(owned, list):
        result = []
        for item in existing:
            if item in owned:
                continue
            if isinstance(item, dict) and "hooks" in item:
                matching = [o for o in owned if isinstance(o, dict)
                            and o.get("matcher") == item.get("matcher")]
                copy = dict(item)
                for old in matching:
                    copy["hooks"] = subtract_owned(copy["hooks"], old.get("hooks", []))
                if not copy["hooks"]:
                    continue
                item = copy
            result.append(item)
        return result
    return existing


def managed_hook_group(group: object) -> bool:
    commands = [hook.get("command") for hook in group.get("hooks", [])
                if isinstance(hook, dict)] if isinstance(group, dict) else []
    return bool(commands) and all(isinstance(command, str) and HOOK_HOME in command
                                  for command in commands)


def mod_dirs(source: Path) -> list:
    return [f"~/.dot-agent/claude/mods/{path.parent.parent.name}"
            for path in sorted((source / "claude/mods").glob("*/.claude-plugin/plugin.json"))]


def with_mods(settings: dict, wanted: list) -> dict:
    env = settings.get("env", {})
    if not wanted or not isinstance(env, dict):
        return settings
    current = [item for item in str(env.get(PLUGIN_DIRS) or "").split(os.pathsep) if item]
    have = {os.path.expanduser(item) for item in current}
    joined = os.pathsep.join(current + [item for item in wanted if os.path.expanduser(item) not in have])
    return dict(settings, env=dict(env, **{PLUGIN_DIRS: joined}))


def with_hooks(settings: dict, wanted: dict) -> dict:
    current = settings.get("hooks", {})
    if not isinstance(current, dict):
        raise ValueError("BLOCKED: ~/.claude/settings.json hooks is not an object; fix it by hand")
    hooks = dict(current)
    for event, groups in wanted.items():
        existing = hooks.get(event, [])
        if not isinstance(existing, list):
            raise ValueError(f"BLOCKED: ~/.claude/settings.json hooks.{event} is not a list")
        hooks[event] = [group for group in existing if not managed_hook_group(group)] + groups
    return dict(settings, hooks=hooks)


def without_generated_keymap(text: str, keymap: dict) -> str:
    before = strict_loads(text)
    if before.get("tui", {}).get("keymap") != keymap:
        return text
    lines = text.splitlines()
    for context, actions in keymap.items():
        starts = [i for i, line in enumerate(lines) if line.strip() == f"[tui.keymap.{context}]"]
        if len(starts) != 1:
            return text
        start = starts[0]
        end = next((i for i in range(start + 1, len(lines)) if lines[i].lstrip().startswith("[")),
                   len(lines))
        if [line.strip() for line in lines[start + 1:end] if line.strip()] != [
                f"{key} = {json.dumps(value)}" for key, value in actions.items()]:
            return text
        del lines[start:end]
    while lines and not lines[-1].strip():
        lines.pop()
    result = "\n".join(lines) + "\n"
    after = strict_loads(result)
    del before["tui"]["keymap"]
    if not before["tui"] and "tui" not in after:
        del before["tui"]
    return result if after == before else text


def remove_owned_hooks(document: dict) -> dict:
    result = json.loads(json.dumps(document))
    commands = {"cat ~/.dot-agent/claude/caveman-boot.txt", "~/.dot-agent/codex/title-hook.sh"}
    for event, groups in list(result.get("hooks", {}).items()):
        if not isinstance(groups, list):
            continue
        kept = []
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                kept.append(group)
                continue
            copy = dict(group)
            copy["hooks"] = [h for h in group.get("hooks", [])
                             if not (isinstance(h, dict) and h.get("type") == "command"
                                     and h.get("command") in commands)]
            if copy["hooks"]:
                kept.append(copy)
        if kept:
            result["hooks"][event] = kept
        else:
            del result["hooks"][event]
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--codex-config", action="store_true")
    parser.add_argument("--record-skills", action="store_true")
    parser.add_argument("--check", action="store_true", help="Read-only managed retirement and Codex config audit")
    parser.add_argument("--runtime", choices=("codex", "all", "claude"), default="codex",
                        help="Installed runtimes (matches setup.sh --runtime). With Claude Code, keep "
                             "owner settings, manage copied skills and the CLAUDE.md import line; "
                             "without Codex, retire its managed links and skill copies")
    args = parser.parse_args()
    migration = Migration(args.source, args.home, args.state, check=args.check,
                          runtime=args.runtime)
    try:
        if args.record_skills:
            if args.check:
                parser.error("--record-skills cannot be combined with --check")
            if migration.codex_runtime:
                migration.record_skills()
            if migration.claude_runtime:
                migration.record_skills("claude")
        elif args.codex_config:
            migration.codex_config()
        else:
            migration.retire_claude()
            migration.retire_files()
            migration.retire_launchagents()
            migration.retire_codex_skills()
            if not migration.codex_runtime:
                migration.retire_codex_runtime()
            if migration.claude_runtime:
                migration.retire_claude_skills()
                migration.claude_instructions()
                migration.claude_settings()
            if args.check and migration.codex_runtime:
                migration.codex_config()
    finally:
        migration.report()
    if args.check and migration.changed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
