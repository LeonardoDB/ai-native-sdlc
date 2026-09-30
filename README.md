# AI-Native SDLC — from task to MR/PR

Give your coding agent a task link from Linear, GitLab, or GitHub, and it drives the work through design, build, and review to an opened MR/PR — with human approval gates at every handoff. Based on the first half of Anthropic's [AI-Native SDLC playbook](https://claude.com/blog/the-ai-native-sdlc-playbook).

> **The loop ends when the MR/PR is opened.** The agent never merges, deploys, or releases — the team reviews and merges, and deployment is the team's own pipeline.

This repo is a **Claude Code plugin** (the skill plus its gate hook), and the skill alone lives at `skills/ai-native-sdlc/`.

## The workflow

```
task link → Design → Plan → Shape → Build → Review → MR/PR opened ■ end
```

| Step | What happens | Gate |
|---|---|---|
| Design | the agent explores the code and writes `docs/changes/<task>/spec.md` (skipped for small changes) | you approve the spec |
| Plan | `plan.md`: files that change, one slice per acceptance criterion, the command that proves each | you approve the plan |
| Shape | the types and signatures are written as stubs; an **architect** subagent critiques them until it approves | the architect's verdict |
| Build | one criterion at a time, test first — each slice by a **builder** subagent on a cheaper model | — |
| Review | deterministic checks, then a fresh **reviewer** subagent; fixes; the criteria walked with evidence | you say *commit, push, open the MR/PR* |

The agent never merges or deploys; a hook blocks it. Running it again with the same link resumes where the task stopped. The whole contract is one page: [`SKILL.md`](skills/ai-native-sdlc/SKILL.md).

**Learn more:** [each step in detail](skills/ai-native-sdlc/references/playbook.md) · [task links and delivery](skills/ai-native-sdlc/references/trackers.md) · [tailoring to a team, and how each rule is enforced](skills/ai-native-sdlc/references/adoption.md)

## Install

### As a Claude Code plugin (recommended)

Installs the skill **and** the gate hook in one step, and updates with the repo:

```bash
claude plugin marketplace add LeonardoDB/ai-native-sdlc
claude plugin install ai-native-sdlc@ai-native-sdlc
```

(Inside a session: `/plugin marketplace add LeonardoDB/ai-native-sdlc`, then `/plugin install ai-native-sdlc@ai-native-sdlc`.) Update later with `claude plugin marketplace update ai-native-sdlc`. While developing the skill itself, load it straight from the checkout with `claude --plugin-dir ~/path/to/ai-native-sdlc`.

### As a Claude Code skill only

The skill without the hook. Link it rather than copying, so a `git pull` updates it (use `$CLAUDE_CONFIG_DIR/skills` if you set that variable):

```bash
mkdir -p ~/.claude/skills
ln -s "$PWD/skills/ai-native-sdlc" ~/.claude/skills/ai-native-sdlc
```

## Set up a repo

Nothing has to be copied into your repo; the scripts run from the installed skill.

