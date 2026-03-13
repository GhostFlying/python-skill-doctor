from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .models import (
    ActionResult,
    ActionStatus,
    CheckResult,
    CommandResult,
    Confidence,
    DetectionEvidence,
    DocsPatch,
    DocsResult,
    DocsState,
    DocsWriteResult,
    EnvVarHint,
    FileSource,
    FixPlan,
    FixResult,
    Issue,
    ResolvedFile,
    Severity,
    SkillInspection,
    SkillRef,
    VenvState,
)


ENV_VAR_PATTERNS = [
    re.compile(r"os\.getenv\(\s*[\"']([A-Z0-9_]+)[\"']"),
    re.compile(r"os\.environ\.get\(\s*[\"']([A-Z0-9_]+)[\"']"),
    re.compile(r"os\.environ\[\s*[\"']([A-Z0-9_]+)[\"']\s*\]"),
]


def load_meta(path: Path) -> dict:
    meta_path = path / "skill-meta.json"
    if not meta_path.exists():
        return {}
    try:
        return json.loads(meta_path.read_text())
    except json.JSONDecodeError:
        return {}


def load_skill_name(skill_md_path: Path) -> str | None:
    if not skill_md_path.exists():
        return None
    text = skill_md_path.read_text()
    match = re.search(r"^name:\s*(.+)$", text, re.MULTILINE)
    if match:
        return match.group(1).strip().strip('"')
    return None


def detect_python_mentions(text: str) -> tuple[bool, bool]:
    lower = text.lower()
    return ("python " in lower or "python3 " in lower, "pip install" in lower)


def detect_sections(text: str) -> DocsState:
    lower = text.lower()
    has_setup = "## setup" in lower or "### setup" in lower
    has_activate = "## activate" in lower or "### activate" in lower
    has_usage = "## usage" in lower or "### usage" in lower or "### commands" in lower
    mentions_global_pip = "pip install" in lower and ".venv" not in lower
    mentions_venv = ".venv" in text
    mentions_activate = "source " in lower and "activate" in lower
    compliant = (
        has_setup
        and has_activate
        and (mentions_venv or mentions_activate)
        and not mentions_global_pip
    )
    return DocsState(
        skill_md_exists=True,
        has_setup_section=has_setup,
        has_activate_section=has_activate,
        has_usage_section=has_usage,
        mentions_global_pip=mentions_global_pip,
        mentions_venv=mentions_venv,
        mentions_activate=mentions_activate,
        compliant=compliant,
    )


def parse_python_command(text: str) -> str | None:
    match = re.search(
        r"(?:^|\n)```bash\n(?:.*\n)*?(?:python|python3)\s+([^\s\\]+\.py)", text
    )
    if match:
        return match.group(1)
    match = re.search(r"(?:python|python3)\s+([^\s]+\.py)", text)
    return match.group(1) if match else None


def scan_env_vars(files: list[Path], root: Path) -> list[EnvVarHint]:
    seen: set[tuple[str, str]] = set()
    hints: list[EnvVarHint] = []
    for file in files:
        try:
            text = file.read_text()
        except Exception:
            continue
        for pattern in ENV_VAR_PATTERNS:
            for match in pattern.finditer(text):
                key = (match.group(1), file.as_posix())
                if key in seen:
                    continue
                seen.add(key)
                hints.append(
                    EnvVarHint(
                        name=match.group(1),
                        source_file=str(file.relative_to(root)),
                        access_pattern=pattern.pattern.split("\\(")[0],
                    )
                )
    return hints


