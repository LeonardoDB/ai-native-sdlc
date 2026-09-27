# AI-Native SDLC — from task to MR/PR

Give your coding agent a task link from Linear, GitLab, or GitHub, and it drives the work through design, build, and review to an opened MR/PR — with human approval gates at every handoff. Based on the first half of Anthropic's [AI-Native SDLC playbook](https://claude.com/blog/the-ai-native-sdlc-playbook).

> **The loop ends when the MR/PR is opened.** The agent never merges, deploys, or releases — the team reviews and merges, and deployment is the team's own pipeline.

This repo is three things at once:

- A **Codex skill** at `skills/ai-native-sdlc/`, installable into `~/.codex/skills`.
- A **Claude Code skill** — the same folder, installable into `~/.claude/skills`.
- A **Claude Code plugin** and marketplace (`.claude-plugin/`) bundling the skill and the gate hook.
- A **Codex plugin** (`.codex-plugin/plugin.json` at the repo root) that bundles the skill.

**Learn more:** [Phase-by-phase playbook](skills/ai-native-sdlc/references/playbook.md) · [Task links and delivery](skills/ai-native-sdlc/references/trackers.md) · [Tailoring to a team](skills/ai-native-sdlc/references/adoption.md)

## The workflow

```
Plan (tracker board) → Design → Build → Review → MR/PR opened ■ end
                                                   │
                        team review, merge, deploy: outside this workflow
```

- **Plan** is the tracker: a task on the board is an accepted intent. The agent reads it, never edits it, and gets onto the task's branch before touching code.
- **Design** writes `docs/changes/<task>/spec.md`, after an **explorer** subagent maps unfamiliar code, with the org's skills and the project's knowledge base. Small, localized changes take the **light path** and skip the spec.
- **Build** writes `docs/changes/<task>/plan.md` in plan mode — with an **impact map** of who depends on the files it will change — then works **test-first**: types first when the change adds domain shapes, then one acceptance criterion at a time, red → green — nothing committed yet.
- **Review** runs the deterministic checks — every acceptance criterion has a test that **fails without the change and passes with it** (`check_tdd.py`), small mistakes on the changed lines fail a test (`check_mutations.py`), no unexplained `any`/suppressions/skipped or rewritten tests (`check_diff_hygiene.py`), the plan covers the diff (`check_plan_sync.py`) — then hands the change to a fresh-context **reviewer** subagent, filters its scored findings, checks the task's acceptance criteria with evidence, re-verifies, then asks once to commit, push, and open the MR/PR — the last thing the agent does.

Running the skill again with the same link resumes where the task stopped, read from its `docs/changes/<task>/` folder.

One folder per task keeps parallel branches in a repo from touching the same files. The agent does the generation, verification, and mechanical work; humans approve the spec and the plan, give the go-ahead to open the MR/PR, and review and merge it. The full phase → artifact → gate contract lives in `skills/ai-native-sdlc/SKILL.md`.

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

### As a Codex skill

```bash
mkdir -p ~/.codex/skills
cp -R skills/ai-native-sdlc ~/.codex/skills/
```

### As a Codex plugin

Clone or copy this repo to `~/plugins/ai-native-sdlc`, then add it to your personal marketplace at `~/.agents/plugins/marketplace.json`:

```json
{
  "name": "personal",
  "interface": {
    "displayName": "Personal"
  },
  "plugins": [
    {
      "name": "ai-native-sdlc",
      "source": {
        "source": "local",
        "path": "./plugins/ai-native-sdlc"
      },
      "policy": {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL"
      },
      "category": "Productivity"
    }
  ]
}
```

Installing the plugin also makes the bundled skill available, so you don't need to also copy it into `~/.codex/skills` — choose one path.

## Set up a repo

Nothing from this repo has to be copied into yours: the skill and its scripts run from the installed skill.

