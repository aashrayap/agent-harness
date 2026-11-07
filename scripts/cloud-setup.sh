#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SKILLS="$ROOT/.claude/skills"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"

usage() { echo "Usage: scripts/cloud-setup.sh [--check] [claude-home, default \${CLAUDE_CONFIG_DIR:-\$HOME/.claude}]"; exit 2; }
check=0
[[ "${1:-}" == --check ]] && { check=1; shift; }
[[ $# -le 1 ]] || usage
HOME_DIR="${1:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}}"
DEST="$HOME_DIR/skills"
MANIFEST="$HOME_DIR/dot-agent-cloud"

older() { [[ "$1" != "$2" && "$(printf '%s\n%s\n' "$1" "$2" | sort -V | head -1)" == "$1" ]]; }

verify() {
  local delivered problems=0 name
  delivered="$(sed -n 's/^version //p' "$MANIFEST" 2>/dev/null || true)"
  if [[ -z "$delivered" ]]; then
    echo "ERROR: no dot-agent skills in $DEST; run scripts/cloud-setup.sh"
    return 1
  fi
  if older "$delivered" "$VERSION"; then
    echo "ERROR: $DEST has dot-agent $delivered, older than $VERSION; run scripts/cloud-setup.sh"
    return 1
  fi
  older "$VERSION" "$delivered" && echo "WARNING: $DEST has dot-agent $delivered, newer than this checkout's $VERSION"
  for name in $(sed -n 's/^skill //p' "$MANIFEST"); do
    diff -rq -x __pycache__ "$SKILLS/$name" "$DEST/$name" >/dev/null 2>&1 \
      || { echo "ERROR: skill $name differs from dot-agent $VERSION"; problems=1; }
  done
  [[ $problems -eq 0 ]] && echo "$DEST has dot-agent $delivered skills"
  return $problems
}

if [[ $check -eq 1 ]]; then
  verify
  exit
fi

mine=" "
[[ -f "$MANIFEST" ]] && mine=" $(sed -n 's/^skill //p' "$MANIFEST" | tr '\n' ' ') "
for dir in "$SKILLS"/*/; do
  name="$(basename "$dir")"
  if [[ -e "$DEST/$name" && "$mine" != *" $name "* ]]; then
    echo "ERROR: $DEST/$name is not dot-agent's; it will not be overwritten"
    exit 1
  fi
done

mkdir -p "$DEST"
for name in $mine; do rm -rf "${DEST:?}/$name"; done
{
  echo "version $VERSION"
  for dir in "$SKILLS"/*/; do
    name="$(basename "$dir")"
    echo "skill $name"
    cp -R "$dir" "$DEST/$name"
  done
} > "$MANIFEST"

verify