def inspect_skill(
    skill_path: str, deps_override: str | None = None, entry_override: str | None = None
) -> SkillInspection:
    root = Path(skill_path).expanduser().resolve()
    skill_md = root / "SKILL.md"
    meta_path = root / "skill-meta.json"
    meta = load_meta(root)
    skill_name = load_skill_name(skill_md) or meta.get("name")

    issues: list[Issue] = []
    if not root.exists():
        return SkillInspection(
            skill=SkillRef(path=str(root), name=skill_name),
            is_python_skill=False,
            detection_evidence=DetectionEvidence(),
            issues=[
                Issue(
                    code="path_not_found",
                    severity=Severity.ERROR,
                    message="Skill path does not exist",
                    field="path",
                )
            ],
        )
    if not root.is_dir():
        return SkillInspection(
            skill=SkillRef(path=str(root), name=skill_name),
            is_python_skill=False,
            detection_evidence=DetectionEvidence(),
            issues=[
                Issue(
                    code="invalid_skill_path",
                    severity=Severity.ERROR,
                    message="Skill path is not a directory",
                    field="path",
                )
            ],
        )

    skill_text = skill_md.read_text() if skill_md.exists() else ""
    mentions_python, mentions_pip = detect_python_mentions(skill_text)
    py_files = list(root.rglob("*.py"))
    evidence = DetectionEvidence(
        has_pyproject_toml=(root / "pyproject.toml").exists(),
        has_requirements_txt=(root / "requirements.txt").exists(),
        has_scripts_requirements_txt=(root / "scripts" / "requirements.txt").exists(),
        python_files_count=len(py_files),
        skill_md_mentions_python=mentions_python,
        skill_md_mentions_pip=mentions_pip,
    )
    is_python_skill = any(
        [
            evidence.has_pyproject_toml,
            evidence.has_requirements_txt,
            evidence.has_scripts_requirements_txt,
            evidence.python_files_count > 0 and (mentions_python or mentions_pip),
        ]
    )
    if not skill_md.exists():
        issues.append(
            Issue(
                code="skill_md_missing",
                severity=Severity.WARNING,
                message="SKILL.md not found",
                field="docs",
            )
        )
    if not is_python_skill:
        issues.append(
            Issue(
                code="not_python_skill",
                severity=Severity.ERROR,
                message="Could not classify directory as a Python skill",
                field="classification",
            )
        )

    dependency_file = None
    if deps_override:
        deps_path = (
            (root / deps_override).resolve()
            if not Path(deps_override).is_absolute()
            else Path(deps_override)
        )
        if deps_path.exists():
            dependency_file = ResolvedFile(
                path=str(deps_path.relative_to(root)),
                source=FileSource.OVERRIDE,
                confidence=Confidence.HIGH,
            )
        else:
            issues.append(
                Issue(
                    code="deps_override_not_found",
                    severity=Severity.ERROR,
                    message="Dependency override file not found",
                    field="dependencies",
                )
            )
    else:
        for candidate in [
            root / "pyproject.toml",
            root / "requirements.txt",
            root / "scripts" / "requirements.txt",
        ]:
            if candidate.exists():
                dependency_file = ResolvedFile(
                    path=str(candidate.relative_to(root)),
                    source=FileSource.AUTO,
                    confidence=Confidence.HIGH,
                )
                break
    if dependency_file is None and is_python_skill:
        issues.append(
            Issue(
                code="dependency_file_missing",
                severity=Severity.ERROR,
                message="No dependency file found",
                field="dependencies",
            )
        )

    entry_script = None
    if entry_override:
        entry_path = (
            (root / entry_override).resolve()
            if not Path(entry_override).is_absolute()
            else Path(entry_override)
        )
        if entry_path.exists():
            entry_script = ResolvedFile(
                path=str(entry_path.relative_to(root)),
                source=FileSource.OVERRIDE,
                confidence=Confidence.HIGH,
            )
        else:
            issues.append(
                Issue(
                    code="entry_override_not_found",
                    severity=Severity.ERROR,
                    message="Entry override file not found",
                    field="entry_script",
                )
            )
    else:
        parsed = parse_python_command(skill_text) if skill_text else None
        if parsed and (root / parsed).exists():
            entry_script = ResolvedFile(
                path=parsed, source=FileSource.SKILL_MD, confidence=Confidence.HIGH
            )
        else:
            candidates = sorted(root.glob("scripts/*.py"))
            preferred = [
                c
                for c in candidates
                if any(token in c.name for token in ("cli", "client", "main"))
            ]
            selected = (
                preferred[0] if preferred else (candidates[0] if candidates else None)
            )
            if selected:
                confidence = (
                    Confidence.MEDIUM
                    if len(candidates) > 1 and not preferred
                    else Confidence.HIGH
                )
                entry_script = ResolvedFile(
                    path=str(selected.relative_to(root)),
                    source=FileSource.CONVENTION,
                    confidence=confidence,
                )
                if len(candidates) > 1 and not preferred:
                    issues.append(
                        Issue(
                            code="ambiguous_entry_script",
                            severity=Severity.WARNING,
                            message="Multiple candidate entry scripts found; selected the first one",
                            field="entry_script",
                        )
                    )
    if entry_script is None and is_python_skill:
        issues.append(
            Issue(
                code="entry_script_not_found",
                severity=Severity.WARNING,
                message="No entry script found",
                field="entry_script",
            )
        )

    docs = (
        detect_sections(skill_text)
        if skill_md.exists()
        else DocsState(skill_md_exists=False)
    )
    if docs.skill_md_exists:
        if docs.mentions_global_pip:
            issues.append(
                Issue(
                    code="docs_global_pip",
                    severity=Severity.WARNING,
                    message="SKILL.md suggests global pip install",
                    field="docs",
                )
            )
        if not docs.has_activate_section or not docs.mentions_activate:
            issues.append(
                Issue(
                    code="docs_missing_activate_section",
                    severity=Severity.WARNING,
                    message="SKILL.md is missing virtualenv activation guidance",
                    field="docs",
                )
            )
        if not docs.has_setup_section:
            issues.append(
                Issue(
                    code="docs_missing_setup_section",
                    severity=Severity.WARNING,
                    message="SKILL.md is missing a setup section",
                    field="docs",
                )
            )

    venv_root = root / ".venv"
    venv_python = venv_root / "bin" / "python"
    venv_pip = venv_root / "bin" / "pip"
    venv = VenvState(
        expected_path=str(venv_root.relative_to(root)),
        exists=venv_root.exists(),
        python_path=str(venv_python.relative_to(root))
        if venv_python.exists()
        else None,
        pip_path=str(venv_pip.relative_to(root)) if venv_pip.exists() else None,
        manager="uv"
        if venv_root.exists() and (venv_root / "pyvenv.cfg").exists()
        else None,
        reusable=venv_python.exists() and venv_pip.exists(),
    )
    if not venv.exists and is_python_skill:
        issues.append(
            Issue(
                code="missing_venv",
                severity=Severity.WARNING,
                message="No local virtual environment found",
                field="venv",
            )
        )

    env_scan_files = []
    if entry_script:
        env_scan_files.append(root / entry_script.path)
    env_vars = scan_env_vars(env_scan_files or py_files[:5], root)
    if env_vars:
        issues.append(
            Issue(
                code="env_vars_detected",
                severity=Severity.INFO,
                message="Potential runtime environment variables detected",
                field="env",
            )
        )

    return SkillInspection(
        skill=SkillRef(
            path=str(root),
            name=skill_name,
            source=meta.get("source"),
            skill_md_path=str(skill_md) if skill_md.exists() else None,
            meta_path=str(meta_path) if meta_path.exists() else None,
        ),
        is_python_skill=is_python_skill,
        detection_evidence=evidence,
        dependency_file=dependency_file,
        entry_script=entry_script,
        venv=venv,
        docs=docs,
        env_vars=env_vars,
        issues=issues,
    )


