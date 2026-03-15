"""Base validator with shared logic for all ecosystems."""

import fnmatch
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ..policy import EcosystemPolicy, _normalize_name


class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class Dependency:
    """A parsed dependency from a project file."""

    name: str
    version: Optional[str] = None
    source: Optional[str] = None
    line_number: Optional[int] = None
    file_path: Optional[str] = None


@dataclass
class Violation:
    """A policy violation found during validation."""

    package: str
    version: Optional[str]
    reason: str
    severity: Severity
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    suggestion: str = ""


class BaseValidator:
    """Base class for ecosystem-specific validators."""

    ecosystem: str = ""

    def __init__(self, policy: EcosystemPolicy):
        self.policy = policy

    def parse_dependencies(self, path: str) -> list[Dependency]:
        """Parse dependencies from a project file. Override in subclasses."""
        raise NotImplementedError

    def _lookup_key(self, name: str) -> str:
        """Normalize dependency name for policy lookup. Override for ecosystems with special naming."""
        return _normalize_name(name)

    def check_package(self, dep: Dependency) -> list[Violation]:
        """Check a single dependency against the policy."""
        violations = []
        lookup = self._lookup_key(dep.name)
        pkg_policy = self.policy.packages.get(lookup)

        # Package not in policy
        if pkg_policy is None:
            if not self.policy.default_allowed:
                violations.append(Violation(
                    package=dep.name,
                    version=dep.version,
                    reason=f"Package '{dep.name}' is not in the allowed list",
                    severity=Severity.ERROR,
                    file_path=dep.file_path,
                    line_number=dep.line_number,
                    suggestion=f"Submit a package request PR to add '{dep.name}' to the policy",
                ))
            return violations

        # Package explicitly blocked
        if not pkg_policy.allowed:
            violations.append(Violation(
                package=dep.name,
                version=dep.version,
                reason=f"Package '{dep.name}' is explicitly blocked",
                severity=Severity.ERROR,
                file_path=dep.file_path,
                line_number=dep.line_number,
                suggestion=pkg_policy.notes or "Contact security team for alternatives",
            ))
            return violations

        if not dep.version:
            violations.append(Violation(
                package=dep.name,
                version=None,
                reason=f"Package '{dep.name}' has no version pinned",
                severity=Severity.WARNING,
                file_path=dep.file_path,
                line_number=dep.line_number,
                suggestion="Pin to a specific version for reproducible builds",
            ))
            return violations

        # Version too low
        if pkg_policy.min_version:
            if self._version_lt(dep.version, pkg_policy.min_version):
                violations.append(Violation(
                    package=dep.name,
                    version=dep.version,
                    reason=f"Version {dep.version} is below minimum allowed {pkg_policy.min_version}",
                    severity=Severity.ERROR,
                    file_path=dep.file_path,
                    line_number=dep.line_number,
                    suggestion=f"Upgrade to at least {pkg_policy.min_version}",
                ))

        # Version too high
        if pkg_policy.max_version:
            if self._version_gt(dep.version, pkg_policy.max_version):
                violations.append(Violation(
                    package=dep.name,
                    version=dep.version,
                    reason=f"Version {dep.version} exceeds maximum allowed {pkg_policy.max_version}",
                    severity=Severity.ERROR,
                    file_path=dep.file_path,
                    line_number=dep.line_number,
                    suggestion=f"Downgrade to at most {pkg_policy.max_version}",
                ))

        # Not in pinned versions list
        if pkg_policy.pinned_versions:
            if not any(fnmatch.fnmatch(dep.version, p) for p in pkg_policy.pinned_versions):
                violations.append(Violation(
                    package=dep.name,
                    version=dep.version,
                    reason=f"Version {dep.version} is not in the pinned versions: {pkg_policy.pinned_versions}",
                    severity=Severity.ERROR,
                    file_path=dep.file_path,
                    line_number=dep.line_number,
                    suggestion=f"Use one of: {', '.join(pkg_policy.pinned_versions)}",
                ))

        return violations

    def validate(self, path: str) -> list[Violation]:
        """Validate all dependencies in a file against the policy."""
        deps = self.parse_dependencies(path)
        violations = []
        for dep in deps:
            violations.extend(self.check_package(dep))
        return violations

    def _parse_version_parts(self, version: str) -> list[int]:
        """Parse a version string into numeric parts for comparison."""
        clean = version.lstrip("v").split("-")[0].split("+")[0]
        parts = []
        for p in clean.split("."):
            try:
                parts.append(int(p))
            except ValueError:
                break
        return parts

    def _version_lt(self, version: str, minimum: str) -> bool:
        """Check if version < minimum."""
        try:
            from packaging.version import Version
            return Version(version) < Version(minimum)
        except Exception:
            v1, v2 = self._parse_version_parts(version), self._parse_version_parts(minimum)
            return v1 < v2

    def _version_gt(self, version: str, maximum: str) -> bool:
        """Check if version > maximum."""
        try:
            from packaging.version import Version
            return Version(version) > Version(maximum)
        except Exception:
            v1, v2 = self._parse_version_parts(version), self._parse_version_parts(maximum)
            return v1 > v2
