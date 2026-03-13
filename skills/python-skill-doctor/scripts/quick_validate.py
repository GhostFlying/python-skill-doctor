from __future__ import annotations

import sys
from pathlib import Path


REQUIRED_FRONTMATTER_KEYS = {"name", "description"}


def parse_frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        raise ValueError("SKILL.md must start with YAML frontmatter")

    data: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"')
    return data


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    skill_md = root / "SKILL.md"
    scripts_dir = root / "scripts"

    if not skill_md.exists():
        print("ERROR: SKILL.md not found", file=sys.stderr)
        return 1
    if not scripts_dir.exists():
        print("ERROR: scripts/ directory not found", file=sys.stderr)
        return 1

    frontmatter = parse_frontmatter(skill_md.read_text())
    missing = sorted(REQUIRED_FRONTMATTER_KEYS - set(frontmatter))
    if missing:
        print(f"ERROR: missing frontmatter keys: {', '.join(missing)}", file=sys.stderr)
        return 1

    print("Validation OK")
    print(f"name: {frontmatter['name']}")
    print(f"description: {frontmatter['description']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
