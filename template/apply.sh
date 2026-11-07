#!/usr/bin/env bash
set -euo pipefail

TEMPLATE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
[[ $# -eq 1 && -d "$1" ]] && top="$(git -C "$1" rev-parse --show-toplevel 2>/dev/null)" \
  && [[ "$top" == "$(cd "$1" && pwd -P)" ]] || {
  echo "usage: $0 <git repo>   adds the starter files the repo lacks; never overwrites" >&2
  exit 1
}
REPO="$(cd "$1" && pwd -P)"

for relative in README.md AGENTS.md CLAUDE.md CONSTRAINTS.tsv GLOSSARY.md VERIFY.md \
  VERSION RELEASES.md scripts/check scripts/private-boundary.py scripts/readme-check.py \
  scripts/doc-fresh.py scripts/diagram-lint.py .github/workflows/ci.yml; do
  target="$REPO/$relative"
  if [[ -e "$target" || -L "$target" ]]; then
    echo "kept   $relative"
    continue
  fi
  mkdir -p "$(dirname "$target")"
  cp -p "$TEMPLATE/$relative" "$target"
  echo "added  $relative"
done
