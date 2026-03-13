---
name: python-skill-doctor
description: Inspect, bootstrap, and repair Python-based skills that rely on local virtual environments instead of global pip installs. Use this whenever a skill has Python scripts, requirements files, broken setup instructions, missing .venv guidance, or needs its SKILL.md updated to follow local-environment conventions.
---

# Python Skill Doctor

Use this skill to analyze and repair Python-based skills whose setup currently depends on global Python packages or outdated documentation.

## When to use this skill

Use this skill when the user asks to:

- fix a Python-based skill that no longer works in a managed system Python environment
- create or repair a local `.venv` for a skill
- inspect which dependencies / entry scripts a skill uses
- rewrite a skill's `SKILL.md` so it documents local virtualenv setup correctly
- preview what a docs rewrite would change before writing it

Typical targets look like:

- `~/.agents/skills/<skill-name>`
- `~/.aipaas/skills/<skill-name>`
- any local skill directory containing `SKILL.md` and Python scripts

## What this skill provides

This skill bundles a local CLI with three commands:

- `check` — inspect a skill and report problems
- `fix` — create / reuse `.venv`, install dependencies, and smoke test the entry script
- `docs` — preview or write `SKILL.md` changes for local virtualenv usage

## Workflow

1. Start with `check` unless the user already knows they want a docs-only or fix-only operation.
2. Prefer `docs --format patch` before writing docs changes.
3. Use `fix --dry-run` before applying changes that create or mutate `.venv`.
4. When writing documentation, keep generated instructions relative to the skill root. Do not emit machine-specific absolute paths into `SKILL.md`.

## Commands

Run commands from this skill directory.

If this skill is distributed from a multi-skill repository, that usually means:

```bash
cd skills/python-skill-doctor
```

Validate the skill package itself:

```bash
python scripts/quick_validate.py
```

### Check a skill

```bash
python scripts/run_doctor.py check <skill-path>
```

Example:

```bash
python scripts/run_doctor.py check ~/.agents/skills/codebase--codebase --json
```

### Dry-run a fix

```bash
python scripts/run_doctor.py fix <skill-path> --dry-run
```

### Preview docs changes

```bash
python scripts/run_doctor.py docs <skill-path> --format patch
```

### Write docs changes

```bash
python scripts/run_doctor.py docs <skill-path> --write
```

## Output expectations

- `check` returns structured inspection results, including dependency file, entry script, `.venv` state, doc issues, and env-var hints.
- `fix` is conservative: it stops on fatal setup errors instead of guessing.
- `docs` should describe commands relative to the target skill root rather than embedding absolute paths into the target `SKILL.md`.

## Guardrails

- Do not silently rewrite unrelated sections of `SKILL.md`.
- Do not assume the real filesystem path should be written into docs; symlinked skill installs should still produce portable documentation.
- Prefer `uv venv` when `uv` is available; fall back to `python -m venv`.
- If the skill depends on private packages or credentials, report the missing prerequisite instead of pretending the repair succeeded.

## References

- Read `references/skill-packaging.md` for the expected layout of a Python-based skill.
- Use `README.md` for local development details of this bundled CLI.

## Packaging

To package this skill into a `.skill` archive:

```bash
python scripts/package_skill.py
```

If publishing through Vercel's skills CLI, prefer keeping this skill at `skills/python-skill-doctor/` in the repository so users can install it with:

```bash
npx skills add GhostFlying/python-skill-doctor --skill python-skill-doctor
```
