# Adoption — staged rollout

The plays have dependencies. Start with any play that nothing points into (a leaf play — it needs nothing first), then adopt the plays that depend on it. The adoption order is not the phase order: several later-phase plays are cheap and come first.

## Dependency order

The plays form a directed dependency graph. Start at any leaf play (nothing points into it), then adopt the plays that depend on it — see `references/graph.md` for why the workflow is engineered as a graph.

| Layer | Plays |
|---|---|
| Start here (no prerequisites) | capture intent, CLAUDE.md, feedback loop, build-time hooks, plan mode |
| Second | skills, subagents, continuous evals |
| Third | requirements + design, PR review |
| Fourth | CI/CD integration, approval gates |
| Last | close the loop (monitoring → new intents) |

## Framework mapping

The plays are written generically; each framework has its own names for the same roles:

| Role | Claude Code | Codex |
|---|---|---|
| Repository memory | CLAUDE.md | AGENTS.md |
| Skills | `.claude/skills/` | `~/.codex/skills/` |
| Subagents | `.claude/agents/*.md` | Codex subagent configuration |
| Hook wiring | `.claude/settings.json` + `.claude/hooks/` | Codex settings/hooks |
| Artifacts | intent.md, spec.md, plan.md, REVIEW.md, bands.yaml | same files |

When this skill or the templates say CLAUDE.md or `.claude/`, map to the equivalent in the target framework. The artifacts, the templates, and the scaffold script are framework-neutral.

## Minimal first run

1. Ship the intent.md template and require it for new work (capture intent).
2. Create a one-page CLAUDE.md and keep it under a page (CLAUDE.md).
3. Teach the feedback loop: one command each for build/test/lint that exits non-zero on failure (feedback loop).
4. Add one deterministic hook — protected paths, secrets, or the release gate (hooks).
5. Start agent sessions in plan mode so nothing is implemented without an accepted plan (plan mode).

That alone moves requirements from weeks to hours and makes the audit trail real.

## Encoding org standards as skills

For any policy that must be applied consistently (brand, security, UX, API design), create a skill: a folder with SKILL.md, frontmatter that says when it triggers, and a body that says what to do. Place it in `.claude/skills/<name>/` to ship with the code, or distribute it through a plugin. Test that it triggers, and have the policy owner sign off on changes. Rule of thumb: skills for institutional knowledge that must be applied consistently; CLAUDE.md for working knowledge; prompts for one-offs.

## Wiring hooks

Hooks are the deterministic backstop. Decide which red lines are non-negotiable and enforce them with hooks owned by platform/IT (managed settings) so individuals cannot disable them. Build-phase: block protected paths, auto-format, keep credentials out of diffs. Gate hooks: allow, ask, or block; the release gate is the canonical ask. Example wiring for Claude Code:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": "${CLAUDE_PROJECT_DIR}/hooks/production-gate.sh" }
        ]
      }
    ]
  }
}
```

For regulated organizations, `assets/managed-settings.example.json` is a starting point to tailor (permissions, sandbox, credentials, managed hooks/MCP, version floor).

## Building the eval suite

Start with the 10 most recent real tasks, then grow to 20–50. Each eval is a prompt, an expected outcome, and a machine-checkable pass condition. Run the suite on a schedule and on any change to CLAUDE.md, skills, or hooks. Gate configuration changes on the pass rate. Add an eval after every production incident. A GitHub Actions example ships in `assets/agent-evals.yml.example`.

## Review culture

REVIEW.md defines the passes (bugs, security, compliance) and the evidence requirement; agree on severity levels, the 5-nit cap, and what to skip. Reviews are bidirectional (@claude on a comment triggers a fix; a slash command babysits PRs to merge). Second-time mistakes land in CLAUDE.md as part of the review. The tech lead tunes the setup monthly.

## Parallel sessions and subagents

Split the plan into independent file sets; one worktree per session; start with 2–3. Subagents in `.claude/agents/*.md` package recurring jobs:

```markdown
---
name: verifier
description: Runs the app and checks the change works before the session reports done
tools: Bash, Read
---
Start the app with make run. Exercise the changed behavior and the two nearest
neighboring flows. Report what you ran, what you saw, and any behavior that does
not match plan.md. Do not fix anything; report only.
```

Subagent hygiene: name each one for its function, commit the definition so the team shares it, and keep it visible to the engineer — the orchestrating agent explains why it was dispatched and summarizes its output. Give every subagent a bounded deliverable and an evidence-based report (what it ran, what it saw, what it did not check). A subagent is a scoped helper, not a black box: if it goes quiet, returns assertions without evidence, or acts on stale repo state, inspect or replace it.

## Source of truth for each artifact

Existing systems (Jira, ServiceNow, Figma, change boards) are hard to displace. For every artifact the process produces, name one system as the source of truth:

- **Repo as truth:** the markdown artifacts are authoritative; legacy systems reference files within commits. Cleanest for engineering-led organizations.
- **Legacy system as truth:** the record lives in Jira/ServiceNow; the agent reads it at session start and writes outcomes back through an MCP connector.
- **Linkage as the minimum bar:** artifacts carry the record ID and legacy records carry the commit SHA. A good place to start when transitioning.

## Closing the loop

Add `bands.yaml` plus a deterministic, unit-tested detection script; define the 1σ/2σ/3σ responses; make diagnosis produce intent.md automatically. Trigger from a schedule, a monitoring webhook, or chat. Route chat alerts into the same pipeline and keep the channel as audit evidence.

## Existing tooling

Keep Jira, Figma, GitHub, and Slack. Repo markdown is the source of truth (or linked to it, per artifact). This workflow changes the process, not the toolchain.
