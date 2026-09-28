# CLAUDE.md — repository memory

Keep this file under one page. Add a rule when the same mistake happens twice.

> In Codex projects, the same content lives in AGENTS.md; the role is identical.

## Commands

- Build: `make build` (must finish with "Build succeeded")
- Test: `make test` (all green; never skip or delete a failing test)
- Lint: `make lint` (zero warnings)
- Typecheck: `make typecheck` (zero errors, tests included)
- Itest: `make itest` (integration, needs docker)

## Verifying your work

Run build, typecheck, test, and lint before reporting any task complete, and paste the output.
If a test fails, fix the code, not the test. Never add `any`, casts, or suppressions to make
the type checker pass without a `reason:` on the same line.

## Conventions

<Language/framework conventions, formatting, naming. If the project has a style
skill, name it here (e.g. "invoke the /code-style skill before writing or reviewing
code") — Build and Review invoke it, and every subagent brief repeats the instruction.>

## Architecture

<One-paragraph mental model: main modules and data flow.>

## Things the agent gets wrong

<Each mistake, its fix, and how to check for it.>

## Code tooling

<Optional. Tools for precise edits: the LSP to use for definitions and references
instead of grep, and the library-docs tool or MCP to check a dependency's current
API before using it from memory. e.g. "LSP: pyright", "docs: <docs-mcp-name>".>

## Tracker

<Optional. Default: tasks come from the tracker link you pass; the forge comes from
`git remote get-url origin` (gh + PRs, glab + MRs). Fill in only what differs, e.g.
"tasks live in Linear team ENG (Linear MCP); code on GitHub", or "issues live in
group/backlog, not in this project".>

## Knowledge base

<Optional. The stores the workflow recalls from and captures to — pointers only, never
the knowledge itself. One line per store: name — purpose — transport — who may write.
Without this section, recall reads the repo's docs and capture goes to the repo. e.g.
- decisions — why the system is the way it is — repo `docs/adr/` — anyone, via the MR
- domain — business rules, glossary — MCP `<server-name>` — agent, with confirmation
- runbooks — operating each service — GitLab wiki of `group/ops` — read only
- Conventions: <file names, templates, frontmatter, link style>
- Store skills: <a skill to use for writing to a store, if any>>

## Commit and MR/PR

<Optional. The project's own skills or rules for committing and opening MRs/PRs —
they win over the workflow's defaults. e.g. "commit with the /commit skill",
"open MRs with the /create-mr skill", "MR template: .gitlab/merge_request_templates/default.md"
(or the command that fetches it when it lives in another repo),
"Conventional Commits; title `<type>(<scope>): <summary> (#<issue>)`".>

## Hooks

<Deterministic hooks and what they enforce.>
