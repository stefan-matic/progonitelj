"""Trivy integration for vulnerability scanning."""

import json
import shutil
import subprocess
from dataclasses import dataclass


@dataclass
class VulnResult:
    """A vulnerability found by Trivy."""

    vuln_id: str
    package: str
    severity: str
    installed_version: str
    fixed_version: str
    title: str


CVE_SEVERITY_ORDER = {"UNKNOWN": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def check_trivy_installed() -> bool:
    """Check if Trivy is available on the system."""
    return shutil.which("trivy") is not None


def scan_filesystem(path: str, severity: str = "HIGH") -> list[VulnResult]:
    """Scan a filesystem path for vulnerabilities."""
    return _run_trivy(["trivy", "fs", "--format", "json", "--severity", _severity_filter(severity), path])


def scan_image(image: str, severity: str = "HIGH") -> list[VulnResult]:
    """Scan a container image for vulnerabilities."""
    return _run_trivy(["trivy", "image", "--format", "json", "--severity", _severity_filter(severity), image])


def scan_config(path: str) -> list[VulnResult]:
    """Scan configuration files (Dockerfile, K8s manifests, etc.) for misconfigurations."""
    return _run_trivy(["trivy", "config", "--format", "json", path])


def _severity_filter(min_severity: str) -> str:
    """Build severity filter string: include min_severity and above."""
    min_level = CVE_SEVERITY_ORDER.get(min_severity.upper(), 3)
    return ",".join(s for s, level in CVE_SEVERITY_ORDER.items() if level >= min_level)


def _run_trivy(cmd: list[str]) -> list[VulnResult]:
    """Run a Trivy command and parse JSON output."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "Trivy is not installed. Install it: https://aquasecurity.github.io/trivy"
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("Trivy scan timed out after 5 minutes")

    if not result.stdout.strip():
        return []

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    vulns = []
    results = data.get("Results") or []
    for target in results:
        for vuln in target.get("Vulnerabilities") or []:
            vulns.append(VulnResult(
                vuln_id=vuln.get("VulnerabilityID", ""),
                package=vuln.get("PkgName", ""),
                severity=vuln.get("Severity", "UNKNOWN"),
                installed_version=vuln.get("InstalledVersion", ""),
                fixed_version=vuln.get("FixedVersion", ""),
                title=vuln.get("Title", ""),
            ))

    return vulns
