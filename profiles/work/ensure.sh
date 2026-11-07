#!/usr/bin/env bash
set -euo pipefail

echo "work profile: portable overlay active"

hook="${DOT_AGENT_STATE_HOME:-$HOME/.dot-agent/state}/work-ensure.sh"
if [[ -f "$hook" ]]; then
  bash "$hook"
fi
