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

<Language/framework conventions, formatting, naming.>

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

## Hooks

<Deterministic hooks and what they enforce.>
