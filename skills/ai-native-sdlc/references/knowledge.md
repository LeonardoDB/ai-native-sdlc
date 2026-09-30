# Knowledge bases — recall before, capture after

The workflow reads the project's knowledge before it decides, and writes back
what the task taught so the next session does not re-derive it. Both are
driven by the `## Knowledge base` section of CLAUDE.md, which declares the
**stores**; without it, recall reads the repo's own docs and capture goes to
the repo.

## Declaring the stores

One line per store — name, purpose, transport, who may write — plus the
conventions that apply to all of them:

```markdown
## Knowledge base

- decisions — why the system is the way it is (ADRs) — repo `docs/adr/` — anyone, via the MR
- domain — business rules, glossary, customer use cases — MCP `<wiki-server>` — agent, with confirmation
- runbooks — how to operate and debug each service — GitLab wiki of `group/ops` (`glab api projects/group%2Fops/wikis`) — read only
- Conventions: ADRs are `NNNN-title.md` from `docs/adr/0000-template.md`; wiki pages carry `service:` and `updated:` frontmatter; link related pages
- Store skills: use the `<wiki-skill>` skill to write to the domain wiki
```

- **Transport** is how to reach it: a repo path, an MCP server (connected
  with `claude mcp add`), or a CLI/API command. The agent never guesses one.
- **Who may write**: `anyone, via the MR` (repo stores — the write is part of
  the diff and the team reviews it), `agent, with confirmation` (external
  stores — written only inside the delivery go-ahead), or `read only`.
- Shared stores for every repo of a company go in the company folder's
  CLAUDE.md; a repo adds its own below it.

## Recall — before deciding

| Phase | Ask the stores for |
|---|---|
| Design | prior decisions in the area, domain rules, the glossary terms the task uses |
| Build (plan) | conventions and known gotchas for the files that change |
| Debugging | known root causes, past incidents, runbooks for the failing area |
| Review | the decisions the change must honor (the reviewer brief receives them) |
| MR feedback | the decision behind a thread's "why?" before answering it |

- Match the question to the store whose **purpose** fits; search the repo
  stores with Grep/Read and the MCP stores with their search tools.
- **Cite every recall** in the artifact that used it — spec.md's
  `Knowledge used`, plan.md's Build log — as a path (`docs/adr/0007-…md`) or
  `[kb:<store>] <page>`. Unmarked claims are the agent's own reasoning.
- Settled decisions are extended, not re-decided. A conflict between the task
  and a recalled decision is an open question for the user, never a silent
  choice.
- An unreachable store (MCP down, CLI unauthenticated) is reported, not
  skipped silently; continue with what is reachable and say what was not.
- An empty search is a result. Say so and move on.

## Capture — during and after

**During the task**, append to plan.md's `## Learnings` the moment something
worth keeping appears — one line, no ceremony:

```markdown
## Learnings

- [ ] gotcha: the tax table is cached for 24h; tests must call `tax.clear_cache()`
- [ ] decision: free-shipping threshold is inclusive (≥ 100), per the task's AC-1
```

**At the end of Review**, before asking to deliver, triage every entry:

- **promote** it to the store whose purpose fits — `- [promoted → decisions: docs/adr/0012-inclusive-threshold.md] …`;
- or **drop** it — `- [dropped: already in docs/adr/0004] …`.

An entry qualifies for promotion only if all of these hold:

1. **Reusable** — a future session on this repo is likely to need it.
2. **Verified** — backed by code, a test, command output, a decision record,
   or the user's own statement; not a guess.
3. **Non-obvious** — not visible in the nearest file.
4. **Not already there** — you searched the target store; update a stale page
   instead of adding a duplicate.
5. **In the right store** — the one whose purpose fits, filed where its
   conventions say.
6. **Safe** — no secrets, credentials, personal or customer data, raw logs.

Where the promotions land:

- **Repo stores** — write the file now; it is committed with the change and
  reviewed in the MR like code.
- **External stores** — draft the page or patch, and write it only as part of
  the delivery go-ahead (*commit, push, open the MR, and write 2 notes to the
  domain wiki?*), with the store's skill when one is named. Prefer patching an
  existing page to creating a new one.
- **Operating rules the agent must follow in this repo** go to CLAUDE.md, not a
  knowledge store; CLAUDE.md is not a place for history or gotchas.

`check_diff_hygiene.py` fails while any `- [ ]` entry is left untriaged.
