#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1

MODE="install"

usage() {
  echo "Usage: ./setup.sh [--version] [--check-instructions] [--live-delegation-probe] [--runtime codex|all|claude]"
  echo
  echo "Modes:"
  echo "  ./setup.sh                 Install runtime config, then run instruction audits."
  echo "  ./setup.sh --version       Show the source, installed and origin/main versions."
  echo "  ./setup.sh --check-instructions"
  echo "                             Run instruction audits only; do not install or patch."
  echo "  ./setup.sh --check-instructions --live-delegation-probe"
  echo "                             Also run the live ephemeral Codex delegation proof."
  echo "  ./setup.sh --runtime all   Install Codex plus Claude Code: the normal choice on a Mac"
  echo "                             with both runtimes. --runtime codex installs Codex only"
  echo "                             (the default); --runtime claude installs Claude Code only"
  echo "                             and retires managed Codex copies. An explicit choice is saved in"
  echo "                             state/runtime-scope for later runs."
}

RUNTIME_SCOPE=""
LIVE_DELEGATION_PROBE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-instructions)
      MODE="check-instructions"
      shift
      ;;
    --version)
      MODE="version"
      shift
      ;;
    --live-delegation-probe)
      LIVE_DELEGATION_PROBE=1
      shift
      ;;
    --runtime)
      shift
      case "${1:-}" in
        codex|all|claude) RUNTIME_SCOPE="$1" ;;
        *) echo "ERROR: --runtime takes codex, all or claude"; usage; exit 1 ;;
      esac
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1"
      usage
      exit 1
      ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
