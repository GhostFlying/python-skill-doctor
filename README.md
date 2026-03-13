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

If this repository is published, users should be able to install the skill with:

```bash
npx skills add <owner/repo> --skill python-skill-doctor
```
