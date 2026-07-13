# Scored Skill Audit Rubric

Use this rubric for audits, revisions, ports, and release reviews. Score the package that actually runs, then note source-package differences separately.

## Scoring

Rate each dimension from 0 to 4:

- **0 — Absent or invalid:** The capability is missing, broken, or contradicted.
- **1 — Material weakness:** Common cases fail or require substantial agent guesswork.
- **2 — Partial:** The intent is visible, but important cases remain unreliable.
- **3 — Solid:** The package handles normal use with minor, bounded gaps.
- **4 — Release quality:** Evidence demonstrates clear, dependable behavior across boundaries and edge cases.

Calculate weighted points as `rating / 4 × weight`. Use `Not tested`, not a guessed rating, when behavioral evidence is unavailable; do not claim release readiness with an untested release gate. Use `N/A` only when a dimension truly cannot apply and explain why.

| Dimension | Weight |
| --- | ---: |
| Routing metadata and boundaries | 15 |
| Contract and output | 10 |
| Reasoning and authority | 10 |
| Edge cases, fallback, and safety | 10 |
| Capability fit and composition | 10 |
| Runtime provenance and source of truth | 10 |
| Progressive disclosure and resources | 10 |
| Platform-native packaging | 5 |
| Static integrity | 5 |
| Behavioral evidence and regression safety | 15 |

Interpret totals only when every required dimension has evidence:

- **90–100:** Release-ready, provided all release gates pass and no High finding remains.
- **75–89:** Strong but remediation remains.
- **50–74:** Not release-ready; material gaps remain.
- **Below 50:** Redesign or substantial repair is warranted.

## Dimension Checks

### Routing Metadata And Boundaries

- Keep the description on one line and within platform limits.
- Name concrete audit or execution contexts using realistic user language.
- Cover positive triggers, paraphrases, implicit cases, explicit invocation, nearest competitors, and must-not-trigger cases.
- Avoid broad language that captures ordinary work owned by native or specialist skills.
- Place all routing information in metadata available before the body loads.

### Contract And Output

- Define what the skill returns, its stable shape, allowed assumptions, and non-guarantees.
- Make outputs usable by the next agent or human without reinterpretation.
- Match the contract to each supported mode; do not require edits from a read-only audit.

### Reasoning And Authority

- Teach decision principles, quality criteria, and ambiguity resolution rather than only rote steps.
- State read/write authority and external side-effect boundaries.
- Match freedom to task fragility; move exact transforms and brittle sequences into scripts.

### Edge Cases, Fallback, And Safety

- Cover missing inputs, ambiguity, unavailable capabilities, conflicting sources, dirty worktrees, and partial failure.
- State safe fallbacks without promising unavailable behavior.
- Protect secrets, user data, production systems, and unrelated changes.

### Capability Fit And Composition

- Inventory relevant skills, tools, scripts, apps, connectors, MCP capabilities, assets, and dependencies.
- Distinguish active/discoverable capabilities from documented assumptions.
- Compose with native or specialist capabilities instead of duplicating them.
- Keep the package focused on durable, non-obvious workflow knowledge.

### Runtime Provenance And Source Of Truth

- Identify the actual discovered runtime package and canonical source.
- Record adapters, mirrors, generation steps, copies, symlinks, hashes or commits, and drift.
- Validate the callable variant rather than only a convenient repository copy.

### Progressive Disclosure And Resources

- Keep the core concise and link each conditional reference directly.
- Read references completely when their path applies; avoid duplicating guidance between core and references.
- Keep scripts executable, deterministic, and tested.
- Use assets only for output resources; remove placeholders, orphans, oversized duplicates, and hidden instructions.

### Platform-Native Packaging

- Follow current native naming, frontmatter, metadata, directory, and invocation conventions.
- Keep generated adapters synchronized with the canonical behavioral contract.
- Verify UI metadata describes the current skill and points only to existing assets.

### Static Integrity

- Run the authoritative platform validator and every documented command.
- Check schema, links, paths, metadata constraints, script exits, and package contents.
- Label custom lint results as static checks; reject keyword-presence checks as evidence of quality.

### Behavioral Evidence And Regression Safety

- Test metadata routing independently from body execution.
- Compare incumbent or no-skill behavior with the candidate on representative tasks.
- Use fresh agents, clean fixtures, blinded variants, and no leaked diagnosis or expected answer.
- Capture prompt, artifact, environment, result, score, and evaluator provenance.
- Include common, boundary, failure, authority, and prior-regression cases.

## Finding Priority

- **High:** Causes unsafe action, invalid packaging, runtime failure, severe routing error, source/runtime corruption, or failure of a critical release gate.
- **Medium:** Materially weakens common behavior, composition, maintainability, or confidence but has a bounded workaround.
- **Low:** Improves clarity, efficiency, consistency, or hygiene without changing core reliability.

Fix High findings first, then routing and contract gaps, authority or safety gaps, runtime drift, behavioral regressions, and package hygiene. Preserve evidence and user changes while revising.

## Audit Completion Checklist

- Confirm that the full core and applicable references were read.
- Confirm that runtime and source were distinguished.
- Confirm that nearby capabilities and routing negatives were tested.
- Confirm that static and behavioral results were reported separately.
- Confirm that each score cites evidence and each unrun check says `Not tested`.
- Confirm that the report uses High, Medium, and Low labels and honors the selected authority mode.
