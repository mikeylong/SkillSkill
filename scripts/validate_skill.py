#!/usr/bin/env python3
"""Run dependency-free static checks on one or more skill packages."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote, urlsplit


FRONTMATTER_RE = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*(?:\n|\Z)", re.DOTALL)
TOP_LEVEL_KEY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):(?:[ \t]*(.*))?$")
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
NUMBER_RE = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?\Z")
MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]\n]*\]\(([^)\n]+)\)")
REFERENCE_LINK_RE = re.compile(r"^[ \t]*\[[^\]\n]+\]:[ \t]*(\S+)", re.MULTILINE)
HEADING_RE = re.compile(r"^(#{2,6})[ \t]+(.+?)[ \t]*#*[ \t]*$", re.MULTILINE)

MAX_SKILL_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
CLAUDE_DESCRIPTION_MAX = 250
MAX_CORE_LINES = 160
MAX_CORE_WORDS = 1800
CODEX_FRONTMATTER_KEYS = {"name", "description", "license", "allowed-tools", "metadata"}
QUALITY_HEADINGS = {
    "contract or output guidance": re.compile(
        r"\b(contract|output|outputs|deliverable|deliverables|response format|return format)\b",
        re.IGNORECASE,
    ),
    "edge cases or fallbacks": re.compile(
        r"\b(edge cases?|fallbacks?|failure modes?|exceptions?)\b", re.IGNORECASE
    ),
    "an example or pattern anchor": re.compile(
        r"\b(examples?|patterns?|samples?|representative requests?)\b", re.IGNORECASE
    ),
}


@dataclass
class ValidationResult:
    path: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def ok(self) -> bool:
        return not self.errors


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run static structure and packaging checks without third-party dependencies."
    )
    parser.add_argument("skill_dirs", nargs="+", help="One or more skill directories to check.")
    parser.add_argument(
        "--expect-codex",
        action="store_true",
        help="Require and statically check Codex agents/openai.yaml metadata.",
    )
    parser.add_argument(
        "--expect-claude",
        action="store_true",
        help="Apply Claude's description limit to each target package.",
    )
    parser.add_argument(
        "--strict-quality",
        action="store_true",
        help="Require non-empty contract/output, edge/fallback, and example/pattern sections.",
    )
    return parser.parse_args(argv)


def _append_once(items: list[str], message: str) -> None:
    if message not in items:
        items.append(message)


def _strip_yaml_comment(value: str) -> str:
    quote: str | None = None
    escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if quote == '"' and char == "\\":
            escaped = True
            continue
        if char in {'"', "'"}:
            if quote is None:
                quote = char
            elif quote == char:
                if char == "'" and index + 1 < len(value) and value[index + 1] == "'":
                    continue
                quote = None
            continue
        if char == "#" and quote is None and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
    return value.rstrip()


def _parse_string_scalar(
    raw_value: str, field_name: str, result: ValidationResult
) -> str | None:
    value = _strip_yaml_comment(raw_value.strip())
    if not value:
        result.errors.append(f"{field_name} must be a non-empty string.")
        return None
    if value in {"|", ">", "|-", "|+", ">-", ">+"}:
        result.errors.append(f"{field_name} must be a single-line string, not a block value.")
        return None
    if value.startswith('"'):
        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            result.errors.append(f"{field_name} has an invalid quoted string value.")
            return None
        if not isinstance(parsed, str):
            result.errors.append(f"{field_name} must be a string.")
            return None
        return parsed
    if value.startswith("'"):
        if len(value) < 2 or not value.endswith("'"):
            result.errors.append(f"{field_name} has an invalid quoted string value.")
            return None
        inner = value[1:-1]
        if re.search(r"(?<!')'(?!')", inner):
            result.errors.append(f"{field_name} has an invalid quoted string value.")
            return None
        return inner.replace("''", "'")
    if value.endswith(('"', "'")) or value[0] in "[{":
        result.errors.append(f"{field_name} must be a string.")
        return None
    if re.search(r":[ \t]", value):
        result.errors.append(f"{field_name} has an invalid unquoted scalar value.")
        return None
    if value.lower() in {"null", "~", "true", "false", ".nan", ".inf", "-.inf"} or NUMBER_RE.fullmatch(value):
        result.errors.append(f"{field_name} must be a string.")
        return None
    return value


def load_frontmatter(skill_md: Path, result: ValidationResult) -> tuple[dict[str, str], str]:
    try:
        text = skill_md.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        result.errors.append(f"could not read SKILL.md: {exc}")
        return {}, ""
    match = FRONTMATTER_RE.match(text)
    if not match:
        result.errors.append("SKILL.md is missing valid YAML frontmatter delimiters.")
        return {}, text

    raw_entries: dict[str, str | None] = {}
    current_container: str | None = None
    for line_number, raw_line in enumerate(match.group(1).splitlines(), start=2):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if raw_line[0].isspace():
            if current_container is None:
                result.errors.append(f"invalid frontmatter indentation on line {line_number}.")
            elif current_container in {"name", "description"}:
                _append_once(
                    result.errors,
                    f"{current_container} must be a single-line string, not a nested or block value.",
                )
            continue
        current_container = None
        key_match = TOP_LEVEL_KEY_RE.match(raw_line)
        if not key_match:
            result.errors.append(f"invalid frontmatter entry on line {line_number}.")
            continue
        key, raw_value = key_match.groups()
        if key in raw_entries:
            result.errors.append(f"duplicate frontmatter key: {key}")
            continue
        raw_value = (raw_value or "").strip()
        raw_entries[key] = raw_value or None
        if not raw_value or raw_value in {"|", ">", "|-", "|+", ">-", ">+"}:
            current_container = key

    data: dict[str, str] = {}
    for key in ("name", "description"):
        if key not in raw_entries:
            result.errors.append(f"frontmatter is missing required key: {key}")
            continue
        raw_value = raw_entries[key]
        if raw_value is None:
            result.errors.append(f"{key} must be a non-empty single-line string.")
            continue
        parsed = _parse_string_scalar(raw_value, key, result)
        if parsed is not None:
            data[key] = parsed.strip()

    name = data.get("name", "")
    if name:
        if len(name) > MAX_SKILL_NAME_LENGTH:
            result.errors.append(
                f"name exceeds {MAX_SKILL_NAME_LENGTH} characters ({len(name)} found)."
            )
        if not NAME_RE.fullmatch(name):
            result.errors.append(
                "name must be hyphen-case: lowercase letters or digits separated by single hyphens."
            )
    description = data.get("description", "")
    if description:
        if len(description) > MAX_DESCRIPTION_LENGTH:
            result.errors.append(
                f"description exceeds {MAX_DESCRIPTION_LENGTH} characters ({len(description)} found)."
            )
        if "<" in description or ">" in description:
            result.errors.append("description cannot contain angle brackets (< or >).")

    return data | {"__keys__": "\0".join(raw_entries)}, text[match.end() :].lstrip("\n")


def _mask_markdown_code(markdown: str) -> str:
    output: list[str] = []
    fence: str | None = None
    for line in markdown.splitlines():
        marker_match = re.match(r"^[ \t]*(```+|~~~+)", line)
        if marker_match:
            marker = marker_match.group(1)[0]
            fence = None if fence == marker else marker if fence is None else fence
            output.append("")
        elif fence is not None:
            output.append("")
        else:
            output.append(re.sub(r"`[^`\n]*`", "", line))
    return "\n".join(output)


def _link_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        return target[1 : target.index(">")]
    return target.split(maxsplit=1)[0]


def check_markdown_links(skill_md: Path, body: str, result: ValidationResult) -> None:
    markdown = _mask_markdown_code(body)
    targets = [match.group(1) for match in MARKDOWN_LINK_RE.finditer(markdown)]
    targets.extend(match.group(1) for match in REFERENCE_LINK_RE.finditer(markdown))
    for raw_target in targets:
        target = _link_target(raw_target)
        if not target or target.startswith(("#", "//")):
            continue
        parsed = urlsplit(target)
        if parsed.scheme:
            continue
        path_text = unquote(parsed.path).replace("\\ ", " ")
        if not path_text:
            continue
        linked_path = Path(path_text)
        if not linked_path.is_absolute():
            linked_path = skill_md.parent / linked_path
        if not linked_path.exists():
            result.errors.append(f"broken local Markdown link: {target}")


def check_no_nested_skill_files(skill_dir: Path, result: ValidationResult) -> None:
    root_skill = skill_dir / "SKILL.md"
    for nested_skill in skill_dir.rglob("SKILL.md"):
        if nested_skill == root_skill:
            continue
        result.errors.append(
            f"installable package contains nested active skill: {nested_skill.relative_to(skill_dir)}"
        )


def _parse_openai_interface(openai_yaml: Path, result: ValidationResult) -> dict[str, str]:
    try:
        lines = openai_yaml.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        result.errors.append(f"could not read agents/openai.yaml: {exc}")
        return {}
    interface_start: int | None = None
    for index, line in enumerate(lines):
        if line == "interface:":
            if interface_start is not None:
                result.errors.append("agents/openai.yaml contains duplicate interface mappings.")
            interface_start = index
    if interface_start is None:
        result.errors.append("agents/openai.yaml is missing the interface mapping.")
        return {}

    interface: dict[str, str] = {}
    for line_number, line in enumerate(lines[interface_start + 1 :], start=interface_start + 2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line[0].isspace():
            break
        stripped = line.lstrip()
        entry = TOP_LEVEL_KEY_RE.match(stripped)
        if not entry:
            result.errors.append(f"invalid interface entry in agents/openai.yaml on line {line_number}.")
            continue
        key, raw_value = entry.groups()
        if key in interface:
            result.errors.append(f"duplicate interface key in agents/openai.yaml: {key}")
            continue
        scalar_text = (raw_value or "").strip()
        if (
            len(scalar_text) < 2
            or scalar_text[0] not in {'"', "'"}
            or scalar_text[-1] != scalar_text[0]
        ):
            result.errors.append(
                f"interface.{key} must use a quoted string value in agents/openai.yaml."
            )
        parsed = _parse_string_scalar(scalar_text, f"interface.{key}", result)
        if parsed is not None:
            interface[key] = parsed.strip()
    return interface


def check_codex_metadata(skill_dir: Path, name: str, result: ValidationResult) -> None:
    openai_yaml = skill_dir / "agents" / "openai.yaml"
    if not openai_yaml.is_file():
        result.errors.append("missing required Codex metadata file: agents/openai.yaml")
        return
    interface = _parse_openai_interface(openai_yaml, result)
    for key in ("display_name", "short_description", "default_prompt"):
        if not interface.get(key):
            result.errors.append(f"agents/openai.yaml is missing interface.{key}.")
    short_description = interface.get("short_description", "")
    if short_description and not 25 <= len(short_description) <= 64:
        result.errors.append(
            "interface.short_description must be 25-64 characters "
            f"({len(short_description)} found)."
        )
    default_prompt = interface.get("default_prompt", "")
    if name and default_prompt and f"${name}" not in default_prompt:
        result.errors.append(f"interface.default_prompt must contain ${name}.")
    for key in ("icon_small", "icon_large"):
        icon = interface.get(key)
        if not icon:
            continue
        parsed = urlsplit(icon)
        icon_path = Path(unquote(parsed.path))
        if parsed.scheme or icon_path.is_absolute():
            result.errors.append(f"interface.{key} must reference a relative local file.")
        elif not (skill_dir / icon_path).is_file():
            result.errors.append(f"interface.{key} references a missing file: {icon}")


def validate_strict_quality(body: str, result: ValidationResult) -> None:
    matches = list(HEADING_RE.finditer(body))
    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        sections.append((match.group(2).strip(), body[match.end() : end].strip()))
    for label, heading_pattern in QUALITY_HEADINGS.items():
        if not any(heading_pattern.search(heading) and content for heading, content in sections):
            result.errors.append(f"strict quality check requires a non-empty section for {label}.")


def validate_skill_dir(
    skill_dir: Path,
    expect_codex: bool = False,
    expect_claude: bool = False,
    strict_quality: bool = False,
) -> ValidationResult:
    skill_dir = skill_dir.resolve()
    result = ValidationResult(path=skill_dir)
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        result.errors.append("missing required file: SKILL.md")
        return result

    check_no_nested_skill_files(skill_dir, result)
    data, body = load_frontmatter(skill_md, result)
    keys = set(data.pop("__keys__", "").split("\0")) - {""}
    if expect_codex:
        unexpected = sorted(keys - CODEX_FRONTMATTER_KEYS)
        if unexpected:
            result.errors.append(
                "unexpected Codex frontmatter key(s): "
                + ", ".join(unexpected)
                + "; allowed keys are: "
                + ", ".join(sorted(CODEX_FRONTMATTER_KEYS))
            )
        check_codex_metadata(skill_dir, data.get("name", ""), result)
    if expect_claude and len(data.get("description", "")) > CLAUDE_DESCRIPTION_MAX:
        result.errors.append(
            f"Claude description exceeds {CLAUDE_DESCRIPTION_MAX} characters "
            f"({len(data['description'])} found)."
        )

    check_markdown_links(skill_md, body, result)
    if strict_quality:
        validate_strict_quality(body, result)
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
    return result


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    overall_ok = True
    for raw_path in args.skill_dirs:
        result = validate_skill_dir(
            Path(raw_path),
            expect_codex=args.expect_codex,
            expect_claude=args.expect_claude,
            strict_quality=args.strict_quality,
        )
        print(f"STATIC {'PASS' if result.ok() else 'FAIL'} {result.path}")
        for error in result.errors:
            print(f"  ERROR: {error}")
        for warning in result.warnings:
            print(f"  WARN: {warning}")
        overall_ok = overall_ok and result.ok()
    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
