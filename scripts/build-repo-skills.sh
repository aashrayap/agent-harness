#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1

DOT_AGENT_SOURCE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SKILLS_SRC="$DOT_AGENT_SOURCE_ROOT/skills"
PROFILES_SRC="$DOT_AGENT_SOURCE_ROOT/profiles"
MACHINE_PROFILE=personal
INSTALL_CODEX=0
INSTALL_CLAUDE=1
TARGET="${REPO_SKILLS_TARGET:-$DOT_AGENT_SOURCE_ROOT/.claude/skills}"

build="$(mktemp -d "${TMPDIR:-/tmp}/dot-agent-repo-skills.XXXXXX")"
trap 'rm -rf "$build"' EXIT
CLAUDE_DST="$build/.claude"
BACKUP_ROOT="$build/backups"
source "$DOT_AGENT_SOURCE_ROOT/scripts/lib/install-skills.sh"

mkdir -p "$CLAUDE_DST/skills"
link_skills
find "$CLAUDE_DST/skills" -path '*/agents/openai.yaml' -delete
find "$CLAUDE_DST/skills" -type d -empty -delete

case "${1:-}" in
  --check)
    modes() { (cd "$1" && find . -type f -perm -u+x -not -path '*/__pycache__/*' | sort); }
    if ! diff -r -x __pycache__ "$CLAUDE_DST/skills" "$TARGET" || [[ "$(modes "$CLAUDE_DST/skills")" != "$(modes "$TARGET")" ]]; then
      echo "ERROR: .claude/skills differs from skills/; run scripts/build-repo-skills.sh and commit"
      exit 1
    fi
    echo ".claude/skills matches skills/"
    ;;
  "")
    if [[ -d "$TARGET" ]] && git -C "$TARGET" rev-parse --is-inside-work-tree >/dev/null 2>&1 \
      && [[ -n "$(git -C "$TARGET" status --porcelain -- .)" ]]; then
      echo "ERROR: $TARGET has uncommitted changes; edit skills/ instead, then commit or discard the copy's changes"
      exit 1
    fi
    rm -rf "$TARGET"
    mkdir -p "$(dirname "$TARGET")"
    mv "$CLAUDE_DST/skills" "$TARGET"
    echo "Built $TARGET"
    ;;
  *)
    echo "Usage: scripts/build-repo-skills.sh [--check]"
    exit 2
    ;;
esac