def build_check_result(inspection: SkillInspection) -> CheckResult:
    if inspection.has_errors() or not inspection.is_python_skill:
        result = CommandResult.FATAL
    elif inspection.has_issues():
        result = CommandResult.ISSUES_FOUND
    else:
        result = CommandResult.SUCCESS
    next_command = None
    if inspection.is_python_skill:
        if any(issue.code == "missing_venv" for issue in inspection.issues):
            next_command = f"python-skill-doctor fix {inspection.skill.path}"
        elif any(issue.code.startswith("docs_") for issue in inspection.issues):
            next_command = f"python-skill-doctor docs {inspection.skill.path}"
    return CheckResult(
        command="check",
        result=result,
        inspection=inspection,
        suggested_next_command=next_command,
    )


def _run(command: list[str], cwd: Path) -> tuple[int, str, str]:
    proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def create_fix_plan(
    inspection: SkillInspection, skip_install: bool, skip_smoke: bool
) -> FixPlan:
    return FixPlan(
        create_venv=not bool(inspection.venv and inspection.venv.exists),
        reuse_existing_venv=bool(inspection.venv and inspection.venv.exists),
        install_dependencies=not skip_install,
        run_smoke_test=not skip_smoke,
        dependency_file=inspection.dependency_file.path
        if inspection.dependency_file
        else None,
        entry_script=inspection.entry_script.path if inspection.entry_script else None,
    )


