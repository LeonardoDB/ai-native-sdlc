# Adoption — tailoring the workflow to a team

Adopting the loop in a repo takes little: install the skill, let the tracker's own CLI or connector authenticate, and fill in the repo's CLAUDE.md. Everything below is how to make it fit a team.

## First run

1. Agree that a task on the board is an accepted intent, and write new tasks in the `assets/intent.md` shape.
2. Write a one-page CLAUDE.md (`scripts/init_workflow.py` scaffolds a starter): one command each for build, test, lint, and typecheck, each exiting non-zero on failure.
3. Wire the checks in MR/PR CI: `check_plan_sync.py --base … --head HEAD`, `check_tdd.py --base …`, `check_diff_hygiene.py --base …`; optionally `check_plan_sync.py --hook` as a pre-commit hook.
4. Run one task end to end and watch where it bends before tuning anything.

## How each rule is enforced

Each hard rule has an advisory layer (the skill makes compliance likely), a deterministic layer (code makes violation nearly impossible), or neither — then it rests on review. Anything that must always hold belongs in the deterministic column.

| Rule | Deterministic | Otherwise |
|---|---|---|
| 1. Gates are real | `check_plan_sync.py` refuses implementation without `Status: Approved` in plan.md | **The agent writes that line** when you approve, so the check proves a plan was recorded as approved, not who approved it. The real backstop is human: spec and plan land in the MR/PR, where the team reviews them. |
| 2. Stop at the MR/PR | `hooks/gate.py` blocks merges, pushes to the default branch, `--no-verify`, bare force-pushes; branch protection on the forge | — |
| 3. Plan first | `check_plan_sync.py`: every changed file is in the approved plan's Files that change | — |
| 4. Shape before code | `check_diff_hygiene.py`: no open architect finding, the verdict recorded | that the stubs came before the tests rests on the agent |
| 5. Test first, typed | `check_tdd.py` (green with the change, red without); `check_diff_hygiene.py` (suppressions, skips, rewritten tests); the typecheck; optionally `check_mutations.py` | — |
| 6. Verify before asking | `hooks/gate.py` runs the checks before any push or MR/PR | build and lint rest on CLAUDE.md's commands |
| 7. Evidence | — | REVIEW.md; the reviewer brief |
| 8. Subagents bounded | — | the briefs in `references/agents/` |
| 9. Encode lessons | — | CLAUDE.md; the second-time-mistake rule in reviews |

The checks parse Python and JS/TS best: `check_tdd.py` and `check_plan_sync.py` work in any language (they run your commands and read git), `check_mutations.py` mutates only common code suffixes, and `impact_map.py` resolves imports only for Python and JS/TS.

## Models

The session plans and judges; mechanical work can run cheaper. Run the session on the strongest model you have, and set each subagent's model in CLAUDE.md:

```markdown
## Models

- explorer: sonnet
- architect: inherit
- builder: sonnet
- reviewer: inherit
```

`inherit` is the session's model. `builder: inherit` builds the slices in the session instead of dispatching them. The choice is advisory — no script can see which model ran — but a weaker builder cannot get past the checks.

## CLAUDE.md as repository memory

CLAUDE.md gives the agent what a new joiner needs: commands with healthy output, conventions, architecture, and the mistakes the team sees most — plus pointers to the tracker exceptions, the knowledge stores, the models, and the commit and MR/PR skills. Keep it under a page; the agent reads all of it at session start. When the agent makes a mistake twice, the correction goes in. Many repos sharing a setup can share one CLAUDE.md in their parent folder.

## Org standards as skills

For a policy that must be applied consistently (security, API design, brand, code style), write a skill: a folder with a SKILL.md whose frontmatter says when it triggers and whose body says what to do. Put it in `.claude/skills/<name>/` or ship it in a plugin, test that it triggers, and have the policy owner sign off on changes. Point the workflow at it from CLAUDE.md: a style skill in `## Conventions`, commit and MR/PR skills in `## Commit and MR/PR`. A skill is advisory; a policy that must always hold needs a hook or a check behind it.

## Hooks

The workflow ships one: `hooks/gate.py`, a PreToolUse hook on Bash. It blocks merges (`glab mr merge`, `gh pr merge`), pushes to the default branch, `--no-verify`, and force-pushes without a lease, and lets a task branch be pushed or its MR/PR opened only when the tree is committed and `check_plan_sync`, `check_tdd`, and `check_diff_hygiene` pass against the default branch (`SDLC_GATE_MUTATIONS=1` adds `check_mutations`). Branches without a `docs/changes/<task>/plan.md` are left alone. It uses the repo's scaffolded `scripts/` when present, else the skill's.

The plugin wires it for you. With the skill-only install, add it to `~/.claude/settings.json`:

```json
{"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
  {"type": "command", "command": "python3 ~/.claude/skills/ai-native-sdlc/hooks/gate.py"}]}]}}
```

There is deliberately no Stop hook: a failing test is normal mid-slice, and the agent must stay free to stop and ask. Add your own hooks for protected paths, formatting, and secrets; keep them fast and scoped to the file that changed.

## Review culture

REVIEW.md sets the passes, the evidence requirement, severity levels, and the 5-nit cap. The agent runs them on its own change before asking to open the MR/PR; the team's review on the MR/PR stays human.

## Parallel work

Each task has its own `docs/changes/<task>/` folder and branch, so parallel tasks do not collide; give each session its own worktree (`.worktrees/<task>`, ignored by the scaffolded `.gitignore`). Start with two or three — the ceiling is how many streams one person can review properly. Once the guardrails are tuned, auto-accept for routine work is reasonable: approve the plan, let the agent work, review the artifacts.

Other recurring jobs can become subagents in `.claude/agents/*.md` — a verifier that runs the app and checks the change, for example. Name each for its function, commit it, and keep its report bounded and evidence-based.

## Source of truth

Each artifact has one home, and the others cross-reference it: the task in the tracker; the spec and plan in `docs/changes/<task>/`; code review and merge in the MR/PR. Keep the team's existing tools — this changes the process, not the toolchain.
