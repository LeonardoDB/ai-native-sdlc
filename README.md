# AI-Native SDLC — reusable workflow repo

A ready-to-inherit implementation of Anthropic's [AI-Native SDLC playbook](https://claude.com/blog/the-ai-native-sdlc-playbook): give your coding agent a goal or idea, and it scaffolds and drives the project through the full lifecycle — planning, design, build, test, deploy, and maintain — with human approval gates at every handoff.

This repo is three things at once:

- A **Codex skill** at `skills/ai-native-sdlc/`, installable into `~/.codex/skills`.
- A **Claude Code skill** — the same folder, installable into `~/.claude/skills`.
- A **Codex plugin** (`.codex-plugin/plugin.json` at the repo root) that bundles the skill, so teams can publish or fork it as their workflow baseline.

## The workflow

```
Plan → Design → Build → Test → Deploy → Maintain
  ↑                                              │
  └────────────────── back to Plan ←─────────────┘
```

Each phase ends by committing a versioned artifact; the next phase starts by reading it:

| Phase | Artifact | Human gate |
|---|---|---|
| Plan | `intent.md` | accepted → Design |
| Design | `spec.md` | approved → Build |
| Build | `plan.md` → code + tests → PR | plan approved before code; PR merged → Deploy |
| Test | eval results, regression evals | config changes that drop pass rate are reviewed |
| Deploy | authorized release | agentic review + explicit release authorization |
| Maintain | diagnosis → new `intent.md` | on-call triage, then back to Plan |

The agent does the generation, verification, and mechanical work. Humans keep the judgment calls: the agent goes all the way to the production gate and never crosses it.

**Framework mapping.** The skill is framework-neutral: Claude Code calls repository memory CLAUDE.md and keeps skills in `.claude/skills/`; Codex calls it AGENTS.md and installs skills into `~/.codex/skills/`. The templates, artifacts, and scaffold script are the same either way.

## Install

### As a Codex skill

```bash
mkdir -p ~/.codex/skills
cp -R skills/ai-native-sdlc ~/.codex/skills/
```

### As a Claude Code skill

```bash
mkdir -p ~/.claude/skills
cp -R skills/ai-native-sdlc ~/.claude/skills/
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

For a team, publish the repo and point a marketplace at it instead.

### Or inherit the repo directly

Fork it, keep the skill and templates, and drop in your organization's standards. The repo models the workflow it ships, so agents working inside it (via the root `AGENTS.md`) follow the same conventions.

## Use it

Start a new project:

```bash
python3 skills/ai-native-sdlc/scripts/init_workflow.py my-project --name "My idea"
```

Then tell your agent:

> $ai-native-sdlc: I want to build an expense tracker. Start with the intent.

The agent interviews you until the idea is concrete, writes `intent/intent.md`, commits it, and asks you to accept. From there it moves through spec → plan → build → test → deploy, stopping at each approval gate, and finally wires up monitoring so the loop can close back into new intents.

Already have a project? Copy the templates into it:

```bash
cp skills/ai-native-sdlc/assets/{intent.md,spec.md,plan.md,CLAUDE.md,REVIEW.md,bands.yaml} .
cp skills/ai-native-sdlc/assets/production-gate.sh hooks/
```

## Customizing for your organization

- **Standards as skills** — encode brand, security, UX, and compliance policies as skills so Design and Build apply them consistently.
- **Hooks as red lines** — protected paths, secrets, and the release gate go in deterministic hooks, not prose. `production-gate.sh` blocks deploys without human authorization; `hook-settings.example.json` shows the wiring; `managed-settings.example.json` is the regulated-enterprise starting point.
- **Evals** — collect 20–50 real tasks with expected outcomes; run them in CI on every config change and after every incident (`agent-evals.yml.example`).
- **Review culture** — `REVIEW.md` sets the passes (bugs, security, compliance), the evidence requirement, and the 5-nit cap.
- **CI/CD and autonomy tiers** — agent triage runs non-interactively in the pipeline; dev is open, production needs a release manager; rollbacks are rehearsed.
- **Monitoring** — `bands.yaml` defines the control bands; 1σ logs, 2σ diagnoses, 3σ proposes a fix or runbook and writes the diagnosis back as a new intent.

See `skills/ai-native-sdlc/references/adoption.md` for the staged rollout order.

## Layout

```text
.
├── .codex-plugin/plugin.json      # Codex plugin manifest (repo root is the plugin)
├── AGENTS.md                      # guidance for agents working in this repo
├── README.md
├── LICENSE
└── skills/
    └── ai-native-sdlc/
        ├── SKILL.md               # skill entrypoint
        ├── agents/openai.yaml     # UI metadata
        ├── references/
        │   ├── playbook.md        # phase-by-phase procedures
        │   └── adoption.md        # staged rollout + org customization
        ├── assets/                # templates copied into target projects
        │   ├── intent.md
        │   ├── spec.md
        │   ├── plan.md
        │   ├── CLAUDE.md
        │   ├── REVIEW.md
        │   ├── bands.yaml
        │   ├── production-gate.sh
        │   ├── evals.example.md
        │   ├── hook-settings.example.json
        │   ├── agent-evals.yml.example
        │   └── managed-settings.example.json
        └── scripts/
            └── init_workflow.py   # scaffolds the artifact skeleton
```

## Attribution and license

Based on [The AI-Native SDLC playbook](https://claude.com/blog/the-ai-native-sdlc-playbook) by Anthropic's Applied AI team (2026). MIT licensed — see `LICENSE`.