def fix_skill(
    inspection: SkillInspection,
    dry_run: bool = False,
    skip_install: bool = False,
    skip_smoke: bool = False,
    force_uv: bool = False,
    force_pip: bool = False,
    recreate_venv: bool = False,
) -> FixResult:
    plan = create_fix_plan(inspection, skip_install=skip_install, skip_smoke=skip_smoke)
    if dry_run:
        return FixResult(
            command="fix",
            result=CommandResult.DRY_RUN,
            inspection=inspection,
            plan=plan,
            remaining_issues=list(inspection.issues),
        )
    if (
        inspection.has_errors()
        or not inspection.is_python_skill
        or inspection.dependency_file is None
        or inspection.venv is None
    ):
        return FixResult(
            command="fix",
            result=CommandResult.FATAL,
            inspection=inspection,
            plan=plan,
            remaining_issues=list(inspection.issues),
        )

    root = Path(inspection.skill.path)
    venv_path = root / inspection.venv.expected_path
    actions: list[ActionResult] = []
    remaining_issues = [
        issue for issue in inspection.issues if issue.code not in {"missing_venv"}
    ]

    if recreate_venv and venv_path.exists():
        shutil.rmtree(venv_path)

    if not venv_path.exists():
        if force_pip:
            create_cmd = [sys.executable, "-m", "venv", str(venv_path)]
            manager = "venv"
        else:
            uv_bin = shutil.which("uv")
            if uv_bin and not force_pip:
                create_cmd = [uv_bin, "venv", str(venv_path)]
                manager = "uv"
            else:
                create_cmd = [sys.executable, "-m", "venv", str(venv_path)]
                manager = "venv"
        code, _, err = _run(create_cmd, root)
        if code != 0:
            actions.append(
                ActionResult(
                    code="create_venv",
                    status=ActionStatus.FAILED,
                    message="Failed to create .venv",
                    details={"stderr": err.strip()},
                )
            )
            remaining_issues.append(
                Issue(
                    code="venv_create_failed",
                    severity=Severity.ERROR,
                    message="Failed to create local virtual environment",
                    field="venv",
                )
            )
            return FixResult(
                command="fix",
                result=CommandResult.FATAL,
                inspection=inspection,
                plan=plan,
                actions=actions,
                remaining_issues=remaining_issues,
            )
        actions.append(
            ActionResult(
                code="create_venv",
                status=ActionStatus.SUCCESS,
                message=f"Created .venv using {manager}",
                details={"manager": manager},
            )
        )
    else:
        actions.append(
            ActionResult(
                code="reuse_venv",
                status=ActionStatus.SUCCESS,
                message="Reusing existing .venv",
            )
        )

    python_bin = venv_path / "bin" / "python"
    pip_bin = venv_path / "bin" / "pip"
    if not skip_install:
        dep_path = root / inspection.dependency_file.path
        if dep_path.name == "pyproject.toml":
            install_cmd = [str(pip_bin), "install", "."]
        else:
            install_cmd = [str(pip_bin), "install", "-r", str(dep_path)]
        code, out, err = _run(install_cmd, root)
        if code != 0:
            actions.append(
                ActionResult(
                    code="install_dependencies",
                    status=ActionStatus.FAILED,
                    message="Failed to install dependencies",
                    details={"stdout": out.strip(), "stderr": err.strip()},
                )
            )
            remaining_issues.append(
                Issue(
                    code="dependency_install_failed",
                    severity=Severity.ERROR,
                    message="Failed to install dependencies",
                    field="dependencies",
                )
            )
            return FixResult(
                command="fix",
                result=CommandResult.PARTIAL_SUCCESS,
                inspection=inspection,
                plan=plan,
                actions=actions,
                remaining_issues=remaining_issues,
            )
        actions.append(
            ActionResult(
                code="install_dependencies",
                status=ActionStatus.SUCCESS,
                message=f"Installed dependencies from {inspection.dependency_file.path}",
            )
        )

    if not skip_smoke:
        if inspection.entry_script is None:
            actions.append(
                ActionResult(
                    code="smoke_test",
                    status=ActionStatus.SKIPPED,
                    message="Skipped smoke test because no entry script was found",
                )
            )
            remaining_issues.append(
                Issue(
                    code="smoke_test_skipped_no_entry",
                    severity=Severity.WARNING,
                    message="Smoke test skipped because no entry script was found",
                    field="entry_script",
                )
            )
        else:
            entry_path = root / inspection.entry_script.path
            code, out, err = _run([str(python_bin), str(entry_path), "--help"], root)
            if code != 0:
                actions.append(
                    ActionResult(
                        code="smoke_test",
                        status=ActionStatus.FAILED,
                        message="Smoke test failed",
                        details={"stdout": out.strip(), "stderr": err.strip()},
                    )
                )
                remaining_issues.append(
                    Issue(
                        code="smoke_test_failed",
                        severity=Severity.ERROR,
                        message="Smoke test failed",
                        field="entry_script",
                    )
                )
                return FixResult(
                    command="fix",
                    result=CommandResult.PARTIAL_SUCCESS,
                    inspection=inspection,
                    plan=plan,
                    actions=actions,
                    remaining_issues=remaining_issues,
                )
            actions.append(
                ActionResult(
                    code="smoke_test",
                    status=ActionStatus.SUCCESS,
                    message=f"Smoke test passed for {inspection.entry_script.path}",
                )
            )

    result = (
        CommandResult.SUCCESS
        if not any(issue.severity == Severity.ERROR for issue in remaining_issues)
        else CommandResult.PARTIAL_SUCCESS
    )
    next_command = (
        f"python-skill-doctor docs {inspection.skill.path}"
        if any(issue.code.startswith("docs_") for issue in remaining_issues)
        else None
    )
    return FixResult(
        command="fix",
        result=result,
        inspection=inspect_skill(inspection.skill.path),
        plan=plan,
        actions=actions,
        remaining_issues=remaining_issues,
        suggested_next_command=next_command,
    )


