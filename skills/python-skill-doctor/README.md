# python-skill-doctor

Minimal CLI to inspect and repair Python-based skills that should use a local `.venv` instead of global package installation.

This skill is packaged in a multi-skill-friendly repository layout:

```text
python-skill-doctor/
└── skills/
    └── python-skill-doctor/
```

## Run locally

```bash
cd skills/python-skill-doctor
PYTHONPATH=src python3 -m python_skill_doctor --help
```

## Commands

```bash
python -m python_skill_doctor.cli check <skill-path>
python -m python_skill_doctor.cli fix <skill-path>
python -m python_skill_doctor.cli docs <skill-path>
```

## Examples

```bash
python scripts/run_doctor.py check ~/.agents/skills/codebase--codebase
python scripts/run_doctor.py fix ~/.agents/skills/codebase--codebase --dry-run
python scripts/run_doctor.py docs ~/.agents/skills/codebase--codebase --format patch
```

## Notes

- Prefers `uv venv` when `uv` is installed.
- Falls back to `python -m venv` otherwise.
- Uses only the Python standard library.

## Exit codes

- `0`: success
- `1`: fatal validation/runtime error
- `2`: issues found or partial success

## Installing with Vercel skills CLI

From a published repo containing this layout, users can install with:

```bash
npx skills add <owner/repo> --skill python-skill-doctor
```
