# CLAUDE.md — repository memory

Keep this file under one page. Add a rule when the same mistake happens twice.

> In Codex projects, the same content lives in AGENTS.md; the role is identical.

## Commands

- Build: `make build` (must finish with "Build succeeded")
- Test: `make test` (all green; never skip or delete a failing test)
- Lint: `make lint` (zero warnings)
- Itest: `make itest` (integration, needs docker)

## Verifying your work

Run build, test, and lint before reporting any task complete, and paste the output.
If a test fails, fix the code, not the test.

## Conventions

<Language/framework conventions, formatting, naming. If the project has a style
skill, name it here (e.g. "invoke the /code-style skill before writing or reviewing
code") — Build and Review invoke it, and every subagent brief repeats the instruction.>

## Architecture

<One-paragraph mental model: main modules and data flow.>

## Things the agent gets wrong

<Each mistake, its fix, and how to check for it.>

## Tracker

<Optional. Default: tasks come from the tracker link you pass; the forge comes from
`git remote get-url origin` (gh + PRs, glab + MRs). Fill in only what differs, e.g.
"tasks live in Linear team ENG (Linear MCP); code on GitHub", or "issues live in
group/backlog, not in this project".>

## Knowledge base

<Optional. Where the project's knowledge lives and how to search it — pointers only,
never the knowledge itself. Read during Design, not every session. e.g.
"docs/kb/ — decisions in docs/kb/decisions/, glossary in docs/kb/glossary.md", or
"MCP <server-name> — search by service name or domain term".>

## Commit and MR/PR

<Optional. The project's own skills or rules for committing and opening MRs/PRs —
they win over the workflow's defaults. e.g. "commit with the /commit skill",
"open MRs with the /create-mr skill", "MR template: .gitlab/merge_request_templates/default.md"
(or the command that fetches it when it lives in another repo),
"Conventional Commits; title `<type>(<scope>): <summary> (#<issue>)`".>

## Hooks

<Deterministic hooks and what they enforce.>
