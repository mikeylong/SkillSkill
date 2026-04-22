---
name: frontend-skill-example-after
description: Design and implement visually directed landing pages or product UIs from requests like "make this feel premium" or "redesign this dashboard", producing a clear visual thesis, section plan, and restrained interface with strong hierarchy, imagery, and motion.
---

# Frontend Skill Example After

Use this skill when the request is not only to build UI, but to make the UI feel intentional. It is for landing pages, websites, demos, prototypes, and high-importance app surfaces where art direction, hierarchy, restraint, imagery, and motion materially affect the result.

Goal: ship interfaces that feel deliberate, premium, and current. Default toward award-level composition: one big idea, strong imagery, sparse copy, rigorous spacing, and a small number of memorable motions.

Do not use this skill for routine bug fixes, narrow component edits inside an established design system, or purely functional UI work where visual direction is not part of the ask.

For detailed heuristics and composition rules, use [references/visual-playbook.md](references/visual-playbook.md) after choosing the correct mode.

## Contract

This skill produces:

- a concrete visual direction the agent can implement, not just styling adjectives
- a page or surface structure matched to the request type
- a restrained interface with one dominant idea per section and a small number of intentional motions
- a short rationale the user or downstream agent can follow without reinterpreting the design intent

This skill may assume:

- the agent can choose layout, typography, spacing, and imagery direction when the user leaves them open
- the existing brand or product system should be preserved unless the user explicitly asks for a rework

This skill does not guarantee:

- net-new brand strategy, illustration systems, or custom image generation unless the user asks for them
- a marketing-style hero for operational product surfaces
- cardless layouts when the interaction model genuinely depends on cards

## Mode Selection

Choose one mode before designing:

- marketing surface: brand, promise, CTA, and a dominant visual lead the page
- product surface: orientation, status, action, and workflow lead the page
- hybrid demo: one branded entry moment leads into a working product surface quickly

If the request is ambiguous, infer the mode from the user's actual job:

- selling, launching, inviting, announcing: marketing surface
- operating, monitoring, analyzing, managing: product surface
- showcasing a product while still proving usability: hybrid demo

## Working Model

Before building, write three things:

- visual thesis: one sentence describing mood, material, and energy
- content plan: hero, support, detail, final CTA
- interaction thesis: 2-3 motion ideas that change the feel of the page

Each section gets one job, one dominant visual idea, and one primary takeaway or action.

If the task is implementation rather than concepting, turn these three items into concrete layout and styling decisions immediately instead of leaving them as abstract notes.

## Edge Cases

- Existing design system: preserve its type scale, tokens, and interaction patterns. Improve hierarchy, spacing, composition, and emphasis before inventing a new visual language.
- Weak or missing imagery: switch to typography, shape, contrast, or product UI as the anchor. Do not force a photo-led page with placeholder visuals.
- Dense operational data: clarity wins over atmosphere. Reduce chrome and marketing copy before reducing information value.
- Mobile pressure: cut secondary copy, decorative media, and ornamental motion before compressing the primary message or CTA.
- Accessibility conflicts: contrast, readability, focus states, and tap targets win over the visual thesis.
- User asks for "more premium", "more modern", or "make it pop": translate that into one concrete hierarchy change, one composition change, and one motion choice rather than adding decorative UI.

## Output Shape

When doing implementation work, the agent should deliver:

- the actual UI changes
- a short summary of the visual thesis
- the chosen structure or surface mode
- the few motion or interaction ideas that materially affect the feel

When the user asks for direction only, return:

- `Visual Thesis`
- `Structure`
- `Motion Plan`
- `Asset Needs`
- `Risks`

## Example Requests

- `Design a premium launch page for our AI travel product.`
- `Redesign this dashboard so it feels calmer and less card-heavy.`
- `Make this prototype feel more editorial and less template-like.`

## Litmus Checks

- Is the selected mode correct for the user's actual job?
- Is there one dominant idea per section?
- Is the UI clearer and more intentional, not just more decorated?
- Does the work preserve existing product conventions unless the user asked for a rebrand?
