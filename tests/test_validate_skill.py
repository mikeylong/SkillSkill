from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate_skill.py"
PACKAGE_VALIDATOR_PATH = (
    REPO_ROOT / "packages" / "codex" / "skillskill" / "scripts" / "validate_skill.py"
)
FIXTURES = REPO_ROOT / "tests" / "fixtures"
EVAL_MANIFEST = REPO_ROOT / "tests" / "evals" / "skillskill_behavior_cases.json"

spec = importlib.util.spec_from_file_location("skillskill_validator", VALIDATOR_PATH)
validator = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = validator
spec.loader.exec_module(validator)


class ValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

    def stage_fixture(self, fixture_name: str, package_name: str = "fixture") -> Path:
        package = self.root / package_name
        package.mkdir(parents=True)
        shutil.copyfile(
            FIXTURES / fixture_name / "SKILL.fixture.md", package / "SKILL.md"
        )
        return package

    def write_skill(self, text: str, package_name: str = "skill") -> Path:
        package = self.root / package_name
        package.mkdir(parents=True)
        (package / "SKILL.md").write_text(text, encoding="utf-8")
        return package

    def write_codex_metadata(self, package: Path, body: str) -> None:
        metadata = package / "agents" / "openai.yaml"
        metadata.parent.mkdir(parents=True, exist_ok=True)
        metadata.write_text(body, encoding="utf-8")

    def test_existing_valid_fixture_passes_default_and_strict_checks(self) -> None:
        package = self.stage_fixture("valid-skill")
        self.assertTrue(validator.validate_skill_dir(package).ok())
        self.assertTrue(validator.validate_skill_dir(package, strict_quality=True).ok())

    def test_missing_quality_sections_only_fail_in_strict_mode(self) -> None:
        package = self.stage_fixture("bad-missing-sections")
        self.assertTrue(validator.validate_skill_dir(package).ok())
        result = validator.validate_skill_dir(package, strict_quality=True)
        self.assertFalse(result.ok())
        self.assertEqual(3, len([error for error in result.errors if "strict quality" in error]))

    def test_keyword_stuffing_does_not_satisfy_strict_quality(self) -> None:
        package = self.write_skill(
            """---
name: keyword-stuffing
description: A structurally thin skill used to test static validation.
---
# Keyword Stuffing
Contract output edge cases fallbacks example pattern.
"""
        )
        result = validator.validate_skill_dir(package, strict_quality=True)
        self.assertFalse(result.ok())
        self.assertEqual(3, len([error for error in result.errors if "strict quality" in error]))

    def test_empty_quality_headings_do_not_pass(self) -> None:
        package = self.write_skill(
            """---
name: empty-headings
description: A skill with headings but no substantive section content.
---
# Empty
## Contract
## Edge Cases
## Examples
"""
        )
        self.assertFalse(validator.validate_skill_dir(package, strict_quality=True).ok())

    def test_multiline_description_is_rejected(self) -> None:
        package = self.stage_fixture("bad-multiline-skill")
        result = validator.validate_skill_dir(package)
        self.assertFalse(result.ok())
        self.assertTrue(any("single-line" in error for error in result.errors))

    def test_malformed_yaml_in_allowed_frontmatter_field_is_rejected(self) -> None:
        package = self.write_skill(
            """---
name: malformed-frontmatter
description: Reject malformed YAML anywhere in the frontmatter mapping.
license: [unterminated
---
# Malformed Frontmatter
"""
        )
        result = validator.validate_skill_dir(package)
        self.assertFalse(result.ok())
        self.assertTrue(any("frontmatter contains invalid YAML" in error for error in result.errors))

    def test_frontmatter_rejects_yaml_non_string_values_for_required_strings(self) -> None:
        values = [
            "yes", "Yes", "YES", "no", "No", "NO", "on", "On", "ON", "off", "Off", "OFF",
            "true", "True", "TRUE", "false", "False", "FALSE",
            "null", "Null", "NULL", "~", "2026-10-22", "2026-10-22T12:34:56Z",
            "42", "-42", "+42", "010", "0xFF", "0b10", "1_000", "1.5", "1:20",
            ".NaN", ".INF", "-.Inf", "+.inf", "[]", "[one, two]", "{}", "{key: value}",
            "!!int '42'", "!!bool 'yes'",
        ]
        for field in ("name", "description"):
            for index, value in enumerate(values):
                with self.subTest(field=field, value=value):
                    name = value if field == "name" else "typed-skill"
                    description = value if field == "description" else "A valid description."
                    package = self.write_skill(
                        f"---\nname: {name}\ndescription: {description}\n---\n# Skill\n",
                        f"{field}-{index}",
                    )
                    result = validator.validate_skill_dir(package)
                    self.assertIn(f"{field} must be a string.", result.errors)

    def test_quoted_yaml_non_string_tokens_remain_strings(self) -> None:
        values = [
            "yes", "Yes", "YES", "no", "No", "NO", "on", "On", "ON", "off", "Off", "OFF",
            "true", "false", "null", "~", "2026-10-22", "2026-10-22T12:34:56Z",
            "42", "010", "0xFF", "1.5", ".NaN", "[]", "[one, two]", "{}", "{key: value}",
        ]
        for index, value in enumerate(values):
            for quote in ("'", '"'):
                with self.subTest(value=value, quote=quote):
                    package = self.write_skill(
                        f"---\nname: quoted-skill\ndescription: {quote}{value}{quote}\n---\n# Skill\n",
                        f"quoted-{index}-{ord(quote)}",
                    )
                    result = validator.validate_skill_dir(package)
                    self.assertTrue(result.ok(), result.errors)
                    data, _ = validator.load_frontmatter(package / "SKILL.md", result)
                    self.assertEqual(value, data["description"])
        for name in ("yes", "no", "on", "off"):
            package = self.write_skill(
                f"---\nname: '{name}'\ndescription: A valid description.\n---\n# Skill\n",
                f"quoted-name-{name}",
            )
            self.assertTrue(validator.validate_skill_dir(package).ok())

    def test_yaml_string_decoding_preserves_valid_syntax(self) -> None:
        cases = {
            "'Owner''s # title' # comment": "Owner's # title",
            r'"Use\x20this\u0020skill" # comment': "Use this skill",
            r'"A\_nonbreaking space"': "A\N{NO-BREAK SPACE}nonbreaking space",
            "!!str yes": "yes",
            "Describe the quoted \"file\"": 'Describe the quoted "file"',
            "*summary": "A shared description.",
        }
        for index, (scalar, expected) in enumerate(cases.items()):
            with self.subTest(scalar=scalar):
                package = self.write_skill(
                    "---\nname: yaml-string\nlicense: &summary A shared description.\n"
                    f"description: {scalar}\n---\n# Skill\n",
                    f"string-{index}",
                )
                result = validator.validate_skill_dir(package)
                self.assertTrue(result.ok(), result.errors)
                data, _ = validator.load_frontmatter(package / "SKILL.md", result)
                self.assertEqual(expected, data["description"])

    def test_empty_and_multiline_yaml_strings_remain_rejected(self) -> None:
        values = [
            "''", '\"\"', "'   '", r'"Line\nnext"', r'"Line\rnext"',
            r'"Line\Nnext"', r'"Line\Lnext"', "|2-\n  A block description.",
            '\"A physically\n  wrapped description.\"',
        ]
        for index, value in enumerate(values):
            with self.subTest(value=value):
                package = self.write_skill(
                    f"---\nname: multiline-string\ndescription: {value}\n---\n# Skill\n",
                    f"multiline-{index}",
                )
                self.assertFalse(validator.validate_skill_dir(package).ok())

    def test_missing_yaml_dependency_fails_closed(self) -> None:
        package = self.stage_fixture("valid-skill")
        with (
            mock.patch.object(validator, "yaml", None),
            mock.patch.object(validator, "_UniqueKeyLoader", None),
        ):
            result = validator.validate_skill_dir(package)
        self.assertFalse(result.ok())
        self.assertTrue(any("PyYAML>=6.0,<7 is required" in error for error in result.errors))

    def test_malformed_yaml_outside_openai_interface_is_rejected(self) -> None:
        package = self.stage_fixture("valid-skill")
        self.write_codex_metadata(
            package,
            """interface:
  display_name: "Market Scan"
  short_description: "Create a decision-ready market scan"
  default_prompt: "Use $market-scan to compare this market."
dependencies:
  tools:
    - type: "mcp"
      value: [unterminated
""",
        )
        result = validator.validate_skill_dir(package, expect_codex=True)
        self.assertFalse(result.ok())
        self.assertTrue(any("openai.yaml contains invalid YAML" in error for error in result.errors))

    def test_duplicate_nested_yaml_key_is_rejected(self) -> None:
        package = self.stage_fixture("valid-skill")
        self.write_codex_metadata(
            package,
            """interface:
  display_name: "Market Scan"
  short_description: "Create a decision-ready market scan"
  default_prompt: "Use $market-scan to compare this market."
dependencies:
  tools:
    - type: "mcp"
      value: "github"
      value: "duplicate"
""",
        )
        result = validator.validate_skill_dir(package, expect_codex=True)
        self.assertFalse(result.ok())
        self.assertTrue(any("duplicate key" in error for error in result.errors))

    def test_supported_openai_dependencies_and_policy_yaml_passes(self) -> None:
        package = self.stage_fixture("valid-skill")
        self.write_codex_metadata(
            package,
            """interface:
  display_name: "Market Scan"
  short_description: "Create a decision-ready market scan"
  default_prompt: "Use $market-scan to compare this market."
dependencies:
  tools:
    - type: "mcp"
      value: "github"
      description: "GitHub MCP server"
      transport: "streamable_http"
      url: "https://api.githubcopilot.com/mcp/"
policy:
  allow_implicit_invocation: true
""",
        )
        self.assertTrue(validator.validate_skill_dir(package, expect_codex=True).ok())

    def test_name_and_description_constraints(self) -> None:
        cases = {
            "Bad_Name": "hyphen-case",
            "-bad-name": "hyphen-case",
            "bad--name": "hyphen-case",
            "a" * 65: "64 characters",
        }
        for name, message in cases.items():
            with self.subTest(name=name):
                package = self.write_skill(
                    f"---\nname: {name}\ndescription: A valid description.\n---\n# Skill\n",
                    package_name=name.replace("/", "_")[:40],
                )
                result = validator.validate_skill_dir(package)
                self.assertTrue(any(message in error for error in result.errors), result.errors)

        package = self.write_skill(
            "---\nname: angle-skill\ndescription: Use <input> to make output.\n---\n# Skill\n",
            "angle",
        )
        self.assertTrue(
            any("angle brackets" in error for error in validator.validate_skill_dir(package).errors)
        )

    def test_codex_rejects_unexpected_frontmatter_but_generic_mode_allows_it(self) -> None:
        package = self.write_skill(
            """---
name: extra-key
description: A valid description for a generic skill package.
argument-hint: "[topic]"
---
# Extra Key
"""
        )
        self.assertTrue(validator.validate_skill_dir(package).ok())
        self.write_codex_metadata(
            package,
            """interface:
  display_name: "Extra Key"
  short_description: "Validate a package with metadata"
  default_prompt: "Use $extra-key to validate this package."
""",
        )
        result = validator.validate_skill_dir(package, expect_codex=True)
        self.assertTrue(any("unexpected Codex" in error for error in result.errors))

    def test_codex_skill_can_contain_only_skill_md(self) -> None:
        package = self.stage_fixture("valid-skill")
        self.assertEqual(["SKILL.md"], [path.name for path in package.iterdir()])
        result = validator.validate_skill_dir(package, expect_codex=True, strict_quality=True)
        self.assertTrue(result.ok(), result.errors)

    def test_codex_metadata_and_interface_fields_are_optional(self) -> None:
        package = self.stage_fixture("valid-skill")
        assets = package / "assets"
        assets.mkdir()
        (assets / "icon.svg").write_text("<svg/>", encoding="utf-8")
        metadata_cases = [
            "{}\n",
            "interface: {}\n",
            "policy:\n  allow_implicit_invocation: false\n",
            'dependencies:\n  tools:\n    - type: "mcp"\n      value: "github"\n',
        ]
        optional_fields = {
            "display_name": "Market Scan",
            "short_description": "Create a decision-ready market scan",
            "default_prompt": "Use $market-scan to compare this market.",
            "icon_small": "./assets/icon.svg",
            "icon_large": "./assets/icon.svg",
            "brand_color": "#3B82F6",
        }
        metadata_cases.extend(
            f'interface:\n  {key}: "{value}"\n' for key, value in optional_fields.items()
        )
        for metadata in metadata_cases:
            with self.subTest(metadata=metadata):
                self.write_codex_metadata(package, metadata)
                result = validator.validate_skill_dir(package, expect_codex=True)
                self.assertTrue(result.ok(), result.errors)

    def test_native_generated_ui_metadata_passes_without_default_prompt(self) -> None:
        # Frozen default UI metadata from Codex skill-creator's init_skill.py and
        # generate_openai_yaml.py, paired with completed skill instructions.
        # Neither script supplies an unrequested prompt.
        outputs = [
            (
                "native-initializer",
                '---\nname: native-initializer\n'
                'description: "Review initialized skill packages for task-specific guidance."\n'
                '---\n\n# Native Initializer\n\n'
                'Review the supplied skill package and identify guidance the task requires.\n',
                'interface:\n  display_name: "Native Initializer"\n'
                '  short_description: "Help with Native Initializer tasks"\n',
            ),
            (
                "market-scan",
                (FIXTURES / "valid-skill" / "SKILL.fixture.md").read_text(encoding="utf-8"),
                'interface:\n  display_name: "Market Scan"\n'
                '  short_description: "Help with Market Scan tasks"\n',
            ),
        ]
        for name, skill_md, metadata in outputs:
            with self.subTest(output=name):
                package = self.write_skill(skill_md, name)
                self.write_codex_metadata(package, metadata)
                self.assertNotIn("default_prompt", metadata)
                result = validator.validate_skill_dir(package, expect_codex=True)
                self.assertTrue(result.ok(), result.errors)

    def test_supplied_interface_must_be_a_mapping(self) -> None:
        package = self.stage_fixture("valid-skill")
        for value in ("", "null", '""', '"Market Scan"', "[]", "true", "42"):
            with self.subTest(value=value):
                self.write_codex_metadata(package, f"interface: {value}\n")
                result = validator.validate_skill_dir(package, expect_codex=True)
                self.assertIn("agents/openai.yaml interface must contain a YAML mapping.", result.errors)

    def test_present_codex_metadata_path_must_be_a_file(self) -> None:
        for kind in ("directory", "dangling-symlink"):
            with self.subTest(kind=kind):
                package = self.stage_fixture("valid-skill", kind)
                metadata = package / "agents" / "openai.yaml"
                metadata.parent.mkdir()
                if kind == "directory":
                    metadata.mkdir()
                else:
                    metadata.symlink_to("missing.yaml")
                result = validator.validate_skill_dir(package, expect_codex=True)
                self.assertIn("Codex metadata path must be a file: agents/openai.yaml", result.errors)

    def test_unreadable_codex_metadata_fails_closed(self) -> None:
        package = self.stage_fixture("valid-skill")
        self.write_codex_metadata(package, "{}\n")
        (package / "agents" / "openai.yaml").write_bytes(b"\xff\xfe")
        result = validator.validate_skill_dir(package, expect_codex=True)
        self.assertTrue(any("could not read agents/openai.yaml" in error for error in result.errors))

    def test_every_supplied_ui_field_still_checks_its_value(self) -> None:
        package = self.stage_fixture("valid-skill")
        invalid_values = (
            "''", "'   '", "null", "true", "42", "[]", "{}", "[one, two]",
            '!!int "42"', "Unquoted text", r'"Line\nnext"',
            '|-\n    A block value', '&value |-\n    A block value',
        )
        for field in (
            "display_name", "short_description", "default_prompt", "icon_small", "icon_large", "brand_color"
        ):
            for value in invalid_values:
                with self.subTest(field=field, value=value):
                    self.write_codex_metadata(package, f"interface:\n  {field}: {value}\n")
                    result = validator.validate_skill_dir(package, expect_codex=True)
                    self.assertFalse(result.ok(), result.errors)
                    self.assertTrue(any(f"interface.{field}" in error for error in result.errors))

    def test_short_description_keeps_native_length_bounds_when_supplied(self) -> None:
        package = self.stage_fixture("valid-skill")
        for length in (24, 25, 64, 65):
            with self.subTest(length=length):
                self.write_codex_metadata(
                    package, f'interface: {{short_description: "{"a" * length}"}}\n'
                )
                result = validator.validate_skill_dir(package, expect_codex=True)
                self.assertEqual(25 <= length <= 64, result.ok(), result.errors)

    def test_optional_prompt_and_icon_values_keep_semantic_checks(self) -> None:
        package = self.stage_fixture("valid-skill")
        cases = {
            "default_prompt": "Use /market-scan to compare this market.",
            "icon_small": "https://example.com/icon.svg",
            "icon_large": "/assets/icon.svg",
        }
        for field, value in cases.items():
            with self.subTest(field=field):
                self.write_codex_metadata(package, f'interface:\n  {field}: "{value}"\n')
                result = validator.validate_skill_dir(package, expect_codex=True)
                self.assertFalse(result.ok(), result.errors)
                self.assertTrue(any(f"interface.{field}" in error for error in result.errors))

    def test_native_valid_metadata_yaml_layouts_and_quoted_scalar_styles_pass(self) -> None:
        package = self.stage_fixture("valid-skill")
        metadata_cases = [
            'interface: # UI fields\n  display_name: "Market Scan"\n',
            'interface:   \n  display_name: "Market Scan"\n',
            'interface: {display_name: "Market Scan"}\n',
            '{interface: {display_name: "Market Scan"}}\n',
            'interface:\n  display_name:\n    "Market Scan"\n',
            'interface:\n  display_name: "Market\n    Scan"\n',
            'interface:\n  display_name: !!str "Market Scan"\n',
            'interface:\n  display_name: &title "Market Scan"\n',
            'title: &title "Market Scan"\ninterface:\n  display_name: *title\n',
            'ui: &ui\n  display_name: "Market Scan"\ninterface: *ui\n',
            'ui: &ui\n  display_name: "Market Scan"\ninterface:\n  <<: *ui\n',
        ]
        for metadata in metadata_cases:
            with self.subTest(metadata=metadata):
                self.write_codex_metadata(package, metadata)
                result = validator.validate_skill_dir(package, expect_codex=True)
                self.assertTrue(result.ok(), result.errors)

    def test_inherited_interface_values_cannot_escape_validation(self) -> None:
        package = self.stage_fixture("valid-skill")
        for value in ('"Too short"', "true", '""'):
            with self.subTest(value=value):
                self.write_codex_metadata(
                    package,
                    f"ui: &ui\n  short_description: {value}\ninterface:\n  <<: *ui\n",
                )
                result = validator.validate_skill_dir(package, expect_codex=True)
                self.assertFalse(result.ok(), result.errors)
                self.assertTrue(any("interface.short_description" in error for error in result.errors))

    def test_present_metadata_must_contain_a_yaml_mapping(self) -> None:
        package = self.stage_fixture("valid-skill")
        for metadata in ("", "null\n", "[]\n", '"metadata"\n'):
            with self.subTest(metadata=metadata):
                self.write_codex_metadata(package, metadata)
                result = validator.validate_skill_dir(package, expect_codex=True)
                self.assertIn("agents/openai.yaml must contain a YAML mapping.", result.errors)

    def test_metadata_without_interface_still_rejects_invalid_yaml_and_duplicates(self) -> None:
        package = self.stage_fixture("valid-skill")
        metadata_cases = [
            "policy: [unterminated\n",
            "policy:\n  allow_implicit_invocation: true\n  allow_implicit_invocation: false\n",
            "interface: {}\ninterface: {}\n",
            'interface: {display_name: "First", display_name: "Second"}\n',
        ]
        for metadata in metadata_cases:
            with self.subTest(metadata=metadata):
                self.write_codex_metadata(package, metadata)
                result = validator.validate_skill_dir(package, expect_codex=True)
                self.assertTrue(any("contains invalid YAML" in error for error in result.errors))

    def test_codex_metadata_contract_and_icon_paths(self) -> None:
        package = self.stage_fixture("valid-skill")
        assets = package / "assets"
        assets.mkdir()
        (assets / "icon.svg").write_text("<svg/>", encoding="utf-8")
        valid = """interface:
  display_name: "Market Scan"
  short_description: "Create a decision-ready market scan"
  icon_small: "./assets/icon.svg"
  default_prompt: "Use $market-scan to compare this market."
"""
        self.write_codex_metadata(package, valid)
        self.assertTrue(validator.validate_skill_dir(package, expect_codex=True).ok())

        invalid_values = {
            "unquoted display": valid.replace(
                'display_name: "Market Scan"', "display_name: Market Scan"
            ),
            "short description": valid.replace(
                '"Create a decision-ready market scan"', '"Too short"'
            ),
            "prompt invocation": valid.replace("$market-scan", "/market-scan"),
            "missing icon": valid.replace("./assets/icon.svg", "./assets/missing.svg"),
        }
        for label, metadata in invalid_values.items():
            with self.subTest(label=label):
                self.write_codex_metadata(package, metadata)
                self.assertFalse(validator.validate_skill_dir(package, expect_codex=True).ok())

    def test_codex_metadata_uses_yaml_strings_and_preserves_quoted_policy(self) -> None:
        package = self.stage_fixture("valid-skill")
        metadata = """interface:
  display_name: 'Owner''s Market Scan' # comment
  short_description: "Create a decision-ready market scan" # comment
  default_prompt: "Use $market-scan to compare this market."
"""
        self.write_codex_metadata(package, metadata)
        result = validator.validate_skill_dir(package, expect_codex=True)
        self.assertTrue(result.ok(), result.errors)
        for value in ("yes", "[]", r'"Market\nScan"'):
            with self.subTest(value=value):
                self.write_codex_metadata(
                    package, metadata.replace("'Owner''s Market Scan' # comment", value)
                )
                self.assertFalse(validator.validate_skill_dir(package, expect_codex=True).ok())

    def test_local_markdown_links_are_checked_and_external_links_are_ignored(self) -> None:
        package = self.write_skill(
            """---
name: linked-skill
description: A skill that links to a local reference and an external source.
---
# Linked
See [local](references/guide.md), [anchor](#linked), and [web](https://example.com).
"""
        )
        reference = package / "references" / "guide.md"
        reference.parent.mkdir()
        reference.write_text("# Guide\n", encoding="utf-8")
        self.assertTrue(validator.validate_skill_dir(package).ok())
        reference.unlink()
        result = validator.validate_skill_dir(package)
        self.assertTrue(any("broken local Markdown link" in error for error in result.errors))

    def test_reachable_markdown_links_are_checked_relative_to_each_reference(self) -> None:
        package = self.stage_fixture("valid-skill")
        skill_md = package / "SKILL.md"
        skill_md.write_text(
            skill_md.read_text(encoding="utf-8") + "\n[Guide](references/guide.md)\n",
            encoding="utf-8",
        )
        references = package / "references"
        references.mkdir()
        (references / "guide.md").write_text(
            "[Nested][nested]\n[nested]: nested/details.markdown#details\n",
            encoding="utf-8",
        )
        nested = references / "nested"
        nested.mkdir()
        (nested / "details.markdown").write_text(
            "[Back](../guide.md)\n[Missing](missing.md)\n", encoding="utf-8"
        )
        result = validator.validate_skill_dir(package)
        self.assertEqual(
            ["broken local Markdown link in references/nested/details.markdown: missing.md"],
            result.errors,
        )
        (nested / "missing.md").write_text("# Present\n", encoding="utf-8")
        self.assertTrue(validator.validate_skill_dir(package).ok())

    def test_recursive_link_checks_ignore_code_and_unreachable_markdown(self) -> None:
        package = self.stage_fixture("valid-skill")
        references = package / "references"
        references.mkdir()
        (references / "orphan.md").write_text("[Missing](missing.md)\n", encoding="utf-8")
        skill_md = package / "SKILL.md"
        skill_md.write_text(
            skill_md.read_text(encoding="utf-8")
            + "\n`[inline](missing.md)`\n```md\n[fenced](references/orphan.md)\n```\n",
            encoding="utf-8",
        )
        self.assertTrue(validator.validate_skill_dir(package).ok())

    def test_symlinked_references_keep_each_alias_relative_link_context(self) -> None:
        package = self.stage_fixture("valid-skill")
        skill_md = package / "SKILL.md"
        for directory in ("first", "second"):
            references = package / directory
            references.mkdir()
            (references / "guide.md").symlink_to("../shared.md")
        (package / "shared.md").write_text("[Child](child.md)\n", encoding="utf-8")
        (package / "first" / "child.md").write_text("# Present\n", encoding="utf-8")
        (package / "child.md").write_text("# Canonical decoy\n", encoding="utf-8")
        skill_md.write_text(
            skill_md.read_text(encoding="utf-8")
            + "\n[First](first/guide.md)\n[Second](second/guide.md)\n",
            encoding="utf-8",
        )
        result = validator.validate_skill_dir(package)
        self.assertEqual(
            ["broken local Markdown link in second/guide.md: child.md"], result.errors
        )
        (package / "second" / "child.md").write_text("# Present\n", encoding="utf-8")
        (package / "child.md").unlink()
        self.assertTrue(validator.validate_skill_dir(package).ok())

    def test_directory_symlink_and_parent_reference_cycles_terminate(self) -> None:
        package = self.stage_fixture("valid-skill")
        references = package / "references"
        references.mkdir()
        (references / "loop").symlink_to(".")
        (references / "guide.md").write_text(
            "[Directory loop](loop/guide.md)\n[Parent loop](../references/guide.md)\n"
            "[Missing](missing.md)\n",
            encoding="utf-8",
        )
        skill_md = package / "SKILL.md"
        skill_md.write_text(
            skill_md.read_text(encoding="utf-8") + "\n[Guide](references/guide.md)\n",
            encoding="utf-8",
        )
        result = validator.validate_skill_dir(package)
        self.assertEqual(
            ["broken local Markdown link in references/guide.md: missing.md"], result.errors
        )

    def test_recursive_link_checks_do_not_read_outside_the_package(self) -> None:
        package = self.stage_fixture("valid-skill")
        external = self.root / "external.md"
        external.write_text("[Missing](missing.md)\n", encoding="utf-8")
        (package / "external.md").symlink_to(external)
        skill_md = package / "SKILL.md"
        skill_md.write_text(
            skill_md.read_text(encoding="utf-8")
            + "\n[Outside](../external.md)\n[Symlink](external.md)\n",
            encoding="utf-8",
        )
        self.assertTrue(validator.validate_skill_dir(package).ok())

    def test_unreadable_reachable_markdown_fails_closed(self) -> None:
        package = self.stage_fixture("valid-skill")
        (package / "invalid.md").write_bytes(b"\xff\xfe")
        skill_md = package / "SKILL.md"
        skill_md.write_text(
            skill_md.read_text(encoding="utf-8") + "\n[Invalid](invalid.md)\n",
            encoding="utf-8",
        )
        result = validator.validate_skill_dir(package)
        self.assertTrue(any("could not read local Markdown reference invalid.md" in e for e in result.errors))

    def test_symlinked_core_uses_package_relative_link_context(self) -> None:
        package = self.stage_fixture("valid-skill")
        skill_md = package / "SKILL.md"
        external = self.root / "external.md"
        external.write_text(
            skill_md.read_text(encoding="utf-8") + "\n[Missing](missing.md)\n",
            encoding="utf-8",
        )
        skill_md.unlink()
        skill_md.symlink_to(external)
        result = validator.validate_skill_dir(package)
        self.assertEqual(
            ["broken local Markdown link in SKILL.md: missing.md"], result.errors
        )
        (package / "missing.md").write_text("# Present\n", encoding="utf-8")
        self.assertTrue(validator.validate_skill_dir(package).ok())

    def test_nested_active_skill_is_rejected_but_fixture_name_is_not(self) -> None:
        package = self.stage_fixture("valid-skill")
        nested = package / "references" / "nested"
        nested.mkdir(parents=True)
        shutil.copyfile(package / "SKILL.md", nested / "SKILL.fixture.md")
        self.assertTrue(validator.validate_skill_dir(package).ok())
        shutil.copyfile(package / "SKILL.md", nested / "SKILL.md")
        self.assertTrue(
            any("nested active skill" in error for error in validator.validate_skill_dir(package).errors)
        )

    def test_expect_claude_checks_the_target_without_requiring_a_mirror(self) -> None:
        valid = self.stage_fixture("valid-skill", "valid-claude")
        self.assertTrue(validator.validate_skill_dir(valid, expect_claude=True).ok())
        long_description = self.stage_fixture("claude-description-too-long", "long-claude")
        result = validator.validate_skill_dir(long_description, expect_claude=True)
        self.assertTrue(any("Claude description exceeds" in error for error in result.errors))

    def test_cli_labels_results_as_static(self) -> None:
        package = self.stage_fixture("valid-skill")
        completed = subprocess.run(
            [sys.executable, str(VALIDATOR_PATH), str(package)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        self.assertTrue(completed.stdout.startswith("STATIC PASS "))

    def test_canonical_codex_package_passes_strict_static_checks(self) -> None:
        package = REPO_ROOT / "packages" / "codex" / "skillskill"
        result = validator.validate_skill_dir(
            package, expect_codex=True, expect_claude=True, strict_quality=True
        )
        self.assertTrue(result.ok(), result.errors)

    def test_packaged_validator_is_byte_identical_and_both_are_executable(self) -> None:
        self.assertEqual(VALIDATOR_PATH.read_bytes(), PACKAGE_VALIDATOR_PATH.read_bytes())
        self.assertTrue(os.access(VALIDATOR_PATH, os.X_OK))
        self.assertTrue(os.access(PACKAGE_VALIDATOR_PATH, os.X_OK))

    def test_validator_requirements_are_shipped_with_the_package(self) -> None:
        root_requirements = REPO_ROOT / "requirements.txt"
        package_requirements = PACKAGE_VALIDATOR_PATH.parent / "requirements.txt"
        self.assertEqual(root_requirements.read_bytes(), package_requirements.read_bytes())


class BehavioralManifestTests(unittest.TestCase):
    def test_manifest_case_counts_ids_categories_and_gates(self) -> None:
        manifest = json.loads(EVAL_MANIFEST.read_text(encoding="utf-8"))
        routing = manifest["routing_cases"]
        execution = manifest["execution_cases"]
        self.assertEqual(24, len(routing))
        self.assertEqual(9, len(execution))
        ids = [case["id"] for case in routing + execution]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(
            {
                "direct_positive",
                "implicit_positive",
                "near_negative",
                "ambiguous_boundary",
                "collision",
            },
            {case["category"] for case in routing},
        )
        expected_execution_categories = set(manifest["required_execution_gates"])
        self.assertEqual(expected_execution_categories, {case["category"] for case in execution})
        for case in routing:
            self.assertIn(case["expected"], {"trigger", "do_not_trigger", "conditional"})
            self.assertTrue(case["required_gates"])
        for case in execution:
            required = set(manifest["required_execution_gates"][case["category"]])
            self.assertTrue(required)
            self.assertTrue(required.issubset(case["required_gates"]))


class RepositoryPackagingTests(unittest.TestCase):
    def test_project_adapters_are_relative_symlinks_to_the_canonical_package(self) -> None:
        canonical = (REPO_ROOT / "packages" / "codex" / "skillskill").resolve()
        for relative_path in (
            ".agents/skills/skillskill",
            ".claude/skills/skillskill",
        ):
            with self.subTest(adapter=relative_path):
                adapter = REPO_ROOT / relative_path
                self.assertTrue(adapter.is_symlink())
                target = Path(os.readlink(adapter))
                self.assertFalse(target.is_absolute())
                self.assertEqual(canonical, (adapter.parent / target).resolve())

    def test_runtime_images_live_under_assets_and_are_referenced(self) -> None:
        package = REPO_ROOT / "packages" / "codex" / "skillskill"
        image_suffixes = {".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"}
        images = {
            path.relative_to(package).as_posix()
            for path in package.rglob("*")
            if path.is_file() and path.suffix.lower() in image_suffixes
        }
        self.assertTrue(images)
        self.assertTrue(all(path.startswith("assets/") for path in images))
        metadata = (package / "agents" / "openai.yaml").read_text(encoding="utf-8")
        referenced = {
            match.group(1).removeprefix("./")
            for match in re.finditer(
                r'^\s+icon_(?:small|large):\s*["\']([^"\']+)["\']\s*$',
                metadata,
                re.MULTILINE,
            )
        }
        self.assertEqual(images, referenced)

    def test_installer_creates_stable_validated_copies_and_requires_force(self) -> None:
        installer = REPO_ROOT / "scripts" / "install.sh"
        canonical = REPO_ROOT / "packages" / "codex" / "skillskill"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            env = os.environ.copy()
            env["CODEX_HOME"] = str(temp_root / "codex-home")
            env["CLAUDE_HOME"] = str(temp_root / "claude-home")
            command = ["bash", str(installer), "--all"]

            first = subprocess.run(
                command, cwd=REPO_ROOT, env=env, check=False, capture_output=True, text=True
            )
            self.assertEqual(0, first.returncode, first.stdout + first.stderr)

            canonical_files = {
                path.relative_to(canonical)
                for path in canonical.rglob("*")
                if path.is_file()
            }
            for home_name in ("codex-home", "claude-home"):
                target = temp_root / home_name / "skills" / "skillskill"
                self.assertTrue(target.is_dir())
                self.assertFalse(target.is_symlink())
                target_files = {
                    path.relative_to(target) for path in target.rglob("*") if path.is_file()
                }
                self.assertEqual(canonical_files, target_files)
                for relative_path in canonical_files:
                    self.assertEqual(
                        (canonical / relative_path).read_bytes(),
                        (target / relative_path).read_bytes(),
                    )

            second = subprocess.run(
                command, cwd=REPO_ROOT, env=env, check=False, capture_output=True, text=True
            )
            self.assertNotEqual(0, second.returncode)

            forced = subprocess.run(
                command + ["--force"],
                cwd=REPO_ROOT,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, forced.returncode, forced.stdout + forced.stderr)
            leftovers = [
                path
                for path in temp_root.rglob(".*")
                if ".stage." in path.name or ".backup." in path.name
            ]
            self.assertEqual([], leftovers)


if __name__ == "__main__":
    unittest.main()
