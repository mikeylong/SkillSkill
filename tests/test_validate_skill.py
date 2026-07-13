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
            "missing display": valid.replace('  display_name: "Market Scan"\n', ""),
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


class BehavioralManifestTests(unittest.TestCase):
    def test_manifest_case_counts_ids_categories_and_gates(self) -> None:
        manifest = json.loads(EVAL_MANIFEST.read_text(encoding="utf-8"))
        routing = manifest["routing_cases"]
        execution = manifest["execution_cases"]
        self.assertEqual(24, len(routing))
        self.assertEqual(8, len(execution))
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
