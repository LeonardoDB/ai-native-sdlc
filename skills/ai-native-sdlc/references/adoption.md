# Adoption — tailoring the workflow to a team

The loop runs from a task on the board to an opened MR/PR. Adopting it in a repo takes little: install the skill, let the tracker's own CLI or connector authenticate, and fill in the repo's CLAUDE.md. Everything below is how to make it fit a team's standards.

## Framework mapping

The workflow is written generically; each framework has its own names for the same roles:

| Role | Claude Code | Codex |
|---|---|---|
| Repository memory | CLAUDE.md | AGENTS.md |
| Skills | `.claude/skills/` | `~/.codex/skills/` |
| Subagents | `.claude/agents/*.md` | Codex subagent configuration |
| Hook wiring | `.claude/settings.json` + `.claude/hooks/` | Codex settings/hooks |
| Artifacts | `docs/changes/<task>/spec.md` + `plan.md`, REVIEW.md (intent: the tracker task) | same files |

When this skill or the templates say CLAUDE.md or `.claude/`, map to the equivalent in the target framework.

## Minimal first run

1. Agree that a task on the board is an accepted intent, and write new tasks in the `assets/intent.md` shape (see `references/trackers.md`).
2. Create a one-page CLAUDE.md and keep it under a page.
3. Teach the feedback loop: one command each for build/test/lint that exits non-zero on failure.
4. Add the typecheck to CLAUDE.md's Commands, and wire the checks: `check_plan_sync.py --hook` as a pre-commit hook, and in MR/PR CI `check_plan_sync.py --base … --head HEAD`, `check_tdd.py --base …`, and `check_diff_hygiene.py --base …`. Add one hook for protected paths or secrets.
5. Start agent sessions in plan mode so nothing is implemented without an accepted plan.

## Encoding org standards as skills

For any policy that must be applied consistently (brand, security, UX, API design, code style), create a skill: a folder with SKILL.md, frontmatter that says when it triggers, and a body that says what to do. Place it in `.claude/skills/<name>/` to ship with the code, or distribute it through a plugin. Test that it triggers, and have the policy owner sign off on changes. Rule of thumb: skills for institutional knowledge that must be applied consistently; CLAUDE.md for working knowledge; prompts for one-offs.

Point the workflow at those skills from CLAUDE.md: a style skill in `## Conventions`, commit and MR/PR skills in `## Commit and MR/PR`.

## Wiring hooks

Hooks are the deterministic backstop for red lines: block protected paths, auto-format, keep credentials out of diffs. Team hooks live in the repo's settings file; non-negotiable ones belong in managed settings owned by platform/IT so individuals cannot disable them. Example wiring for Claude Code:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/protected-paths.sh" }
        ]
      }
    ]
  }
}
```

## Review culture

REVIEW.md defines the passes (bugs, security, compliance) and the evidence requirement; agree on severity levels, the 5-nit cap, and what to skip. The agent runs these passes on its own change before asking to open the MR/PR; the team's review on the MR/PR stays human. Second-time mistakes land in CLAUDE.md as part of the review.

## Parallel sessions and subagents

Split the plan into independent file sets; one worktree per session (`.worktrees/<task>`, ignored by the scaffolded `.gitignore`); start with 2–3. Each task already has its own `docs/changes/<task>/` folder, so parallel tasks in one repo do not collide. The workflow's own subagents — explorer and reviewer — are briefs in `references/agents/`; extend a brief's dispatch context rather than editing the brief for one project. Subagents in `.claude/agents/*.md` package other recurring jobs:

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

Subagent hygiene: name each one for its function, commit the definition so the team shares it, and keep it visible to the engineer — the orchestrating agent explains why it was dispatched and summarizes its output. Give every subagent a bounded deliverable and an evidence-based report (what it ran, what it saw, what it did not check). If it goes quiet, returns assertions without evidence, or acts on stale repo state, inspect or replace it.

## Source of truth

Each artifact has one home, and the others cross-reference it:

- **Intent** — the tracker task (Linear, GitLab, GitHub). The repo cites its ref; the MR/PR closes it.
- **Spec and plan** — `docs/changes/<task>/` in the repo, each citing the task ref.
- **Code review and merge** — the MR/PR on the forge.

Keep the team's existing tools. This workflow changes the process, not the toolchain.
