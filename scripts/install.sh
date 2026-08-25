#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Install skillskill for Codex and/or Claude.

Usage:
  ./scripts/install.sh [--codex] [--claude] [--all] [--force]

Options:
  --codex   Install a stable copy in the personal Codex skills directory.
  --claude  Install a stable copy in the personal Claude skills directory.
  --all     Install both personal copies.
  --force   Replace existing install targets after validation and staging.
  -h, --help

Default behavior:
  If no target flag is given, install Codex only.
EOF
}

force=0
install_codex=0
install_claude=0
temp_paths=()
active_backup=""
active_target=""

cleanup_temp_paths() {
  local path

  if [[ -n "$active_backup" && ( -e "$active_backup" || -L "$active_backup" ) ]]; then
    if [[ ! -e "$active_target" && ! -L "$active_target" ]]; then
      mv -- "$active_backup" "$active_target"
    else
      rm -rf -- "$active_backup"
    fi
  fi

  for path in "${temp_paths[@]-}"; do
    if [[ -n "$path" ]]; then
      rm -rf -- "$path"
    fi
  done
}

trap cleanup_temp_paths EXIT

while [[ $# -gt 0 ]]; do
  case "$1" in
    --codex)
      install_codex=1
      shift
      ;;
    --claude)
      install_claude=1
      shift
      ;;
    --all)
      install_codex=1
      install_claude=1
      shift
      ;;
    --force)
      force=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ "$install_codex" -eq 0 && "$install_claude" -eq 0 ]]; then
  install_codex=1
fi

repo_root="$(cd "$(dirname "$0")/.." && pwd -P)"
source_dir="$repo_root/packages/codex/skillskill"
validator="$repo_root/scripts/validate_skill.py"
codex_home="${CODEX_HOME:-$HOME/.codex}"
claude_home="${CLAUDE_HOME:-$HOME/.claude}"

validate_source() {
  if [[ ! -d "$source_dir" ]]; then
    echo "Canonical source does not exist: $source_dir" >&2
    exit 1
  fi

  if [[ ! -f "$validator" ]]; then
    echo "Validator does not exist: $validator" >&2
    exit 1
  fi

  echo "Validating canonical package"
  python3 "$validator" --expect-codex --expect-claude --strict-quality "$source_dir"
}

check_target() {
  local label="$1"
  local target="$2"

  if [[ ( -e "$target" || -L "$target" ) && "$force" -ne 1 ]]; then
    echo "$label install target already exists: $target" >&2
    echo "Re-run with --force to replace it." >&2
    return 1
  fi
}

install_copy() {
  local label="$1"
  local target="$2"
  local target_parent
  local target_name
  local stage
  local backup=""

  target_parent="$(dirname "$target")"
  target_name="$(basename "$target")"
  mkdir -p "$target_parent"

  if [[ ( -e "$target" || -L "$target" ) && "$force" -ne 1 ]]; then
    echo "$label install target appeared after preflight: $target" >&2
    echo "Re-run with --force to replace it." >&2
    return 1
  fi

  stage="$(mktemp -d "$target_parent/.${target_name}.stage.XXXXXX")"
  temp_paths+=("$stage")

  if ! cp -R "$source_dir/." "$stage/"; then
    echo "Could not stage the $label package." >&2
    return 1
  fi

  if ! python3 "$validator" --expect-codex --expect-claude --strict-quality "$stage"; then
    echo "Staged $label package did not pass validation." >&2
    return 1
  fi

  if [[ -e "$target" || -L "$target" ]]; then
    backup="$(mktemp -d "$target_parent/.${target_name}.backup.XXXXXX")"
    rmdir "$backup"
    active_backup="$backup"
    active_target="$target"
    if ! mv -- "$target" "$backup"; then
      active_backup=""
      active_target=""
      echo "Could not prepare the existing $label target for replacement." >&2
      return 1
    fi
  fi

  if ! mv -- "$stage" "$target"; then
    if [[ -n "$backup" && ( -e "$backup" || -L "$backup" ) ]]; then
      mv -- "$backup" "$target"
    fi
    active_backup=""
    active_target=""
    echo "Could not activate the staged $label package." >&2
    return 1
  fi

  if [[ -n "$backup" ]]; then
    rm -rf -- "$backup"
    active_backup=""
    active_target=""
  fi

  echo "$label installed"
  echo "  source: $source_dir"
  echo "  target: $target"
}

if [[ "$install_codex" -eq 1 ]]; then
  check_target "Codex" "$codex_home/skills/skillskill"
fi

if [[ "$install_claude" -eq 1 ]]; then
  check_target "Claude" "$claude_home/skills/skillskill"
fi

validate_source

if [[ "$install_codex" -eq 1 ]]; then
  install_copy "Codex" "$codex_home/skills/skillskill"
fi

if [[ "$install_claude" -eq 1 ]]; then
  install_copy "Claude" "$claude_home/skills/skillskill"
fi
