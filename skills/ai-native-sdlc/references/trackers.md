# Intent from the tracker

The intent lives in the tracker (Linear, GitLab, GitHub), not in the repo.
A task on the board is an accepted intent: it was refined and prioritized
there, so the tracker board *is* the Plan gate (`tracker_board` in
`workflow-graph.yaml`). The agent reads the task and starts at Design. There
is no `intent.md` in the project.

## Starting from a link

The user passes a task link (`/ai-native-sdlc <link>` or "run the workflow
for <link>") from the repo the work belongs to. No configuration: the repo is
the current checkout, and the forge comes from its `origin` remote.

1. **Resolve the link** — deterministic, offline:

   ```bash
   python3 <skill>/scripts/tracker_link.py parse "<link>"
   ```

   The JSON names the `system`, the native `ref` (`ENG-123`,
   `group/project#42`, `owner/repo#42`), the `current_repo` (from
   `git remote get-url origin`, with its `forge`), and `repo_matches`.
   Detection is by link shape — `linear.app`, GitLab's `/-/` separator on any
   host (self-hosted included), `github.com` — so no host list is kept.
   Exit 1 means the link is not a task (board, epic, project, MR) or is
   unrecognized: say so and ask for the task link. Never guess the system from
   the page content.

2. **Read the task** — title, description, labels, and comments. Read only:

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

4. **Record the source (optional, when the project uses the gate ledger).**
   The board is the gate, so the record names the task, not a human approver:

   ```bash
   python3 scripts/gate_ledger.py record --gate tracker_board \
     --artifact "<ref>" --approver tracker --evidence "<link>"
   ```

5. **Design.** Produce `spec.md` from the task and the org's skills. Its
   header cites the source: `Intent: <ref> <link> (read <YYYY-MM-DD>)`.
   Continue the loop as usual: spec approved → `plan.md` → code + tests →
   MR/PR.

6. **Close the loop in the tracker through the MR/PR.** Name the branch after
   the ref (`eng-123-csv-export`, `42-csv-export`) and put the closing keyword
   in the MR/PR description (`Closes group/project#42`, `Fixes ENG-123`), so
   the tracker moves the task when the change merges.

## Rules

- **Never edit the task description.** The task is the accepted intent; the
  agent does not rewrite, reformat, or relabel it.
- **Gaps go to the spec, not the task.** Anything missing or ambiguous in the
  task becomes an "Open question" in `spec.md` or a question to the user. If
  the task is too thin to design from, say so — sending it back to refinement
  is the product owner's call, made on the board.
- **Any write to the tracker needs the user's confirmation**: a comment, a new
  task, a status change. The only automatic write is the closing keyword in
  the MR/PR, which the tracker applies on merge.
- **One task per run.** Board, epic, and project links are rejected; the user
  picks the task. Work that spans several repos is one task per repo.

## New work without a task

When the user brings an idea, or Maintain produces a diagnosis, draft the
task description in the shape of `assets/intent.md` and create it in the
tracker only after the user confirms. It enters the loop once it is on the
board.

## Configuration

None by default. Authentication belongs to the tracker's own connector or CLI
(`glab auth login --hostname <host>`, `gh auth login`, the Linear MCP), never
to this skill.

For a project that differs from the defaults, add a `## Tracker` section to
its CLAUDE.md (the template ships it empty), for example:

- "Tasks live in Linear team ENG (read with the Linear MCP); code on GitHub."
- "Issues live in `group/backlog`, not in this project; MRs reference them as
  `group/backlog#N`."
