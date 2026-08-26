# Incident INC-<n> — <short summary>

- Opened: <date> by <who, or which control band / trigger>
- Source: <band breach | channel | ticket | schedule>
- Severity: <sev-1 | sev-2 | sev-3> (definitions at the bottom)
- Status: <triaging | diagnosing | fix-in-review | resolved | dismissed>

## What happened

<Observed behavior and evidence: the metric, the sigma level, the band that
tripped; what the agent or alert detected. Cite numbers, not impressions.>

## Timeline

| Time (UTC) | Event |
|---|---|
|  |  |
|  |  |

## Diagnosis

<Root cause with file/line evidence where relevant; what was ruled out.>

## Resolution

<Fix, rollback, or runbook executed; verification; who approved the action and
via which gate (release authorization, PR merge, runbook trigger).>

## Control band

<Which band breached, the sigma level, and whether bands.yaml needs retuning
(dismissals tune the bands and reduce noise).>

## Eval

- [ ] An eval covering this incident class was added (`evals/<name>.json`)
- [ ] Larger than a small bounded fix -> the diagnosis was written back as
      `intent/intent.md` and re-entered the pipeline at Plan

## Severity definitions

- **sev-1** — production down or data loss; immediate response; rollback or hotfix
- **sev-2** — degraded but usable; fix within the working day
- **sev-3** — cosmetic or low-impact; scheduled fix
