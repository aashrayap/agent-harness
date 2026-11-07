#!/usr/bin/env bash
set -euo pipefail

[[ -z "${CLAUDECODE:-}" ]] || { echo "FAIL: launches Codex; run from Codex, not Claude Code" >&2; exit 1; }

probe_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
MODEL="$(sed -n 's/^model = "\(.*\)"/\1/p' "$probe_root/codex/config.toml")"
EFFORT="$(sed -n 's/^model_reasoning_effort = "\(.*\)"/\1/p' "$probe_root/codex/config.toml")"
PROVIDER="openai"
EXPECTED='{"ok":true,"probe":"codex-delegation"}'

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

codex_bin="${CODEX_BIN:-}"
if [[ -z "$codex_bin" && -x "/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex" ]]; then
  codex_bin="/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex"
fi
if [[ -z "$codex_bin" ]]; then
  codex_bin="$(command -v codex || true)"
fi
if [[ -z "$codex_bin" ]]; then
  fail "codex CLI not found — Codex delegation is unavailable"
fi
if ! "$codex_bin" exec review --help >/dev/null 2>&1; then
  fail "codex exec review is unavailable (Codex CLI too old?)"
fi

run_with_timeout() {
  local seconds="$1"
  shift
  if command -v timeout >/dev/null 2>&1; then
    timeout "$seconds" "$@"
  elif command -v gtimeout >/dev/null 2>&1; then
    gtimeout "$seconds" "$@"
  else
    "$@"
  fi
}

scratch="$(mktemp -d "${TMPDIR:-/tmp}/dot-agent-codex-probe.XXXXXX")"
trap 'rm -rf "$scratch"' EXIT
reply_file="$scratch/reply.txt"
events_file="$scratch/events.txt"
metadata_file="$scratch/metadata.txt"
expected_file="$scratch/expected.txt"
expected_newline_file="$scratch/expected-newline.txt"
prompt="Reply with exactly this JSON object and nothing else: $EXPECTED"

printf '%s' "$EXPECTED" > "$expected_file"
printf '%s\n' "$EXPECTED" > "$expected_newline_file"

if ! run_with_timeout 180 "$codex_bin" exec \
  --model "$MODEL" \
  --config "model_reasoning_effort=$EFFORT" \
  --ephemeral \
  --skip-git-repo-check \
  --sandbox read-only \
  --output-last-message "$reply_file" \
  "$prompt" >"$events_file" 2>"$metadata_file"; then
  sed -n '1,80p' "$metadata_file" >&2
  fail "codex exec exact-model probe failed"
fi

[[ -f "$reply_file" ]] || fail "probe produced no reply file"
if ! cmp -s "$expected_file" "$reply_file" \
  && ! cmp -s "$expected_newline_file" "$reply_file"; then
  fail "probe reply was not the exact expected JSON (apart from one CLI newline)"
fi

observed_model="$(sed -n 's/^model: //p' "$metadata_file" | head -n 1)"
observed_provider="$(sed -n 's/^provider: //p' "$metadata_file" | head -n 1)"
session_id="$(sed -n 's/^session id: //p' "$metadata_file" | head -n 1)"
[[ "$observed_model" == "$MODEL" ]] \
  || fail "request model evidence missing or substituted: ${observed_model:-<missing>}"
[[ "$observed_provider" == "$PROVIDER" ]] \
  || fail "request provider evidence missing or substituted: ${observed_provider:-<missing>}"
[[ "$session_id" =~ ^[0-9a-f-]{36}$ ]] \
  || fail "request session evidence missing or malformed: ${session_id:-<missing>}"

codex_home="${CODEX_HOME:-$HOME/.codex}"
for session_root in "$codex_home/sessions" "$codex_home/archived_sessions"; do
  [[ -d "$session_root" ]] || continue
  if find "$session_root" -type f -name "*${session_id}*.jsonl" \
    -print -quit | grep -q .; then
    fail "ephemeral probe persisted session $session_id and can pollute session history"
  fi
done

echo "PASS: exact Codex delegation reply"
echo "EVIDENCE: request model=$observed_model effort=$EFFORT provider=$observed_provider session=$session_id"
echo "EVIDENCE: persistence=ephemeral; no persisted session file"
echo "LIMITATION: response-side identity unavailable; no identity inferred from response text"
