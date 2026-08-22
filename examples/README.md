# Examples

Worked examples that show what the artifacts look like when the workflow is actually running. They are reference material for tone and structure — not product specifications.

## expense-tracker/

The recurring example idea from the README, taken through the early phases:

- `intent.md` — what was asked (Plan)
- `spec.md` — what was decided (Design)
- `plan.md` — how it will be built, before any code (Build)
- `CLAUDE.md` — repository memory for the project
- `workflow-graph.yaml` — the same project's state on the loop graph

To produce the blank forms for your own project:

```bash
python3 skills/ai-native-sdlc/scripts/init_workflow.py my-project --name "My idea"
```
