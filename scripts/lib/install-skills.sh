profile_skill_skipped() {
  local skill_name="$1"
  local list="$PROFILES_SRC/$MACHINE_PROFILE/provided-skills"
  [[ -n "$MACHINE_PROFILE" && -f "$list" ]] || return 1
  sed 's/^[[:space:]]*//;s/[[:space:]]*$//' "$list" | grep -qx "$skill_name"
}

backup_path() {
  local path="$1"
  local rel="$2"

  if [[ -e "$path" || -L "$path" ]]; then
    mkdir -p "$BACKUP_ROOT/$(dirname "$rel")"
    mv "$path" "$BACKUP_ROOT/$rel"
  fi
}

copy_dir_contents() {
  local src_dir="$1"
  local dst_dir="$2"

  mkdir -p "$dst_dir"
  cp -R "$src_dir"/. "$dst_dir"
  find "$dst_dir" -type d -name __pycache__ -prune -exec rm -rf {} +
  find "$dst_dir" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
}

sync_dir_from_temp() {
  local tmp_dir="$1"
  local dst_dir="$2"
  local rel="$3"

  if [[ -d "$dst_dir" && ! -L "$dst_dir" ]] \
    && [[ -z "$(find "$dst_dir" -type l -print -quit)" ]] \
    && diff -qr "$tmp_dir" "$dst_dir" >/dev/null 2>&1; then
    rm -rf "$tmp_dir"
    return
  fi

  backup_path "$dst_dir" "$rel"
  mkdir -p "$(dirname "$dst_dir")"
  mv "$tmp_dir" "$dst_dir"
}

runtime_skill_entry() {
  local runtime="$1"
  local skill_dir="$2"

  if [[ -f "$skill_dir/$runtime/SKILL.md" ]]; then
    printf '%s\n' "$runtime/SKILL.md"
    return
  fi

  if [[ -f "$skill_dir/SKILL.md" ]]; then
    printf '%s\n' "SKILL.md"
  fi
}

shared_payload_exists() {
  local path="$1"
  [[ -d "$path" ]] && [[ -n "$(find "$path" -type f -print -quit 2>/dev/null)" ]]
}

install_codex_skill_runtime() {
  local skill_dir="$1"
  local entry="$2"
  local dst_root="$3"
  local rel_prefix="$4"
  local source="$skill_dir/$entry"
  local source_parent
  local tmp_dir
  local dst_dir

  source_parent="$(dirname "$source")"
  tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/dot-agent-codex-skill.XXXXXX")"
  dst_dir="$dst_root/skills/$(basename "$skill_dir")"

  if [[ "$source_parent" == "$skill_dir" ]]; then
    cp "$source" "$tmp_dir/SKILL.md"
  else
    copy_dir_contents "$source_parent" "$tmp_dir"
    if [[ ! -f "$tmp_dir/SKILL.md" ]]; then
      echo "WARN: Codex skill payload for $(basename "$skill_dir") did not produce SKILL.md"
      rm -rf "$tmp_dir"
      return
    fi
  fi

  for shared_dir in scripts assets references shared agents playbooks principles; do
    if shared_payload_exists "$skill_dir/$shared_dir"; then
      copy_dir_contents "$skill_dir/$shared_dir" "$tmp_dir/$shared_dir"
    fi
  done
  for root_file in "$skill_dir"/*.md; do
    if [[ -f "$root_file" && "$(basename "$root_file")" != SKILL.md ]]; then
      cp "$root_file" "$tmp_dir/"
    fi
  done

  sync_dir_from_temp "$tmp_dir" "$dst_dir" "$rel_prefix"
}

link_skill_runtime() {
  local runtime="$1"
  local dst_root="$2"
  local skill_dir="$3"
  local skill_name
  local rel_prefix
  local entry=""

  skill_name="$(basename "$skill_dir")"
  rel_prefix=".${runtime}/skills/$skill_name"
  entry="$(runtime_skill_entry "$runtime" "$skill_dir")"

  if [[ -z "$entry" ]]; then
    echo "WARN: No ${runtime} entry for skill $skill_name"
    return
  fi

  install_codex_skill_runtime "$skill_dir" "$entry" "$dst_root" "$rel_prefix"
}

link_skills() {
  local skill_file
  local skill_dir
  local skill_name
  local seen=" "
  while IFS= read -r skill_file; do
    skill_dir="$(dirname "$skill_file")"
    skill_name="$(basename "$skill_dir")"
    if [[ "$seen" == *" $skill_name "* ]]; then
      echo "ERROR: duplicate skill name across categories: $skill_name"
      exit 1
    fi
    seen="$seen$skill_name "
    if profile_skill_skipped "$skill_name"; then
      continue
    fi
    if [[ "$INSTALL_CODEX" == "1" ]]; then
      link_skill_runtime "codex" "$CODEX_DST" "$skill_dir"
    fi
    if [[ "$INSTALL_CLAUDE" == "1" ]]; then
      link_skill_runtime "claude" "$CLAUDE_DST" "$skill_dir"
    fi
  done < <(find "$SKILLS_SRC" -maxdepth 3 -mindepth 3 -type f -name SKILL.md | sort)
}
