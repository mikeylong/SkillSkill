---
name: "skillskill"
description: "Create, revise, or critique agent-readable skill files from workflows, prompts, transcripts, or existing skills. Produces stronger SKILL.md packages with precise descriptions, explicit contracts, edge cases, examples, and platform-specific packaging when requested."
---

# SkillSkill

Use this skill to turn workflow knowledge into a durable, high-quality skill package, or to repair a weak skill so it routes and performs better for agents.

Default posture: write a cross-tool skill first, then adapt packaging details only when the caller explicitly names a platform such as Codex or Claude Code.

## Trigger Cases

Use this skill when the user asks to:

- create a skill
- rewrite or refactor a skill
- review a skill for agent readability
- turn a workflow, prompt, notes set, or transcript into a skill
- diagnose why a skill under-triggers, over-triggers, or produces weak outputs

## Contract

Return concrete rewritten artifacts, not only advice.

- `Create`: return a complete new skill draft, any supporting-file recommendations, and a short quality review against the rubric.
- `Revise`: return a rewritten skill file or rewritten sections, a short note on what changed, and any packaging updates required.
- `Critique`: return `Assessment`, `Rewritten Skill`, and `Packaging Notes` when packaging changes are needed.

If the caller asked for file edits, update the files directly instead of only describing changes.

## Workflow

1. Classify the skill.
Determine whether it is a standard skill, a methodology skill, or a personal workflow skill. Identify the likely caller, audience, and where the skill should live.

2. Extract the operating intent.
Pull out the repeated workflow, the target outcome, the artifacts produced, and the trigger phrases an agent is likely to see in real requests.

3. Write the description first.
Treat the description as a routing signal, not a label. Keep it on one line. Name the output or artifact, include trigger-style language, and make the use case concrete enough that the agent can confidently choose it.

4. Draft the body around reasoning.
Do not write only a brittle checklist. Include the principles, quality bar, and decision logic that let the model generalize when inputs vary.

5. Define the output contract.
State what the skill produces, what shape the output should take, what it is allowed to assume, and what it does not promise. Skills should feel closer to an API contract than a motivational prompt.

6. Add output guidance, edge cases, and an example.
Specify the expected output format or sections. Write down the edge cases a human would otherwise silently handle. Include one compact example or point to a reference file with good examples.

7. Split deterministic work out of prose when needed.
If correctness depends on a precise transform, parsing rule, or fragile sequence, recommend or create a script rather than pretending prose will reliably hardwire the behavior.

8. Run a critique pass before finalizing.
Check the draft against the rubric in [references/rubric.md](references/rubric.md) and the review prompts in [references/review-checklist.md](references/review-checklist.md). Rewrite weak descriptions, vague contracts, missing edge cases, and bloated sections before returning the result.

## Authoring Rules

- Keep the core skill lean. Prefer a tight core file with references over a long monolith with competing instructions.
- Prefer behavior-level guidance over excessive exposition. The model already knows basic writing mechanics.
- Make outputs handoff-ready. A downstream agent or human should be able to use the result without reinterpreting the skill's intent.
- Preserve existing conventions when revising an established skill unless the caller asks for a rework.
- If the request is platform-specific, add only the packaging details that platform actually needs.
- If the skill will be reused heavily by agents, recommend a validator path or a small basket of representative prompts so revisions can be compared over time.

## Edge Cases

- If the source material is incomplete, state the assumptions you are making before drafting the skill.
- If the workflow is too broad, narrow it to one repeatable job instead of writing a vague catch-all skill.
- If the platform is unspecified, avoid inventing tool-specific frontmatter rules or metadata fields.
- If the package already exists, preserve naming and structural conventions unless they block routing clarity or output quality.
- If the desired behavior is fundamentally deterministic, recommend a script or supporting tool instead of overpromising with prose.

## Example Requests

- `Turn this meeting-synthesis workflow into a reusable skill.`
- `Critique this SKILL.md and rewrite weak parts.`
- `Use this transcript to draft a skill, then package it for Codex.`

## Review Mode

When the input already contains a skill, do not stop at abstract critique. Rewrite the weak parts and return:

1. `Assessment`: 2-5 bullets on the highest-impact issues.
2. `Rewritten Skill`: the improved `SKILL.md` or the changed sections.
3. `Packaging Notes`: only when the skill needs references, scripts, or platform-specific metadata.

Prioritize:

- vague or broad descriptions
- missing contract or output shape
- absent edge cases
- no example or pattern anchor
- instructions that should be moved into a script or reference
- bloated core files that should be shortened

## Codex Packaging

When the caller wants a Codex skill package, produce:

- `SKILL.md`
- `agents/openai.yaml` with concise UI metadata
- `references/` only when extra detail materially improves the skill
- `scripts/` only for deterministic behavior or validation

If the caller also wants Claude Code packaging, preserve the same core methodology and only adapt the project-skill path, frontmatter, and description length constraints required by Claude.

If local files are available, validate Codex-oriented packages with `python3 scripts/validate_skill.py <skill-dir>` before finishing.
