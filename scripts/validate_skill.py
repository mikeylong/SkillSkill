#!/usr/bin/env python3
"""Validate basic quality and packaging rules for a skill directory."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)
SCALAR_RE = re.compile(r"^(name|description):\s*(.+?)\s*$")
MAX_CORE_LINES = 160
MAX_CORE_WORDS = 1800
CLAUDE_DESCRIPTION_MAX = 250


@dataclass
class ValidationResult:
    path: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def ok(self) -> bool:
        return not self.errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a skill directory without third-party dependencies."
    )
    parser.add_argument(
        "skill_dirs",
        nargs="+",
        help="One or more skill directories to validate.",
    )
    parser.add_argument(
        "--expect-codex",
        action="store_true",
        help="Require Codex packaging files such as agents/openai.yaml.",
    )
    parser.add_argument(
        "--expect-claude",
        action="store_true",
        help="Require a Claude project-skill mirror and validate Claude-specific constraints.",
    )
    return parser.parse_args()


def load_frontmatter(skill_md: Path, result: ValidationResult) -> tuple[dict[str, str], str]:
    text = skill_md.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        result.errors.append("SKILL.md is missing YAML frontmatter.")
        return {}, text

    frontmatter_text = match.group(1)
    body = text[match.end() :].lstrip("\n")
    data: dict[str, str] = {}

    for raw_line in frontmatter_text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        scalar = SCALAR_RE.match(line)
        if not scalar:
            if line.lstrip().startswith("description:") and (
                line.rstrip().endswith("|") or line.rstrip().endswith(">")
            ):
                result.errors.append("description must be a single-line scalar, not a block value.")
            continue
        key, value = scalar.groups()
        value = value.strip()
        if key == "description" and value in {"|", ">"}:
            result.errors.append("description must be a single-line scalar, not a block value.")
            continue
        if value[:1] == value[-1:] and value[:1] in {'"', "'"}:
            value = value[1:-1]
        data[key] = value

    if "name" not in data or not data["name"].strip():
        result.errors.append("frontmatter is missing a non-empty name field.")
    if "description" not in data or not data["description"].strip():
        result.errors.append("frontmatter is missing a non-empty single-line description field.")
    elif "\n" in data["description"]:
        result.errors.append("description must stay on a single line.")

    return data, body


def check_required_files(
    skill_dir: Path, result: ValidationResult, expect_codex: bool
) -> Path | None:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        result.errors.append("missing required file: SKILL.md")
        return None

    if expect_codex:
        openai_yaml = skill_dir / "agents" / "openai.yaml"
        if not openai_yaml.is_file():
            result.errors.append("missing required Codex metadata file: agents/openai.yaml")

    return skill_md


def check_claude_mirror(skill_dir: Path, result: ValidationResult) -> Path | None:
    claude_skill_md = skill_dir / ".claude" / "skills" / "write-skills" / "SKILL.md"
    if not claude_skill_md.is_file():
        result.errors.append(
            "missing required Claude project skill: .claude/skills/write-skills/SKILL.md"
        )
        return None
    return claude_skill_md


def require_body_signal(body_lower: str, result: ValidationResult, label: str, patterns: list[str]) -> None:
    if not any(pattern in body_lower for pattern in patterns):
        result.errors.append(f"body is missing {label}.")


def validate_body(body: str, result: ValidationResult) -> None:
    body_lower = body.lower()

    require_body_signal(
        body_lower,
        result,
        "contract guidance",
        ["contract", "returns", "produces"],
    )
    require_body_signal(
        body_lower,
        result,
        "output guidance",
        ["output", "deliverable", "format", "sections"],
    )
    require_body_signal(
        body_lower,
        result,
        "edge case guidance",
        ["edge case", "edge cases"],
    )
    require_body_signal(
        body_lower,
        result,
        "example guidance",
        ["example", "examples"],
    )

    line_count = len(body.splitlines())
    word_count = len(body.split())
    if line_count > MAX_CORE_LINES:
        result.warnings.append(
            f"core body is {line_count} lines; consider moving detail into references."
        )
    if word_count > MAX_CORE_WORDS:
        result.warnings.append(
            f"core body is {word_count} words; consider shortening the core file."
        )


def validate_claude_frontmatter(data: dict[str, str], result: ValidationResult) -> None:
    description = data.get("description", "")
    if description and len(description) > CLAUDE_DESCRIPTION_MAX:
        result.errors.append(
            f"Claude description exceeds {CLAUDE_DESCRIPTION_MAX} characters."
        )


def normalize_frontmatter(
    text: str, *, description_override: str | None = None, argument_hint_override: str | None = None
) -> str:
    lines: list[str] = []
    in_frontmatter = False
    frontmatter_seen = 0

    for line in text.splitlines():
        if line == "---":
            frontmatter_seen += 1
            in_frontmatter = frontmatter_seen == 1
            lines.append(line)
            continue
        if frontmatter_seen == 1 and in_frontmatter:
            if line.startswith("description:") and description_override is not None:
                lines.append(f'description: "{description_override}"')
                continue
            if line.startswith("argument-hint:"):
                if argument_hint_override is not None:
                    lines.append(f'argument-hint: "{argument_hint_override}"')
                continue
        lines.append(line)

    if argument_hint_override is not None and frontmatter_seen >= 1:
        output: list[str] = []
        inserted = False
        inside = False
        for line in lines:
            output.append(line)
            if line == "---" and not inside:
                inside = True
                continue
            if inside and line.startswith('description: "') and not inserted:
                output.append(f'argument-hint: "{argument_hint_override}"')
                inserted = True
            elif inside and line == "---":
                inside = False
        lines = output

    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def validate_claude_skill(
    skill_dir: Path, canonical_skill_md: Path, result: ValidationResult
) -> None:
    claude_skill_md = check_claude_mirror(skill_dir, result)
    if not claude_skill_md:
        return

    claude_data, claude_body = load_frontmatter(claude_skill_md, result)
    claude_description = claude_data.get("description", "")
    validate_claude_frontmatter(claude_data, result)
    if "argument-hint:" not in claude_skill_md.read_text(encoding="utf-8"):
        result.warnings.append(
            "Claude mirror is missing argument-hint; slash-command usage may be less clear."
        )
    if claude_body:
        validate_body(claude_body, result)

    canonical_text = canonical_skill_md.read_text(encoding="utf-8")
    claude_text = claude_skill_md.read_text(encoding="utf-8")
    expected_claude = normalize_frontmatter(
        canonical_text,
        description_override=claude_description,
        argument_hint_override=claude_data.get("argument-hint", "[request or path]"),
    )
    expected_claude = expected_claude.replace(
        "[references/rubric.md](references/rubric.md)",
        "[../../../references/rubric.md](../../../references/rubric.md)",
    ).replace(
        "[references/review-checklist.md](references/review-checklist.md)",
        "[../../../references/review-checklist.md](../../../references/review-checklist.md)",
    ).replace(
        "## Codex Packaging",
        "## Packaging Notes",
    ).replace(
        "If local files are available, validate Codex-oriented packages with `python3 scripts/validate_skill.py <skill-dir>` before finishing.",
        "When local files are available, validate both canonical and Claude packaging with `python3 scripts/validate_skill.py --expect-codex --expect-claude .`.",
    )

    if claude_text != expected_claude:
        result.errors.append(
            "Claude mirror has drifted from the canonical skill beyond the approved packaging differences."
        )


def validate_skill_dir(skill_dir: Path, expect_codex: bool, expect_claude: bool) -> ValidationResult:
    result = ValidationResult(path=skill_dir)
    skill_md = check_required_files(skill_dir, result, expect_codex)
    if not skill_md:
        return result

    data, body = load_frontmatter(skill_md, result)
    if body:
        validate_body(body, result)

    if expect_claude:
        if (skill_dir / ".claude" / "skills").exists():
            validate_claude_skill(skill_dir, skill_md, result)
        elif skill_dir.parts[-3:] == (".claude", "skills", "write-skills"):
            validate_claude_frontmatter(data, result)
        else:
            validate_claude_frontmatter(data, result)

    return result


def main() -> int:
    args = parse_args()
    overall_ok = True

    for raw_path in args.skill_dirs:
        skill_dir = Path(raw_path).resolve()
        result = validate_skill_dir(
            skill_dir,
            expect_codex=args.expect_codex,
            expect_claude=args.expect_claude,
        )
        status = "PASS" if result.ok() else "FAIL"
        print(f"{status} {result.path}")
        for error in result.errors:
            print(f"  ERROR: {error}")
        for warning in result.warnings:
            print(f"  WARN: {warning}")
        overall_ok = overall_ok and result.ok()

    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
