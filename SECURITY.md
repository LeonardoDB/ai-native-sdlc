# Security

This repository ships **guardrails** — the release gate hook, hooks, and
managed-settings examples are the enforcement layer other teams deploy. Bugs
in them matter more than bugs in ordinary code.

## Reporting a vulnerability

Please report gate-bypass issues, hook failures, and managed-settings
weaknesses privately before opening a public issue:

- Open a private advisory via GitHub's security tab, **or**
- Email the maintainers (see the repository metadata / plugin author) with the
  subject `[ai-native-sdlc security]`.

Include: the affected file and version, a reproduction, and the impact. Do
not include real credentials or production data.

## What we consider security-relevant

- Bypasses of `assets/production-gate.sh` or any gate hook (a deploy that
  should have required authorization, or an approval that survives its expiry).
- Weaknesses in `assets/managed-settings.example.json` or
  `assets/hook-settings.example.json` that weaken the sandbox or permission
  defaults.
- Script injection in `scripts/init_workflow.py` (`--name` interpolation),
  `scripts/run_evals.py`, or `scripts/detect_bands.py`.

## Non-goals (out of scope)

- Vulnerabilities in third-party tools the templates merely *reference*.
- Misconfiguration by adopters who weaken the defaults on purpose.
