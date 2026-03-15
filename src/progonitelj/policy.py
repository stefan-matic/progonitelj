"""Policy loading and data structures."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class PackageConstraint:
    """Version and security constraints for a single package."""

    allowed: bool = True
    min_version: Optional[str] = None
    max_version: Optional[str] = None
    pinned_versions: list[str] = field(default_factory=list)
    max_cve_severity: str = "CRITICAL"
    source: Optional[str] = None
    notes: str = ""


@dataclass
class EcosystemPolicy:
    """Policy definition for an entire ecosystem (docker, python, npm, etc.)."""

    ecosystem: str
    default_allowed: bool = False
    max_cve_severity: str = "CRITICAL"
    allowed_registries: list[str] = field(default_factory=list)
    packages: dict[str, PackageConstraint] = field(default_factory=dict)


def _normalize_name(name: str) -> str:
    """Normalize package name for consistent lookup."""
    return name.lower().replace("-", "_").replace(".", "_")


def load_policy(path: str | Path) -> EcosystemPolicy:
    """Load policy from a YAML file."""
    path = Path(path)
    with open(path) as f:
        data = yaml.safe_load(f)

    if not data:
        raise ValueError(f"Empty policy file: {path}")

    packages: dict[str, PackageConstraint] = {}
    for name, config in data.get("packages", {}).items():
        # Only Python needs name normalization (PEP 503: my-package == my_package)
        # All other ecosystems use exact package names
        ecosystem = data.get("ecosystem", "")
        if ecosystem == "python":
            key = _normalize_name(name)
        else:
            key = name
        if isinstance(config, dict):
            packages[key] = PackageConstraint(
                allowed=config.get("allowed", True),
                min_version=config.get("min_version"),
                max_version=config.get("max_version"),
                pinned_versions=config.get("pinned_versions", []),
                max_cve_severity=config.get("max_cve_severity", data.get("max_cve_severity", "CRITICAL")),
                source=config.get("source"),
                notes=config.get("notes", ""),
            )
        else:
            packages[key] = PackageConstraint(allowed=bool(config))

    return EcosystemPolicy(
        ecosystem=data.get("ecosystem", path.stem),
        default_allowed=data.get("default_allowed", False),
        max_cve_severity=data.get("max_cve_severity", "CRITICAL"),
        allowed_registries=data.get("allowed_registries", []),
        packages=packages,
    )


def load_policies_from_dir(policy_dir: str | Path) -> dict[str, EcosystemPolicy]:
    """Load all policy YAML files from a directory."""
    policy_dir = Path(policy_dir)
    policies = {}
    for path in sorted(policy_dir.glob("*.yaml")):
        try:
            policy = load_policy(path)
            policies[policy.ecosystem] = policy
        except Exception as e:
            raise ValueError(f"Failed to load policy {path}: {e}") from e
    return policies
