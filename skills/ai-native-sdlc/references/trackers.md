# Task links, workspace, and delivery

The intent lives in the tracker (Linear, GitLab, GitHub), not in the repo.
A task on the board is an accepted intent: it was refined and prioritized
there, so the tracker board *is* the Plan gate. The agent reads the task and
starts at Design. There is no `intent.md` in the project.

This file covers the edges of the loop — getting from a link to the right
branch, and from a reviewed change to an opened MR/PR. The phases in between
are in `references/playbook.md`.

## Starting from a link

The user passes a task link (`/ai-native-sdlc <link>` or "run the workflow
for <link>") from the repo the work belongs to. No configuration: the repo is
the current checkout, and the forge comes from its `origin` remote.

1. **Resolve the link** — deterministic, offline:

   ```bash
   python3 <skill>/scripts/tracker_link.py parse "<link>"
   ```

   | Field | Use |
   |---|---|
   | `system`, `ref` | which tracker; the native reference (`ENG-123`, `group/project#42`, `owner/repo#42`) for commits and the MR/PR |
   | `slug`, `change_dir` | the task id for the branch and folder (`eng-123`, `42`, `backlog-42`); `docs/changes/<slug>` holds its spec.md and plan.md |
   | `current_repo` | origin, `forge` (`gitlab` → `glab` + MRs, `github` → `gh` + PRs), `branch`, `default_branch`, `dirty` |
   | `repo_matches` | whether a GitLab/GitHub task belongs to this repo (null for Linear) |
   | `on_task_branch` | whether the checked-out branch is already this task's |
   | `state` | `spec` and `plan` status and the `next` step, for resuming |

   Detection is by link shape — `linear.app`, GitLab's `/-/` separator on any
   host (self-hosted included), `github.com` — so no host list is kept.
   Exit 1 means the link is not a task (board, epic, project, MR) or is
   unrecognized: say so and ask for the task link. Never guess the system from
   the page content.

2. **Read the task** — title, description, labels, comments, and its
   acceptance criteria (Review checks them one by one). Read only:

   | System | Read with |
   |---|---|
   | Linear | Linear MCP connector (`get_issue` + its comments) |
   | GitLab | GitLab MCP connector, or `glab issue view <id> -R <project> --comments` (self-hosted: set `GITLAB_HOST=<host>`) |
   | GitHub | `gh issue view <link> --comments` |

   If no connector or CLI is available or authenticated, stop and tell the
   user which one to set up. Do not work from a pasted summary instead of the
   task.

3. **Confirm the repo.** `repo_matches: false` means a GitLab/GitHub task
   from another project than the checkout: ask whether to switch repos, or
   whether this repo is where the work lands (issues kept in a backlog
   project — note it in the project's `## Tracker` section). A Linear task
   carries no repo (`repo_matches: null`): the current checkout is the repo;
   outside a repo (`current_repo: null`), ask which one.

## Workspace — before reading any code

Never build on whatever happens to be checked out: a task started on someone
else's branch inherits their work in its diff.

- **Already on the task's branch** (`on_task_branch: true`): continue — this
  step is a one-line confirmation.
- **Dirty tree** (`dirty: true`) on another branch: stop and let the user
  decide (stash, commit, or switch). Never carry or discard their changes.
- **Otherwise** propose the branch and wait for the go-ahead before creating
  it: `<type>/<slug>-<summary>` (`feat/eng-123-csv-export`,
  `fix/42-date-off-by-one`; type `feat`, `fix`, or `chore`) off the fetched
  `default_branch` (`git fetch origin && git switch -c <branch> origin/<default>`),
  unless the repo's CLAUDE.md sets another rule. Starting the last segment
  with the slug is what lets `on_task_branch` and `check_plan_sync.py --hook`
  recognize the task.
- **Worktree** only when the user wants the current checkout untouched or is
  running tasks in parallel: `git worktree add .worktrees/<slug> -b <branch>
  origin/<default>`. Say the cost — each worktree needs its own dependency
  install, and a dev stack bound to the main path will not see it.

## Resuming

A second run with the same link continues where the task stopped, from
`state.next`:

| `next` | Means | Continue with |
|---|---|---|
| `design` | no spec, no plan | size the change, then Design (full) or Build (light) |
| `approve-spec` | spec.md is Draft | present the spec for approval |
| `plan` | spec approved, no plan | Build: plan mode |
| `approve-plan` | plan.md is Draft | present the plan for approval |
| `implement` | plan approved | compare the working tree with the plan's "Files that change", then implement what is missing or go to Review |

Say what the state is before acting on it. If the artifacts and the working
tree disagree (a Draft plan but finished code, say), report both and ask
rather than picking one.

## Delivery — the end of the loop

Nothing is committed during Build. When Review is done, ask once: *commit,
push, and open the MR/PR?* — one go-ahead covers all three, and nothing
leaves the machine or enters history without it. Then, if the project's
CLAUDE.md has a `## Commit and MR/PR` section, use the skills and rules it
names; they win over everything below. Otherwise:

- **Commit** only verified code, staging explicit paths (never `git add -A`),
  one logical change per commit, in the repo's style (read `git log`), citing
  the ref. The task's `docs/changes/<slug>/` goes in with the code. Never
  bypass hooks or signing (`--no-verify`).
- **MR/PR body** from the repo's template (`.gitlab/merge_request_templates/`,
  `.github/PULL_REQUEST_TEMPLATE.md`), else the skill's
  `assets/PULL_REQUEST_TEMPLATE.md`, filled from the spec, the plan, the
  review, and the verify output — never an invented body. Put the closing
  keyword in it (`Closes group/project#42`, `Fixes ENG-123`) so the tracker
  moves the task on merge. Reference a task from another project in its
  qualified form (`group/backlog#42`); a bare `#42` points at this repo.
- **Open it** with the forge from `current_repo` (`git push -u origin
  <branch>`, then `glab mr create` or `gh pr create`), then stop. Merge and
  deploy are the team's.

## Rules

- **Never edit the task description.** The task is the accepted intent; the
  agent does not rewrite, reformat, or relabel it.
- **Gaps go to the spec, not the task.** Anything missing or ambiguous in the
  task becomes an "Open question" in `spec.md` (or plan.md on the light path)
  or a question to the user. If the task is too thin to design from, say so —
  sending it back to refinement is the product owner's call, made on the
  board.
- **Any write to the tracker needs the user's confirmation**: a comment, a new
  task, a status change. The only automatic write is the closing keyword in
  the MR/PR, which the tracker applies on merge.
- **One task per run.** Board, epic, and project links are rejected; the user
  picks the task. Work that spans several repos is one task per repo.

## New work without a task

When the user brings an idea with no task yet, draft the task description in
the shape of `assets/intent.md` and create it in the tracker only after the
user confirms. It enters the loop once it is on the board.

## Configuration

None by default. Authentication belongs to the tracker's own connector or CLI
(`glab auth login --hostname <host>`, `gh auth login`, the Linear MCP), never
to this skill.

For a project that differs from the defaults, add a `## Tracker` section to
its CLAUDE.md (the template ships it empty), for example:

- "Tasks live in Linear team ENG (read with the Linear MCP); code on GitHub."
- "Issues live in `group/backlog`, not in this project; MRs reference them as
  `group/backlog#N`."
- "Branches: `<slug>-<summary>`, no type prefix." (keep the slug at the start
  of the last segment so resuming and the plan-sync hook still work)