1. **Install the skill** (see [Install](#install)).
2. **Authenticate the tracker** with its own tool — the skill holds no credentials:
   - GitLab: `glab auth login --hostname <your-gitlab-host>` (or a GitLab MCP connector)
   - Linear: connect the Linear MCP connector
   - GitHub: `gh auth login`
3. **Add the optional sections** to the repo's `CLAUDE.md` (`AGENTS.md` in Codex) — only the ones that apply. Keep them to pointers; never paste the knowledge itself:

   ```markdown
   ## Tracker

   - Issues live in `group/backlog`, not in this project; MRs reference them as
     `group/backlog#N`.

   ## Knowledge base

   - `docs/kb/` — decisions in `docs/kb/decisions/`, glossary in `docs/kb/glossary.md`
   - MCP `<server-name>` — search by service name or domain term

   ## Commit and MR/PR

   - Commit with the `/commit` skill; open MRs with the `/create-mr` skill.
   - MR template: `.gitlab/merge_request_templates/default.md`
   ```

   A project style skill goes in the existing `## Conventions` section ("invoke the `/code-style` skill before writing or reviewing code"); Build and Review invoke it.

   | Section | Without it | Add it when |
   |---|---|---|
   | `## Tracker` | the repo is the current checkout; the forge comes from `git remote get-url origin` (`gh` + PRs, `glab` + MRs) | tasks live somewhere the link and remote don't reveal (another project, another tracker) |
   | `## Knowledge base` | Design skips the knowledge search | the project has a knowledge base (repo folder or MCP store); Design reads it before writing the spec |
   | `## Commit and MR/PR` | commits follow the repo's `git log` style and cite the task; the MR/PR body comes from the repo's template (else the skill's) with the closing keyword | the project has its own commit or MR/PR skills, a template elsewhere, or title/body rules |

   Many repos sharing the same setup? Claude Code also reads `CLAUDE.md` from parent directories, so one file in the folder that holds them (for example `~/work/<company>/CLAUDE.md`) covers every repo below it. Codex needs the sections in each repo's `AGENTS.md`.
4. **Add the typecheck command** to `## Commands` in CLAUDE.md, and optionally a `## Code tooling` section naming the LSP and the library-docs tool.
5. **Wire the gate hook** so the red lines hold outside the prompt — merges, pushes to the default branch, `--no-verify`, and bare force-pushes are blocked, and a task branch is published only with the checks passing. The plugin install does this for you; with the skill-only install, add it to your user `settings.json`:

   ```json
   {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
     {"type": "command", "command": "python3 ~/.claude/skills/ai-native-sdlc/hooks/gate.py"}]}]}}
   ```
6. **Enforce the checks in CI** (see the [playbook](skills/ai-native-sdlc/references/playbook.md#deterministic-checks)): `check_plan_sync.py --base origin/main --head HEAD`, `check_tdd.py --base origin/main`, `check_mutations.py --base origin/main`, `check_diff_hygiene.py --base origin/main`. To scaffold the four scripts together with a starter `CLAUDE.md` and `REVIEW.md` — existing files are skipped unless you pass `--force`:

   ```bash
   python3 skills/ai-native-sdlc/scripts/init_workflow.py path/to/your-repo
   ```

## Use it

From the repo the task belongs to:

- Claude Code: `/ai-native-sdlc https://gitlab.example.com/group/api/-/issues/42`
- Codex: `$ai-native-sdlc: run the workflow for https://linear.app/acme/issue/ENG-123`

The agent resolves the link (`scripts/tracker_link.py` — no config; self-hosted GitLab is recognized by its `/-/` link shape), reads the task, and starts at Design. It stops at each approval gate, asks once to commit, push, and open the MR/PR, and stops there. The MR/PR closes the task when the team merges it.

To see where work bends, across every repo of a company:

```bash
python3 ~/.claude/skills/ai-native-sdlc/scripts/metrics.py --repos ~/work/<company>/* --forge
```

Review came back? Pass the MR/PR link (`/ai-native-sdlc <MR link>`): the agent triages every thread, fixes what is in scope test-first, re-runs the checks, and asks once before pushing and replying. A bug task starts from a reproduction and a root cause, not a guess.

No task yet? Describe the idea; the agent interviews you, drafts the task description, and creates it in the tracker once you confirm.

## Layout

```text
.
├── .claude-plugin/                # Claude Code plugin + marketplace manifests (repo root is the plugin)
├── .codex-plugin/plugin.json      # Codex plugin manifest
├── hooks/hooks.json               # the plugin's hook wiring (gate.py on PreToolUse Bash)
├── .github/workflows/self-check.yml  # CI for this repo itself (validate + tests)
├── AGENTS.md                      # guidance for agents working in this repo
├── README.md
├── CHANGELOG.md
├── LICENSE
├── SECURITY.md
├── tests/                         # tests for every script and the scaffold
└── skills/
    └── ai-native-sdlc/
        ├── SKILL.md               # skill entrypoint (versioned; rule→enforcement matrix)
        ├── agents/openai.yaml     # UI metadata
        ├── references/
        │   ├── playbook.md        # phase-by-phase procedures
        │   ├── trackers.md        # task links, workspace, resuming, delivery
        │   ├── adoption.md        # tailoring the workflow to a team
        │   ├── debugging.md       # bug tasks: reproduce, bisect, hypotheses, root cause
        │   ├── feedback.md        # one MR/PR feedback round
        │   └── agents/            # explorer.md, reviewer.md — subagent briefs
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
            ├── check_mutations.py # mutants on the changed lines must fail a test
            ├── check_diff_hygiene.py  # suppressions, skipped and rewritten tests
            ├── impact_map.py      # dependents, callers, fix rate, risk per changed file
            ├── metrics.py         # rework metrics per task, across repos
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
