# Agent Readability Rubric

Use this rubric to draft or critique skills. The goal is not to make the longest skill. The goal is to make the most callable and dependable one.

## 1. Description Quality

A strong description:

- stays on a single line
- acts as a routing signal, not a label
- names the artifact, document, or output produced
- includes realistic trigger language from user requests
- makes the use case specific enough to call confidently

A weak description:

- is vague, generic, or aspirational
- says it "helps with" a broad domain
- omits the output shape
- can match unrelated requests

## 2. Reasoning Over Rote Steps

The body should teach the model how to think in the workflow, not just what order to click things in.

Include:

- decision principles
- quality criteria
- how to resolve common ambiguity
- when to stay flexible versus when to be strict

Avoid pure linear procedure unless the task is fragile enough that it should become a script.

## 3. Contract Clarity

Every strong skill defines a contract:

- what the skill returns
- what structure or sections the output should have
- what assumptions are allowed
- what the skill does not guarantee

If the contract is fuzzy, agents will call the skill with weak expectations and produce weak handoffs.

## 4. Edge Cases And Examples

Write down the cases a skilled human would otherwise handle implicitly.

Include:

- missing inputs
- ambiguous requests
- competing interpretations
- failure or fallback behavior

Also include one compact example or a pointer to a reference file with a good example. A short example is usually enough to anchor style and structure.

## 5. Lean Core File

Keep the core skill file lean enough to stay legible and callable.

- Prefer a concise core file over a sprawling one.
- Move detailed schemas, domain notes, or long examples into `references/`.
- Move deterministic transforms or brittle sequences into `scripts/`.

Long skills are not inherently better. Competing instructions degrade reliability.

## 6. Composability

Skills should support handoffs.

Ask:

- Can another agent act on this output without reinterpreting it?
- Does the skill produce artifacts in a stable enough shape for downstream work?
- Is the output useful in a larger chain, not just as a one-off response?

Treat the output as part of a workflow, not as an isolated answer.

## 7. Determinism Boundary

Use prose for reasoning. Use scripts for hardwired behavior.

When the desired behavior depends on exact parsing, exact formatting, or a fragile sequence, the skill should recommend or include a script instead of overpromising that plain language will be enough.

## 8. Testing And Iteration

High-quality skills are versioned and tested.

- run a basket of representative prompts or tasks
- compare revisions against prior versions
- verify trigger quality as well as output quality
- keep refining weak descriptions and vague contracts

Treat a skill as a compounding workflow asset, not a static prompt.