EXPECTED_DOT_AGENT_HOME="$HOME/.dot-agent"
COMMON_GIT_DIR="$(git -C "$REPO_ROOT" rev-parse --git-common-dir 2>/dev/null || true)"
if [[ -n "$COMMON_GIT_DIR" && "$COMMON_GIT_DIR" != /* ]]; then
  COMMON_GIT_DIR="$(cd "$REPO_ROOT/$COMMON_GIT_DIR" && pwd -P)"
fi

CANONICAL_REPO_ROOT=""
if [[ -n "$COMMON_GIT_DIR" ]]; then
  CANONICAL_REPO_ROOT="$(cd "$COMMON_GIT_DIR/.." && pwd -P)"
fi

if [[ "$REPO_ROOT" != "$EXPECTED_DOT_AGENT_HOME" && "$CANONICAL_REPO_ROOT" != "$EXPECTED_DOT_AGENT_HOME" ]]; then
  echo "ERROR: dot-agent must live at $EXPECTED_DOT_AGENT_HOME"
  echo "Current repo root: $REPO_ROOT"
  echo "Clone or move the repo, then rerun setup:"
  echo "  git clone https://github.com/<you>/agent-harness.git $EXPECTED_DOT_AGENT_HOME"
  echo "  cd $EXPECTED_DOT_AGENT_HOME"
  echo "  ./setup.sh"
  exit 1
fi

DOT_AGENT_HOME="$EXPECTED_DOT_AGENT_HOME"
DOT_AGENT_SOURCE_ROOT="$REPO_ROOT"
DOT_AGENT_STATE_HOME="${DOT_AGENT_STATE_HOME:-$DOT_AGENT_HOME/state}"
CODEX_SRC="$DOT_AGENT_SOURCE_ROOT/codex"
SKILLS_SRC="$DOT_AGENT_SOURCE_ROOT/skills"
CODEX_DST="$HOME/.codex"
CLAUDE_DST="$HOME/.claude"
BACKUP_ROOT="$DOT_AGENT_STATE_HOME/backups/setup/$(date +%Y%m%d%H%M%S)-$$"
PROFILES_SRC="$DOT_AGENT_SOURCE_ROOT/profiles"
INSTALLED_VERSION_FILE="$DOT_AGENT_STATE_HOME/installed-version"

source_version() {
  local version commit
  version="$(tr -d '[:space:]' < "$DOT_AGENT_SOURCE_ROOT/VERSION")"
  commit="$(git -C "$DOT_AGENT_SOURCE_ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)"
  echo "$version ($commit)"
}

main_version() {
  git -C "$DOT_AGENT_SOURCE_ROOT" show origin/main:VERSION 2>/dev/null | tr -d '[:space:]' || true
}

report_version() {
  local main
  echo "Source:      $(source_version)"
  if [[ -f "$INSTALLED_VERSION_FILE" ]]; then
    echo "Installed:   $(cat "$INSTALLED_VERSION_FILE")"
  else
    echo "Installed:   none recorded (run ./setup.sh)"
  fi
  main="$(main_version)"
  echo "origin/main: ${main:-unknown} (as of the last fetch)"
}

if [[ "$MODE" == "version" ]]; then
  report_version
  exit 0
fi
MACHINE_PROFILE_FILE="$DOT_AGENT_STATE_HOME/machine-profile"
MACHINE_PROFILE=""
if [[ -f "$MACHINE_PROFILE_FILE" ]]; then
  MACHINE_PROFILE="$(tr -d '[:space:]' < "$MACHINE_PROFILE_FILE")"
fi

RUNTIME_SCOPE_FILE="$DOT_AGENT_STATE_HOME/runtime-scope"
RUNTIME_SCOPE_EXPLICIT=0
if [[ -n "$RUNTIME_SCOPE" ]]; then
  RUNTIME_SCOPE_EXPLICIT=1
elif [[ -f "$RUNTIME_SCOPE_FILE" ]]; then
  RUNTIME_SCOPE="$(tr -d '[:space:]' < "$RUNTIME_SCOPE_FILE")"
fi
case "$RUNTIME_SCOPE" in
  codex|all|claude) ;;
  "") RUNTIME_SCOPE="codex" ;;
  *) echo "ERROR: $RUNTIME_SCOPE_FILE must contain codex, all or claude"; exit 1 ;;
esac
INSTALL_CODEX=0
INSTALL_CLAUDE=0
[[ "$RUNTIME_SCOPE" != "claude" ]] && INSTALL_CODEX=1
[[ "$RUNTIME_SCOPE" != "codex" ]] && INSTALL_CLAUDE=1
AUDIT_RUNTIME="codex"
[[ "$INSTALL_CODEX" == "0" ]] && AUDIT_RUNTIME="claude"

GENERATED_AGENTS="$DOT_AGENT_STATE_HOME/generated/AGENTS.md"
GENERATED_RUNTIME_REFERENCE="$DOT_AGENT_STATE_HOME/generated/docs/harness-runtime-reference.md"


generate_agents_md() {
  local fragment="$PROFILES_SRC/$MACHINE_PROFILE/AGENTS.md"
  mkdir -p "$(dirname "$GENERATED_AGENTS")" "$(dirname "$GENERATED_RUNTIME_REFERENCE")"
  {
    cat "$DOT_AGENT_SOURCE_ROOT/AGENTS.md"
    if [[ -n "$MACHINE_PROFILE" && -f "$fragment" ]]; then
      echo
      cat "$fragment"
    fi
  } > "$GENERATED_AGENTS"
  cp "$DOT_AGENT_SOURCE_ROOT/docs/harness-runtime-reference.md" \
    "$GENERATED_RUNTIME_REFERENCE"
}

source "$DOT_AGENT_SOURCE_ROOT/scripts/lib/install-skills.sh"

install_git_hooks() {
  git -C "$DOT_AGENT_SOURCE_ROOT" rev-parse --git-dir >/dev/null 2>&1 || return 0
  if [[ "$(git -C "$DOT_AGENT_SOURCE_ROOT" config --get core.hooksPath || true)" != ".githooks" ]]; then
    git -C "$DOT_AGENT_SOURCE_ROOT" config core.hooksPath .githooks
    echo "Set core.hooksPath to .githooks for $DOT_AGENT_SOURCE_ROOT"
  fi
}

backup_and_link() {
  local src="$1"
  local dst="$2"
  local rel="$3"

  if [[ -L "$dst" && "$(readlink "$dst")" == "$src" ]]; then
    return
  fi

  backup_path "$dst" "$rel"
  mkdir -p "$(dirname "$dst")"
  ln -s "$src" "$dst"
}

backup_and_copy() {
  local src="$1"
  local dst="$2"
  local rel="$3"

  if [[ -f "$dst" && ! -L "$dst" ]] && cmp -s "$src" "$dst"; then
    return
  fi

  backup_path "$dst" "$rel"
  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst"
}

merge_toml_config() {
  local src="$1"
  local dst="$2"
  local rel="$3"
  local tmp_file

  tmp_file="$(mktemp "${TMPDIR:-/tmp}/dot-agent-toml-config.XXXXXX")"

  if [[ -e "$dst" || -L "$dst" ]]; then
    python3 - "$src" "$dst" "$tmp_file" <<'PY'
import re
import sys
from pathlib import Path

SECTION_RE = re.compile(r"^\s*(\[[^\]]+\])\s*$")
KEY_RE = re.compile(r"^\s*([^#=\s][^=]*?)\s*=")

def split_sections(text):
    order = [""]
    sections = {"": []}
    current = ""
    for line in text.splitlines():
        match = SECTION_RE.match(line)
        if match:
            current = match.group(1)
            if current not in sections:
                order.append(current)
                sections[current] = [line]
            else:
                sections[current].append(line)
            continue
        sections.setdefault(current, []).append(line)
    return order, sections

def section_keys(lines):
    keys = set()
    for line in lines:
        if SECTION_RE.match(line):
            continue
        match = KEY_RE.match(line)
        if match:
            keys.add(match.group(1).strip())
    return keys

def missing_key_lines(source_lines, existing_lines):
    existing_keys = section_keys(existing_lines)
    missing = []
    for line in source_lines:
        if SECTION_RE.match(line):
            continue
        match = KEY_RE.match(line)
        if match and match.group(1).strip() not in existing_keys:
            missing.append(line)
    return missing

source_order, source_sections = split_sections(Path(sys.argv[1]).read_text())
existing_order, existing_sections = split_sections(Path(sys.argv[2]).read_text())

merged_order = list(existing_order)
merged_sections = {section: list(lines) for section, lines in existing_sections.items()}

root_missing = missing_key_lines(source_sections.get("", []), merged_sections.get("", []))
if root_missing:
    root_lines = merged_sections.setdefault("", [])
    if root_lines and root_lines[-1].strip():
        root_lines.append("")
    root_lines.extend(root_missing)

for section in source_order:
    if section == "":
        continue
    source_lines = source_sections[section]
    if section not in merged_sections:
        merged_order.append(section)
        merged_sections[section] = list(source_lines)
        continue
    missing = missing_key_lines(source_lines, merged_sections[section])
    if missing:
        if merged_sections[section] and merged_sections[section][-1].strip():
            merged_sections[section].append("")
        merged_sections[section].extend(missing)

out = []
for section in merged_order:
    lines = merged_sections.get(section, [])
    if not lines:
        continue
    if out and out[-1].strip():
        out.append("")
    out.extend(lines)

Path(sys.argv[3]).write_text("\n".join(out).rstrip() + "\n")
PY
  else
    cp "$src" "$tmp_file"
  fi

  python3 "$DOT_AGENT_SOURCE_ROOT/scripts/toml_edit.py" "$tmp_file"

  if [[ -e "$dst" && ! -L "$dst" ]] && cmp -s "$tmp_file" "$dst"; then
    rm -f "$tmp_file"
    return
  fi

  backup_path "$dst" "$rel"
  mkdir -p "$(dirname "$dst")"
  mv "$tmp_file" "$dst"
}

link_codex_payload() {
  backup_and_link "$GENERATED_AGENTS" "$CODEX_DST/AGENTS.md" ".codex/AGENTS.md"
  backup_and_link "$GENERATED_RUNTIME_REFERENCE" "$CODEX_DST/docs/harness-runtime-reference.md" ".codex/docs/harness-runtime-reference.md"
  merge_toml_config "$CODEX_SRC/config.toml" "$CODEX_DST/config.toml" ".codex/config.toml"
  python3 "$DOT_AGENT_SOURCE_ROOT/scripts/retire-managed-runtime.py" \
    --source "$DOT_AGENT_SOURCE_ROOT" --home "$HOME" --state "$DOT_AGENT_STATE_HOME" --codex-config
}

apply_profile_overlays() {
  if [[ -z "$MACHINE_PROFILE" ]]; then
    echo "NOTICE: no machine profile set; profile overlays skipped."
    echo "  Available profiles: $(ls "$PROFILES_SRC" 2>/dev/null | tr '\n' ' ')"
    echo "  To enable one: echo <profile> > $MACHINE_PROFILE_FILE"
    return
  fi

  local profile_src="$PROFILES_SRC/$MACHINE_PROFILE"
  if [[ ! -d "$profile_src" ]]; then
    echo "WARN: machine profile '$MACHINE_PROFILE' has no overlay at $profile_src"
    return
  fi

  echo "Applying machine profile: $MACHINE_PROFILE"

  if [[ -f "$profile_src/ensure.sh" ]]; then
    if ! DOT_AGENT_STATE_HOME="$DOT_AGENT_STATE_HOME" RUNTIME_SCOPE="$RUNTIME_SCOPE" \
      bash "$profile_src/ensure.sh"; then
      echo "WARN: profile ensure script failed: $profile_src/ensure.sh"
    fi
  fi
}

run_python_audit() {
  local script="$1"
  shift
  local python=(python3)
  command -v uv >/dev/null 2>&1 && python=(uv run python)

  if ! (
    cd "$DOT_AGENT_SOURCE_ROOT"
    DOT_AGENT_HOME="$DOT_AGENT_HOME" CODEX_HOME="$CODEX_DST" "${python[@]}" "$script" "$@"
  ); then
    echo "WARN: Audit script failed: $script"
    return 1
  fi
}

run_instruction_audits() {
  local status=0
  local skill_args=() repo_args=()
  if [[ "${1:-advisory}" == "strict" ]]; then
    skill_args=(--strict)
    repo_args=(--strict --dot-agent-only)
  fi
  echo
  run_python_audit "$DOT_AGENT_SOURCE_ROOT/scripts/skill-instruction-audit.py" \
    --runtime "$AUDIT_RUNTIME" ${skill_args[@]+"${skill_args[@]}"} || status=1
  echo
  run_python_audit "$DOT_AGENT_SOURCE_ROOT/scripts/repo-instruction-audit.py" \
    ${repo_args[@]+"${repo_args[@]}"} || status=1
  echo
  if [[ "$INSTALL_CODEX" == "1" ]]; then
    run_python_audit "$DOT_AGENT_SOURCE_ROOT/scripts/settings-drift-audit.py" || status=1
  fi
  run_python_audit "$DOT_AGENT_SOURCE_ROOT/scripts/retire-managed-runtime.py" \
    --source "$DOT_AGENT_SOURCE_ROOT" --home "$HOME" --state "$DOT_AGENT_STATE_HOME" \
    --check --runtime "$RUNTIME_SCOPE" || status=1
  echo
  if [[ "$LIVE_DELEGATION_PROBE" == "1" ]]; then
    if ! bash "$DOT_AGENT_SOURCE_ROOT/scripts/codex-delegation-check.sh"; then
      echo "WARN: Codex delegation check failed"
      status=1
    fi
  fi
  return "$status"
}

prune_setup_backups() {
  local keep=10
  local backups_dir="$DOT_AGENT_STATE_HOME/backups/setup"
  local stale_dirs

  [[ -d "$backups_dir" ]] || return 0
  stale_dirs="$(ls -1 "$backups_dir" | LC_ALL=C sort -r | tail -n +$((keep + 1)))"
  [[ -n "$stale_dirs" ]] || return 0

  while IFS= read -r entry; do
    rm -rf "$backups_dir/${entry:?}"
  done <<<"$stale_dirs"
  echo "Pruned setup backups to the newest $keep runs"
}

if [[ "$MODE" == "check-instructions" ]]; then
  run_instruction_audits strict
  exit $?
fi

if [[ "$REPO_ROOT" != "$EXPECTED_DOT_AGENT_HOME" ]]; then
  if [[ "${DOT_AGENT_ALLOW_SECONDARY_SOURCE:-0}" != "1" ]]; then
    echo "ERROR: refusing to install from a secondary checkout: $REPO_ROOT"
    echo "Installing from here would point runtime symlinks at this checkout"
    echo "instead of $EXPECTED_DOT_AGENT_HOME. Run the canonical install:"
    echo "  $EXPECTED_DOT_AGENT_HOME/setup.sh"
    echo "Set DOT_AGENT_ALLOW_SECONDARY_SOURCE=1 only when debugging setup."
    exit 1
  fi
  echo "WARN: installing from secondary checkout $REPO_ROOT (override active)"
fi

if [[ -n "$MACHINE_PROFILE" && ! -d "$PROFILES_SRC/$MACHINE_PROFILE" ]]; then
  echo "ERROR: unknown machine profile '$MACHINE_PROFILE'"
  echo "  Available: $(ls "$PROFILES_SRC" 2>/dev/null | tr '\n' ' ')"
  echo "  Fix $MACHINE_PROFILE_FILE and rerun."
  exit 1
fi

for runtime_path in "$HOME/.claude" "$HOME/.claude/skills" "$HOME/.claude/docs" \
  "$CODEX_DST" "$CODEX_DST/skills" "$CODEX_DST/docs"; do
  if [[ -L "$runtime_path" ]]; then
    echo "ERROR: refusing install through symlinked runtime directory: $runtime_path"
    exit 1
  fi
done
if [[ "$INSTALL_CODEX" == "1" ]]; then
  python3 "$DOT_AGENT_SOURCE_ROOT/scripts/toml_edit.py" \
    "$CODEX_DST/config.toml" "$CODEX_SRC/config.toml"
fi
if [[ "$RUNTIME_SCOPE_EXPLICIT" == "1" ]]; then
  mkdir -p "$DOT_AGENT_STATE_HOME"
  echo "$RUNTIME_SCOPE" > "$RUNTIME_SCOPE_FILE"
fi
python3 "$DOT_AGENT_SOURCE_ROOT/scripts/retire-managed-runtime.py" \
  --source "$DOT_AGENT_SOURCE_ROOT" --home "$HOME" --state "$DOT_AGENT_STATE_HOME" \
  --runtime "$RUNTIME_SCOPE"
generate_agents_md
install_git_hooks
if [[ "$INSTALL_CODEX" == "1" ]]; then
  mkdir -p "$CODEX_DST/skills"
  link_codex_payload
fi
if [[ "$INSTALL_CLAUDE" == "1" ]]; then
  mkdir -p "$CLAUDE_DST/skills"
  backup_and_copy "$GENERATED_RUNTIME_REFERENCE" "$CLAUDE_DST/docs/harness-runtime-reference.md" ".claude/docs/harness-runtime-reference.md"
  backup_and_copy "$DOT_AGENT_SOURCE_ROOT/claude/scheduled-tasks/gardening-hunter/SKILL.md" \
    "$CLAUDE_DST/scheduled-tasks/gardening-hunter/SKILL.md" ".claude/scheduled-tasks/gardening-hunter/SKILL.md"
fi
link_skills
apply_profile_overlays

if [[ "$INSTALL_CODEX" == "1" ]]; then
  echo "Installed Codex config into $CODEX_DST"
fi
if [[ "$INSTALL_CLAUDE" == "1" ]]; then
  echo "Installed Claude Code instructions and skills into $CLAUDE_DST"
fi
echo "Source config came from $DOT_AGENT_SOURCE_ROOT"
echo "Shared state home is $DOT_AGENT_STATE_HOME"
echo "Machine profile: ${MACHINE_PROFILE:-<none>}"
if [[ -d "$BACKUP_ROOT" ]]; then
  echo "Backups stored in $BACKUP_ROOT"
fi
prune_setup_backups
if ! run_instruction_audits; then
  echo "WARN: one or more instruction audits failed"
fi

echo
if ! DOT_AGENT_HOME="$DOT_AGENT_HOME" \
  DOT_AGENT_STATE_HOME="$DOT_AGENT_STATE_HOME" \
  CODEX_HOME="$CODEX_DST" \
  CLAUDE_HOME="$CLAUDE_DST" \
  python3 "$DOT_AGENT_SOURCE_ROOT/scripts/verify-profile.py" --runtime "$RUNTIME_SCOPE"; then
  echo "ERROR: profile verification failed — install is not in a good state"
  exit 1
fi
python3 "$DOT_AGENT_SOURCE_ROOT/scripts/retire-managed-runtime.py" \
  --source "$DOT_AGENT_SOURCE_ROOT" --home "$HOME" --state "$DOT_AGENT_STATE_HOME" \
  --record-skills --runtime "$RUNTIME_SCOPE"
echo "$(source_version) profile=${MACHINE_PROFILE:-none} runtime=$RUNTIME_SCOPE" \
  > "$INSTALLED_VERSION_FILE"
echo
echo "dot-agent $(source_version) installed"
MAIN_VERSION="$(main_version)"
if [[ -n "$MAIN_VERSION" && "$MAIN_VERSION" != "$(tr -d '[:space:]' < "$DOT_AGENT_SOURCE_ROOT/VERSION")" ]]; then
  echo "NOTICE: origin/main is at $MAIN_VERSION; pull main and rerun setup to match it"
fi
