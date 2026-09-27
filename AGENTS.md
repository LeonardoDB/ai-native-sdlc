# AGENTS.md

This repo is a reusable skill and plugin bundle implementing the AI-native SDLC workflow. Follow these conventions when working in it.

## Source of truth

- The workflow lives in `skills/ai-native-sdlc/SKILL.md`. Read it first, then the references it routes to (`references/playbook.md`, `references/adoption.md`).
- Templates in `skills/ai-native-sdlc/assets/` are copied into target projects — never edited to fit one project.
- `skills/ai-native-sdlc/scripts/init_workflow.py` performs that copy; change the script when the scaffold layout changes.
- `references/trackers.md` holds the task-link flow and its delivery defaults; `scripts/tracker_link.py` and `scripts/check_plan_sync.py` are its deterministic parts.

## Validation

After changing the skill or plugin, run the self-check suite (from the repo root):

```bash
python3 skills/ai-native-sdlc/scripts/quick_validate.py skills/ai-native-sdlc
bash tests/test_init.sh
python3 -m unittest discover -s tests -v
```

All must pass before finishing; CI runs the same checks
(`.github/workflows/self-check.yml`). Keep `plugin.json` and `SKILL.md`
consistent in name, description, and version — `quick_validate.py` enforces
this.

## Conventions

- Keep `SKILL.md` short; put phase detail in references.
- Keep artifacts (intent/spec/plan templates) generic; org specifics belong in the adopter's own skills and hooks.
- Never add hooks or secrets for a specific adopter into the shared templates.
- Commit with the repo-local git identity (`bashebr <43511789+bashebr@users.noreply.github.com>`); never fall back to the global git identity.
