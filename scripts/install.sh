#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Install skillskill for Codex and/or Claude.

Usage:
  ./scripts/install.sh [--codex] [--claude] [--all] [--force]

Options:
  --codex   Install a clean Codex runtime package into the local Codex skills directory.
  --claude  Install into the local Claude personal skills directory.
  --all     Install both Codex and Claude targets.
  --force   Replace an existing install target.
  -h, --help

Default behavior:
  If no target flag is given, install Codex only.
EOF
}

force=0
install_codex=0
install_claude=0

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
codex_home="${CODEX_HOME:-$HOME/.codex}"
claude_home="${CLAUDE_HOME:-$HOME/.claude}"

install_target() {
  local label="$1"
  local source="$2"
  local target="$3"

  mkdir -p "$(dirname "$target")"

  if [[ ! -e "$source" && ! -L "$source" ]]; then
    echo "$label source does not exist: $source" >&2
    exit 1
  fi

  if [[ -L "$target" ]]; then
    local existing_target
    existing_target="$(readlink "$target")"
    if [[ "$existing_target" == "$source" ]]; then
      echo "$label already installed at $target"
      return
    fi
  fi

  if [[ -e "$target" || -L "$target" ]]; then
    if [[ "$force" -eq 1 ]]; then
      rm -rf "$target"
    else
      echo "$label install target already exists: $target" >&2
      echo "Re-run with --force to replace it." >&2
      exit 1
    fi
  fi

  ln -s "$source" "$target"
  echo "$label installed"
  echo "  source: $source"
  echo "  target: $target"
}

install_codex_target() {
  local source="$repo_root"
  local target="$codex_home/skills/skillskill"

  mkdir -p "$(dirname "$target")"

  if [[ -e "$target" || -L "$target" ]]; then
    if [[ "$force" -eq 1 ]]; then
      rm -rf "$target"
    else
      echo "Codex install target already exists: $target" >&2
      echo "Re-run with --force to replace it." >&2
      exit 1
    fi
  fi

  mkdir -p "$target"

  cp "$source/SKILL.md" "$target/SKILL.md"
  cp "$source/README.md" "$target/README.md"
  cp "$source/SkillSkill-SocialMedia.png" "$target/SkillSkill-SocialMedia.png"
  cp "$source/skillskill_mascot.png" "$target/skillskill_mascot.png"

  cp -R "$source/agents" "$target/agents"
  cp -R "$source/references" "$target/references"
  cp -R "$source/scripts" "$target/scripts"

  echo "Codex installed"
  echo "  source: $source"
  echo "  target: $target"
}

if [[ "$install_codex" -eq 1 ]]; then
  install_codex_target
fi

if [[ "$install_claude" -eq 1 ]]; then
  install_target "Claude" "$repo_root/.claude/skills/skillskill" "$claude_home/skills/skillskill"
fi
