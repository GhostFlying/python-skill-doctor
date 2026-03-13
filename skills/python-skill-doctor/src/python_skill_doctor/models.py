from __future__ import annotations

from dataclasses import fields, is_dataclass, dataclass, field
from enum import StrEnum
from typing import Any


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FileSource(StrEnum):
    OVERRIDE = "override"
    AUTO = "auto"
    SKILL_MD = "skill_md"
    CONVENTION = "convention"


class CommandResult(StrEnum):
    SUCCESS = "success"
    ISSUES_FOUND = "issues_found"
    PARTIAL_SUCCESS = "partial_success"
    FATAL = "fatal"
    DRY_RUN = "dry_run"
    WRITTEN = "written"


class ActionStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(slots=True)
class Issue:
    code: str
    severity: Severity
    message: str
    field: str | None = None
    suggestion: str | None = None


@dataclass(slots=True)
class ResolvedFile:
    path: str
    source: FileSource
    confidence: Confidence


@dataclass(slots=True)
class EnvVarHint:
    name: str
    source_file: str
    access_pattern: str


@dataclass(slots=True)
class ActionResult:
    code: str
    status: ActionStatus
    message: str
    details: dict[str, Any] | None = None


@dataclass(slots=True)
class SkillRef:
    path: str
    name: str | None = None
    source: str | None = None
    skill_md_path: str | None = None
    meta_path: str | None = None


@dataclass(slots=True)
class DetectionEvidence:
    has_pyproject_toml: bool = False
    has_requirements_txt: bool = False
    has_scripts_requirements_txt: bool = False
    python_files_count: int = 0
    skill_md_mentions_python: bool = False
    skill_md_mentions_pip: bool = False


@dataclass(slots=True)
class VenvState:
    expected_path: str
    exists: bool
    python_path: str | None = None
    pip_path: str | None = None
    manager: str | None = None
    reusable: bool = False


@dataclass(slots=True)
class DocsState:
    skill_md_exists: bool
    has_setup_section: bool = False
    has_activate_section: bool = False
    has_usage_section: bool = False
    mentions_global_pip: bool = False
    mentions_venv: bool = False
    mentions_activate: bool = False
    compliant: bool = False


@dataclass(slots=True)
class SkillInspection:
    skill: SkillRef
    is_python_skill: bool
    detection_evidence: DetectionEvidence
    dependency_file: ResolvedFile | None = None
    entry_script: ResolvedFile | None = None
    venv: VenvState | None = None
    docs: DocsState | None = None
    env_vars: list[EnvVarHint] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)

    def has_errors(self) -> bool:
        return any(issue.severity == Severity.ERROR for issue in self.issues)

    def has_issues(self) -> bool:
        return bool(self.issues)


@dataclass(slots=True)
class CheckResult:
    command: str
    result: CommandResult
    inspection: SkillInspection
    suggested_next_command: str | None = None
    spec_version: str = "v1"


@dataclass(slots=True)
class FixPlan:
    create_venv: bool
    reuse_existing_venv: bool
    install_dependencies: bool
    run_smoke_test: bool
    dependency_file: str | None = None
    entry_script: str | None = None


@dataclass(slots=True)
class FixResult:
    command: str
    result: CommandResult
    inspection: SkillInspection
    plan: FixPlan
    actions: list[ActionResult] = field(default_factory=list)
    remaining_issues: list[Issue] = field(default_factory=list)
    suggested_next_command: str | None = None
    spec_version: str = "v1"


@dataclass(slots=True)
class DocsPatch:
    format: str
    content: str
    target_file: str


@dataclass(slots=True)
class DocsWriteResult:
    status: str
    message: str


@dataclass(slots=True)
class DocsResult:
    command: str
    result: CommandResult
    inspection: SkillInspection
    patch: DocsPatch
    write_result: DocsWriteResult | None = None
    remaining_issues: list[Issue] = field(default_factory=list)
    spec_version: str = "v1"


def to_dict(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if is_dataclass(value):
        return {item.name: to_dict(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, dict):
        return {key: to_dict(val) for key, val in value.items()}
    if isinstance(value, list):
        return [to_dict(item) for item in value]
    return value
