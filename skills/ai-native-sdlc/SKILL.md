---
name: ai-native-sdlc
description: Run the AI-native SDLC loop — Plan, Design, Build, Test, Deploy, Maintain — with versioned artifacts and human approval gates at every handoff. Use when the user states a goal, idea, feature, or change request and expects the agent to scaffold and drive the project through the full lifecycle instead of jumping straight to code.
---

# AI-Native SDLC

Turn a stated goal into a planned, built, tested, deployed, and monitored project by running the loop from Anthropic's AI-Native SDLC playbook: **Plan → Design → Build → Test → Deploy → Maintain**.

Every phase ends by committing a versioned artifact to git; the next phase starts by reading it. The commit chain is the audit trail: who asked, what the agent produced, and who approved. The agent does the generating, verifying, and mechanical work. Humans keep the judgment calls and the final approvals.

## Hard rules

1. **Human gates are real gates.** Do not advance without approval: intent accepted → Design; spec approved → Build; plan approved → code; PR merged → Deploy; release authorized → production.
2. **Never cross the production gate.** Agent-generated changes stop at the merge/release boundary. High-risk actions (production config, migrations, releases) require explicit human authorization, enforced by a hook where possible.
3. **Verify before asking for review.** Run build, tests, lint, and screenshots yourself first; fix what fails; only then hand work to a human.
4. **Encode repeated lessons.** The same mistake twice → write the correction into the project's CLAUDE.md, a skill, or a hook.
5. **Evidence in reviews.** Every finding cites file/line and concrete evidence, ordered by severity, with at most 5 nit comments per review.
6. **Plan mode first.** Nothing is implemented without an accepted plan; when implementation departs from the plan, update plan.md in the same commit.
7. **Reviews feed back.** When a review flags a mistake for the second time, the correction goes into CLAUDE.md as part of that review.

## Starting from an idea

When the user gives a goal or idea and there is no workflow in place yet:

1. Scaffold the artifact skeleton with `scripts/init_workflow.py <project-dir> --name "<project name>"`, or copy templates from `assets/` into an existing repo.
2. Run **Plan**: interview the user with analyst-style questions — what cannot be done today, who is affected, what success looks like, constraints, what is out of scope — until the idea is concrete.
3. Write `intent/intent.md` from the template, commit it, and ask the product owner to accept or reject. Acceptance triggers Design.

If the user is already inside a later phase (for example, "review this PR" or "diagnose this incident"), start at that phase instead.

## Running the loop

Read `references/playbook.md` for the full phase-by-phase procedure: inputs, steps, outputs, exit gates, and proven prompt patterns for each phase.

At a glance:

| Phase | Reads | Produces | Gate (human approval) |
|---|---|---|---|
| Plan | user's idea | intent.md | accepted → Design |
| Design | intent.md + org standards | spec.md | approved → Build |
| Build | intent.md + spec.md | plan.md → code + tests → PR | plan approved before code; PR merged → Deploy |
| Test | repo + eval suite | eval results, regression evals | config changes that drop pass rate are reviewed |
| Deploy | merged PR + review findings | authorized release | agentic review + explicit release authorization |
| Maintain | production metrics | diagnosis → new intent.md | on-call triage: fix, schedule, or adjust thresholds |

## Templates and assets

The scaffold script copies the core skeleton into a new project; copy these manually when extending an existing repo:

- `assets/intent.md` — intent capture (problem, expected outcome, people/systems, constraints, out of scope, open questions)
- `assets/spec.md` — requirements + design specification with gotchas
- `assets/plan.md` — build plan (files, order, risks, verification)
- `assets/CLAUDE.md` — repository-memory starter (commands, conventions, common mistakes)
- `assets/REVIEW.md` — review standards (passes, evidence, severity, 5-nit cap)
- `assets/bands.yaml` — monitoring control bands for Maintain
- `assets/production-gate.sh` — release authorization hook
- `assets/evals.example.md` — eval case format for Test

Organization-level examples to wire up during adoption:

- `assets/hook-settings.example.json` — hook wiring for Claude Code
- `assets/agent-evals.yml.example` — CI eval workflow
- `assets/managed-settings.example.json` — regulated-enterprise managed settings

## Customization

Read `references/adoption.md` when tailoring the workflow to an organization or when asked how to roll this out gradually. It covers staged adoption, encoding org standards as skills, wiring hooks, building the eval suite, and keeping existing tools (Jira, Figma, GitHub, Slack) in place.
