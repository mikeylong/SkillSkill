# Review Checklist

Use this checklist when critiquing or revising a skill.

## Core Questions

- Is the description specific enough to route correctly?
- Does the description name the output, artifact, or task result?
- Is the description a single line?
- Does the body explain reasoning, not just steps?
- Is there an explicit contract for what the skill returns?
- Is the output format or section structure clear?
- Are important edge cases written down?
- Is there at least one compact example or example pointer?
- Should any brittle behavior be moved into a script?
- Should any bulky detail be moved into `references/`?

## Rewrite Priorities

Fix these first:

1. vague description
2. missing contract
3. missing output shape
4. missing edge cases
5. no example anchor
6. bloated core file

## Output Shape For Critique Mode

When reviewing a skill, prefer returning:

1. `Assessment`: 2-5 bullets on the largest issues
2. `Rewritten Skill`: the improved `SKILL.md` or the changed sections
3. `Packaging Notes`: only if the skill needs references, scripts, or platform-specific metadata
