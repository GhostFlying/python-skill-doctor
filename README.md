# python-skill-doctor repository

This repository is arranged for multi-skill-style distribution compatibility:

```text
python-skill-doctor/
└── skills/
    └── python-skill-doctor/
```

## Local development

```bash
cd skills/python-skill-doctor
python3 scripts/quick_validate.py
python3 scripts/run_doctor.py --help
```

## Intended install flow

Users can install the skill with:

```bash
npx skills add GhostFlying/python-skill-doctor --skill python-skill-doctor
```