1. **Authenticate the tracker** with its own tool — the skill holds no credentials: `glab auth login`, `gh auth login`, or the Linear MCP connector.
2. **Fill in the repo's `CLAUDE.md`** — commands (build, test, lint, typecheck), conventions, and only the optional sections that apply. `python3 skills/ai-native-sdlc/scripts/init_workflow.py path/to/repo` scaffolds a starter with all of them, plus `REVIEW.md` and the check scripts (existing files are skipped).

   | Optional section | Add it when |
   |---|---|
   | `## Models` | you want other models per subagent role than the defaults (explorer and builder `sonnet`, architect and reviewer the session's) |
   | `## Tracker` | tasks live somewhere the link and the git remote don't reveal |
   | `## Knowledge base` | the project has knowledge stores to recall from and write to ([knowledge.md](skills/ai-native-sdlc/references/knowledge.md)) |
   | `## Commit and MR/PR` | the project has its own commit or MR/PR skills or templates |
   | `## Code tooling` | there is an LSP or a library-docs tool the agent should use |
3. **Run the checks in CI** — `check_plan_sync.py --base origin/main --head HEAD`, `check_tdd.py --base origin/main`, `check_diff_hygiene.py --base origin/main` ([playbook](skills/ai-native-sdlc/references/playbook.md#mrpr-ci)).

With the skill-only install, also wire the gate hook ([adoption.md](skills/ai-native-sdlc/references/adoption.md#hooks)).

## Use it

From the repo the task belongs to:

- Claude Code: `/ai-native-sdlc https://gitlab.example.com/group/api/-/issues/42`

It works with Linear, GitLab (self-hosted too), and GitHub links, with no config. The MR/PR closes the task when the team merges it.

Review came back? Pass the MR/PR link (`/ai-native-sdlc <MR link>`): the agent triages every thread, fixes what is in scope test-first, re-runs the checks, and asks once before pushing and replying. A bug task starts from a reproduction and a root cause, not a guess.

No task yet? Describe the idea; the agent interviews you, drafts the task description, and creates it in the tracker once you confirm.

## Evals

`evals/` holds behavioral evals for Claude Code's native runner — offline
fixtures (a Python repo, a GitLab origin that pushes locally, a logging `glab`
stand-in) and mostly deterministic graders. See `evals/README.md`:

```bash
claude plugin eval . --scaffold --trust-plugin --no-publish --allow-tools Bash Edit Write
```

## Layout

```text
.
├── .claude-plugin/                # Claude Code plugin + marketplace manifests (repo root is the plugin)
├── hooks/hooks.json               # the plugin's hook wiring (gate.py on PreToolUse Bash)
├── .github/workflows/self-check.yml  # CI for this repo itself (validate + tests)
├── AGENTS.md                      # guidance for agents working in this repo
├── README.md
├── CHANGELOG.md
├── LICENSE
├── SECURITY.md
├── evals/                         # behavioral evals (claude plugin eval)
├── tests/                         # tests for every script and the scaffold
└── skills/
    └── ai-native-sdlc/
        ├── SKILL.md               # the whole contract on one page
        ├── references/
        │   ├── playbook.md        # phase-by-phase procedures
        │   ├── trackers.md        # task links, workspace, resuming, delivery
        │   ├── adoption.md        # tailoring to a team; how each rule is enforced
        │   ├── knowledge.md       # knowledge stores: recall per phase, capture with a quality gate
        │   ├── debugging.md       # bug tasks: reproduce, bisect, hypotheses, root cause
        │   ├── feedback.md        # one MR/PR feedback round
        │   └── agents/            # explorer, architect, builder, reviewer — subagent briefs
        ├── hooks/
        │   └── gate.py            # PreToolUse gate: no merge, checks before publishing
        ├── assets/
        │   ├── intent.md          # shape of a new tracker task description
        │   ├── spec.md            # → docs/changes/<task>/spec.md
        │   ├── plan.md            # → docs/changes/<task>/plan.md
        │   ├── CLAUDE.md          # repository-memory starter
        │   ├── REVIEW.md          # review standards
        │   ├── PULL_REQUEST_TEMPLATE.md  # fallback MR/PR body
        │   └── .gitignore
        └── scripts/
            ├── tracker_link.py    # resolve a task link (ref, slug, branch, resume state)
            ├── check_plan_sync.py # deterministic plan-vs-diff check
            ├── check_tdd.py       # AC coverage; each test green with the change, red without
            ├── check_mutations.py # optional: mutants on the changed lines must fail a test
            ├── check_diff_hygiene.py  # suppressions, skipped and rewritten tests
            ├── impact_map.py      # optional: who depends on the files a change touches
            ├── init_workflow.py   # scaffold CLAUDE.md, REVIEW.md, the checks
            └── quick_validate.py  # skill/plugin self-check
```

## Contributing

1. Create a branch: `git checkout -b my-change`.
2. Make your change, then run the self-check suite from the repo root:

   ```bash
   python3 skills/ai-native-sdlc/scripts/quick_validate.py skills/ai-native-sdlc
   bash tests/test_init.sh
   python3 -m unittest discover -s tests -v
   ```

   All checks must pass — CI runs the same checks (`.github/workflows/self-check.yml`).
3. Add a `CHANGELOG.md` entry under `[Unreleased]` for user-visible changes.
4. Commit with a clear message (`feat:`, `fix:`, `docs:`, `chore:`, `test:`).

Conventions: keep `SKILL.md` short and put phase detail in `references/`; keep templates generic — organization specifics belong in the adopter's own skills and CLAUDE.md; keep `plugin.json` and the SKILL.md `version` in sync (`quick_validate.py` enforces this). Security issues: see `SECURITY.md`.

## Attribution and license

Based on [The AI-Native SDLC playbook](https://claude.com/blog/the-ai-native-sdlc-playbook) by Anthropic's Applied AI team (2026). MIT licensed — see `LICENSE`.
