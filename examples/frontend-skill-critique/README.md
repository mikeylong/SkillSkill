# Frontend Skill Critique Example

This example captures a real `skillskill` workflow: critique an existing `frontend-skill`, rewrite the weak parts, and then do a second pass to keep the rewritten skill lean enough to stay callable.

This bundle is documentation only. It is not the canonical source of truth for the live `frontend-skill` under `~/.codex/skills/frontend-skill/`.

## What This Example Contains

- `prompt.md`: the cleaned-up request sequence
- `before/SKILL.example.md`: the original skill snapshot that was critiqued
- `assessment.md`: the critique in SkillSkill terms
- `after/SKILL.example.md`: the rewritten core skill snapshot
- `after/references/visual-playbook.md`: the extracted reference playbook that keeps the rewritten example self-contained

## What Changed

- The rewrite tightened routing and clarified when the skill should and should not be used.
- It added an explicit contract, mode selection, edge cases, output shape, and example requests.
- A follow-up pass moved long-form visual heuristics into a reference file so the core skill stayed lean.

## Why The Example Is Frozen

The `before/` and `after/` files are example snapshots. They may diverge from future changes to the real external `frontend-skill`, which is expected. The goal here is to preserve a worked example of the critique-and-rewrite workflow, not to mirror a live package.
