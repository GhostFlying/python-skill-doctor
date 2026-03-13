# Python Skill Packaging Notes

This skill follows a lightweight structure inspired by Anthropic's published skills:

```text
repo-root/
└── skills/
    └── python-skill-doctor/
        ├── SKILL.md
        ├── README.md
        ├── scripts/
        │   └── run_doctor.py
        ├── references/
        │   └── skill-packaging.md
        └── src/
            └── python_skill_doctor/
                ├── __init__.py
                ├── __main__.py
                ├── cli.py
                ├── core.py
                └── models.py
```

## Why this shape

- `SKILL.md` is the triggerable skill contract.
- `scripts/` contains runnable entrypoints for deterministic tasks.
- `references/` stores supporting documentation that does not need to live in the main skill prompt body.
- `src/` contains the actual Python implementation of the bundled CLI.

## Invocation model

Use:

```bash
cd skills/python-skill-doctor
python scripts/run_doctor.py <subcommand> <skill-path>
```

This wrapper makes the skill self-contained for local usage because it injects `src/` into `PYTHONPATH` before invoking the CLI.

## Current subcommands

- `check`
- `fix`
- `docs`

## Packaging guidance

If this skill is installed via symlink, the target skills it repairs may resolve to real filesystem paths. That is acceptable for diagnostic output, but generated `SKILL.md` content should remain relative to the repaired skill root.

For Vercel's skills CLI, the recommended repo shape is a multi-skill container with this skill located under `skills/python-skill-doctor/` so users can install it with `npx skills add <repo> --skill python-skill-doctor`.
