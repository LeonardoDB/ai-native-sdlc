# MR/PR feedback

The main loop ends when the MR/PR is opened. When the team's review comes
back, the user passes the MR/PR link (`/ai-native-sdlc <MR link>`) and one
feedback round runs: read every thread, fix what is in scope, re-verify, and
— on one go-ahead — push and reply. It never merges.

## 1. Resolve and read

- `tracker_link.py parse <link>` returns `kind: merge_request` with its ref
  (`group/project!12`, `owner/repo#12`).
- Read the MR/PR: description, diff, and **every discussion**, resolved or
  not, with its author and the code it points at.

  | Forge | Read with |
  |---|---|
  | GitLab | `glab mr view <id> --comments`; unresolved threads: `glab api projects/<url-encoded project>/merge_requests/<id>/discussions` |
  | GitHub | `gh pr view <id> --comments`; line comments: `gh api repos/<owner>/<repo>/pulls/<id>/comments` |

## 2. Workspace

- Check out the MR/PR's source branch (`glab mr checkout <id>`,
  `gh pr checkout <id>`) after the user confirms; a dirty tree stops here.
- The branch's slug names the task folder (`feat/eng-123-x` →
  `docs/changes/eng-123/`). Add a `### Round <n> (MR feedback)` heading under
  plan.md's Review.

## 3. Triage every thread

Classify each thread before changing anything, and list the result in the new
round:

- **Question or clarification** — draft a reply; no code.
- **Change in scope** — fix it. A behavior change gets its own red → green
  slice; a mechanical one (naming, a comment, a type) is edited directly.
  Record it `thread → file:line → fix`.
- **Out of scope** — draft a reply proposing a follow-up task, and create the
  task only with the user's confirmation.
- **Disagreement** — draft a reply with the evidence (the spec, the test, the
  code); never silently comply with a change that breaks an acceptance
  criterion.

## 4. Verify

Run the same checks as Review — `check_plan_sync`, `check_tdd`,
`check_mutations`, `check_diff_hygiene`, `impact_map --check`, typecheck, and
the suite — and dispatch the reviewer on the round's diff when the fixes are
more than mechanical.

## 5. One go-ahead, then stop

Ask once: *push the fixes and post the replies?* On the go-ahead:

- Commit following the repo's convention — `git commit --fixup <sha>` when it
  autosquashes, plain commits otherwise. Push; if history was rewritten, only
  with `--force-with-lease`.
- Post each drafted reply on its thread. Resolve only the threads this round
  addressed, and only where the forge convention lets the author resolve.
- Stop. Merging stays with the team; the gate hook blocks it anyway.