def build_docs_patch(inspection: SkillInspection, fmt: str = "patch") -> DocsPatch:
    target = inspection.skill.skill_md_path or str(
        Path(inspection.skill.path) / "SKILL.md"
    )
    dep = (
        inspection.dependency_file.path
        if inspection.dependency_file
        else "requirements.txt"
    )
    entry = (
        inspection.entry_script.path if inspection.entry_script else "scripts/main.py"
    )
    full = f"""### Setup\n\nThis skill uses its own Python virtual environment.\n\nRun these commands from the skill root (the directory containing `SKILL.md`):\n\n```bash\nuv venv .venv\n.venv/bin/pip install -r {dep}\n```\n\n### Activate\n\nBefore using the commands below, activate the virtual environment from the skill root:\n\n```bash\nsource .venv/bin/activate\n```\n\n### Usage\n\nFrom the skill root:\n\n```bash\npython {entry} --help\n```\n"""
    if fmt == "full":
        content = full
    elif fmt == "text":
        content = f"Suggested Setup/Activate/Usage sections:\n\n{full}"
    else:
        content = f"--- SKILL.md\n+++ SKILL.md\n@@\n+{full.replace(chr(10), chr(10) + '+').rstrip('+')}"
    return DocsPatch(format=fmt, content=content, target_file=target)


def write_docs(inspection: SkillInspection) -> DocsWriteResult:
    skill_md_path = Path(
        inspection.skill.skill_md_path or Path(inspection.skill.path) / "SKILL.md"
    )
    existing = skill_md_path.read_text() if skill_md_path.exists() else ""
    patch = build_docs_patch(inspection, fmt="full").content
    if "### Setup" in existing:
        updated = re.sub(
            r"### Setup[\s\S]*?(?=\n## |\n### |\Z)",
            patch.strip() + "\n\n",
            existing,
            count=1,
        )
        if updated == existing:
            updated = patch + "\n\n" + existing
    else:
        updated = (existing.rstrip() + "\n\n" + patch).strip() + "\n"
    skill_md_path.write_text(updated)
    return DocsWriteResult(
        status="written", message="Updated SKILL.md with local venv guidance"
    )


def docs_skill(
    inspection: SkillInspection, fmt: str = "patch", write: bool = False
) -> DocsResult:
    patch = build_docs_patch(inspection, fmt=fmt)
    write_result = (
        write_docs(inspection)
        if write
        else DocsWriteResult(
            status="not_written", message="Run with --write to update SKILL.md"
        )
    )
    if inspection.has_errors() and not (
        len(inspection.issues) == 1 and inspection.issues[0].code == "skill_md_missing"
    ):
        result = CommandResult.FATAL
    elif write:
        result = CommandResult.WRITTEN
    elif inspection.has_issues():
        result = CommandResult.ISSUES_FOUND
    else:
        result = CommandResult.SUCCESS
    return DocsResult(
        command="docs",
        result=result,
        inspection=inspection,
        patch=patch,
        write_result=write_result,
    )
