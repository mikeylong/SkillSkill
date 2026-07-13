---
name: skillskill
description: Audit, benchmark, validate, port, and diagnose routing or regressions in existing agent skill packages. Use for skill evaluations, capability-fit reviews, metadata tests, behavioral comparisons, targeted repairs, and release readiness.
---

# SkillSkill

Audit existing skill packages and improve them only when authorized. Defer ordinary new-skill scaffolding to the platform-native creator.

## Modes And Authority

- **Audit:** Stay read-only. Inspect the package and return evidence-backed findings without rewriting files.
- **Evaluate:** Stay read-only except for explicitly authorized, isolated fixtures. Benchmark routing and execution without changing the source package.
- **Revise or implement:** Edit only the package and findings placed in scope. Preserve unrelated files, conventions, and user changes.
- **Port:** Change only the requested target package or adapter. Preserve the canonical behavioral contract unless the user requests a redesign.
- Never infer write authority from requests to audit, review, diagnose, benchmark, or validate.

When the user explicitly invokes `$skillskill` to create a new skill, compose with the platform-native skill creator. Let the native creator own scaffolding and current packaging; use SkillSkill to sharpen boundaries, audit the result, and design evaluation. If no native creator is available, state the fallback before proceeding.

## Workflow

### 1. Establish The Execution Surface

- Identify the skill package actually discovered at runtime before judging a repository copy.
- Resolve the canonical source, installed copy, generated mirrors, adapters, and copy-versus-symlink relationship. Record paths, versions or hashes, and drift when available.
- Read each target `SKILL.md` completely. Read every directly required reference completely; for conditional references, read all files governing the paths under test and record any skipped material.
- Inspect repository and installed-package state separately. Do not assume the edited source is the active runtime.

### 2. Inventory And Compose Capabilities

- Inventory available skills, tools, scripts, apps, connectors, MCP servers or resources, assets, and runtime dependencies.
- Distinguish discoverable capabilities from merely documented or installed ones.
- Find platform-native or specialist capabilities that overlap the package. Compose with them instead of duplicating their generic behavior.
- Verify fallback behavior when a required capability is absent, unavailable, or unauthorized.

### 3. Audit Behavior And Boundaries

- Treat frontmatter descriptions and registry metadata as the routing surface; do not rely on body-only trigger guidance.
- Check positive triggers, must-not-trigger cases, nearest competing skills, explicit invocation, under-triggering, and over-triggering.
- Check the contract, output shape, authority boundaries, reasoning guidance, edge cases, fallback behavior, examples, and handoff quality.
- Separate deterministic behavior that belongs in scripts from judgment that belongs in prose.

### 4. Inspect Disclosure And Packaging

- Keep the core file lean. Link references directly and load detail only for the applicable path.
- Verify that scripts are deterministic and tested, references are instruction-bearing and reachable, and assets are output resources rather than hidden instructions.
- Flag broken links, orphaned resources, duplicated guidance, oversized or unreferenced assets, and competing sources of truth.
- Follow the target platform's native naming, frontmatter, metadata, folder, and validation rules. Regenerate platform adapters from the canonical contract when practical.

### 5. Validate At Two Levels

- Run authoritative platform validators and every documented command against the actual callable variant.
- Label schema, link, command, and package checks as **static validation**. Never present a keyword scan or custom linter as proof of behavioral quality.
- Run metadata-only routing tests and fresh-agent execution comparisons for consequential revisions. Compare no-skill or incumbent behavior with the candidate when practical.
- Give forward-test agents raw user tasks and clean fixtures. Do not leak the suspected defect, intended fix, expected answer, prior output, or scoring conclusion.
- Use isolated workspaces for tests that write files. Do not exercise live production systems without explicit authority.
- Follow [references/evaluation.md](references/evaluation.md) for prompt baskets, provenance, gates, and A/B procedure.

### 6. Score And Report

- Read [references/rubric.md](references/rubric.md) completely and score only supported evidence.
- Lead with a verdict. Report findings under `High`, `Medium`, and `Low`; do not use P-number labels.
- Cite concrete paths, metadata, commands, outputs, or trial artifacts for each material finding.
- Separate runtime drift, static results, behavioral results, implemented changes, and limitations.
- Do not force a rewrite in Audit or Evaluate mode. Offer targeted replacement text only when it clarifies a finding; edit files only in an authorized write mode.

## Edge Cases

- When multiple active copies disagree, identify the discovered runtime, map the drift, and avoid overwriting either copy until the source of truth is established.
- When the platform is unspecified, audit the platform-neutral contract and observed runtime; do not invent packaging rules.
- When clean-agent evaluation is unavailable, preserve a runnable prompt basket and mark behavioral checks `Not tested`.
- When static checks pass but behavior remains untested, report `Static: Pass` and `Behavioral: Not tested`; do not claim release readiness.

## Example Requests

- `Use $skillskill to audit this installed skill against its repository source and diagnose routing drift.`
- `Use $skillskill to evaluate this revision with metadata-only routing tests and fresh-agent A/B tasks.`
- `Use $skillskill to port this skill to Codex while preserving its behavioral contract and validating the adapter.`

## Output Contract

Return the smallest handoff-ready report that covers:

1. `Verdict` and scored readiness
2. `Runtime And Source Map`
3. `High`, `Medium`, and `Low` findings with evidence
4. `Static Validation` and `Behavioral Evaluation` as separate sections
5. `Changes` only when authorized
6. `Limitations` and the next release gate

Mark unrun checks as `Not tested`. Never infer a pass from missing evidence.
