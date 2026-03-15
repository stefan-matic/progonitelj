"""Progonitelj CLI - Supply chain gate for your dependencies."""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from .policy import load_policies_from_dir, load_policy
from .scanner import check_trivy_installed, scan_filesystem, scan_image
from .validators import DETECT_FILES, VALIDATORS
from .validators.base import Severity

console = Console()


def _find_policy_dir() -> Path:
    """Find policy directory - check .progonitelj.yaml, then default locations."""
    cwd = Path.cwd()

    # Check .progonitelj.yaml config
    config_path = cwd / ".progonitelj.yaml"
    if config_path.exists():
        import yaml
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}
        policy_dir = config.get("policy_dir")
        if policy_dir:
            p = Path(policy_dir)
            if not p.is_absolute():
                p = cwd / p
            if p.is_dir():
                return p

    # Default: ./policies
    default = cwd / "policies"
    if default.is_dir():
        return default

    return default


def _auto_detect_files(directory: str) -> list[tuple[str, str]]:
    """Auto-detect dependency files and their ecosystems."""
    found = []
    d = Path(directory)
    for filename, ecosystem in DETECT_FILES.items():
        path = d / filename
        if path.exists():
            found.append((str(path), ecosystem))
    return found


def _print_violations(violations, file_path=None):
    """Print violations as a rich table."""
    if not violations:
        return

    table = Table(title=f"Policy Violations{f' in {file_path}' if file_path else ''}")
    table.add_column("Severity", style="bold")
    table.add_column("Package")
    table.add_column("Version")
    table.add_column("Reason")
    table.add_column("Suggestion", style="dim")

    for v in violations:
        severity_style = {
            Severity.ERROR: "red",
            Severity.WARNING: "yellow",
            Severity.INFO: "blue",
        }.get(v.severity, "white")

        location = v.package
        if v.line_number:
            location += f" (line {v.line_number})"

        table.add_row(
            f"[{severity_style}]{v.severity.value}[/{severity_style}]",
            location,
            v.version or "-",
            v.reason,
            v.suggestion,
        )

    console.print(table)


@click.group()
@click.version_option(package_name="progonitelj")
def cli():
    """Progonitelj (Прогонитељ) - Supply chain gate for your dependencies.

    Controls what packages, container images, and tools are allowed
    in your projects based on security policies defined as code.
    """


@cli.command()
@click.argument("path", default=".")
@click.option("--policy-dir", "-p", default=None, help="Directory containing policy YAML files")
@click.option("--ecosystem", "-e", default=None, help="Ecosystem to validate (docker, python, php, npm, go)")
@click.option("--file", "-f", default=None, help="Specific dependency file to validate")
@click.option("--strict", is_flag=True, help="Treat warnings as errors")
def validate(path, policy_dir, ecosystem, file, strict):
    """Validate project dependencies against policies.

    Scans dependency files (Dockerfile, requirements.txt, composer.json,
    package.json, go.mod) and checks them against your allowed package policies.
    """
    policy_path = Path(policy_dir) if policy_dir else _find_policy_dir()
    if not policy_path.is_dir():
        console.print(f"[red]Policy directory not found: {policy_path}[/red]")
        console.print("Run 'progonitelj init' to create a starter policy directory, or use --policy-dir")
        sys.exit(1)

    policies = load_policies_from_dir(policy_path)

    if not policies:
        console.print(f"[yellow]No policy files found in {policy_path}[/yellow]")
        sys.exit(1)

    # Determine what to validate
    if file and ecosystem:
        targets = [(file, ecosystem)]
    elif file:
        # Try to detect ecosystem from filename
        fname = Path(file).name
        eco = DETECT_FILES.get(fname)
        if not eco:
            console.print(f"[red]Cannot detect ecosystem for '{fname}'. Use --ecosystem flag.[/red]")
            sys.exit(1)
        targets = [(file, eco)]
    else:
        targets = _auto_detect_files(path)

    if not targets:
        console.print(f"[yellow]No dependency files found in {path}[/yellow]")
        sys.exit(0)

    total_errors = 0
    total_warnings = 0

    for dep_file, eco in targets:
        if eco not in policies:
            console.print(f"[yellow]No policy found for ecosystem '{eco}', skipping {dep_file}[/yellow]")
            continue

        if eco not in VALIDATORS:
            console.print(f"[yellow]No validator for ecosystem '{eco}', skipping {dep_file}[/yellow]")
            continue

        validator_cls = VALIDATORS[eco]
        validator = validator_cls(policies[eco])

        console.print(f"\n[bold]Validating {dep_file} ({eco})[/bold]")

        violations = validator.validate(dep_file)

        if violations:
            _print_violations(violations, dep_file)
            total_errors += sum(1 for v in violations if v.severity == Severity.ERROR)
            total_warnings += sum(1 for v in violations if v.severity == Severity.WARNING)
        else:
            console.print(f"  [green]All dependencies comply with policy[/green]")

    # Summary
    console.print()
    if total_errors > 0:
        console.print(f"[red bold]FAILED: {total_errors} error(s), {total_warnings} warning(s)[/red bold]")
        sys.exit(1)
    elif total_warnings > 0 and strict:
        console.print(f"[yellow bold]FAILED (strict): {total_warnings} warning(s)[/yellow bold]")
        sys.exit(1)
    elif total_warnings > 0:
        console.print(f"[yellow]PASSED with {total_warnings} warning(s)[/yellow]")
    else:
        console.print(f"[green bold]PASSED: all dependencies comply with policy[/green bold]")


@cli.command()
@click.argument("target")
@click.option("--severity", "-s", default="HIGH", help="Minimum CVE severity to report (LOW, MEDIUM, HIGH, CRITICAL)")
@click.option("--image", is_flag=True, help="Scan a container image instead of filesystem")
def scan(target, severity, image):
    """Scan for vulnerabilities using Trivy.

    Scans a directory or container image for known CVEs.
    Requires Trivy to be installed (https://aquasecurity.github.io/trivy).
    """
    if not check_trivy_installed():
        console.print("[red]Trivy is not installed.[/red]")
        console.print("Install: https://aquasecurity.github.io/trivy/latest/getting-started/installation/")
        sys.exit(1)

    console.print(f"[bold]Scanning {'image' if image else 'filesystem'}: {target}[/bold]")
    console.print(f"Minimum severity: {severity.upper()}")

    try:
        if image:
            vulns = scan_image(target, severity)
        else:
            vulns = scan_filesystem(target, severity)
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)

    if not vulns:
        console.print("[green]No vulnerabilities found[/green]")
        return

    table = Table(title=f"Vulnerabilities in {target}")
    table.add_column("ID", style="bold")
    table.add_column("Package")
    table.add_column("Severity")
    table.add_column("Installed")
    table.add_column("Fixed")
    table.add_column("Title", max_width=50)

    for v in vulns:
        sev_style = {"CRITICAL": "red bold", "HIGH": "red", "MEDIUM": "yellow", "LOW": "blue"}.get(
            v.severity, "white"
        )
        table.add_row(
            v.vuln_id,
            v.package,
            f"[{sev_style}]{v.severity}[/{sev_style}]",
            v.installed_version,
            v.fixed_version or "-",
            v.title,
        )

    console.print(table)
    console.print(f"\n[red bold]{len(vulns)} vulnerability(ies) found[/red bold]")
    sys.exit(1)


@cli.command()
@click.argument("path", default=".")
def init(path):
    """Initialize Progonitelj in a project.

    Creates a starter .progonitelj.yaml config and policies/ directory
    with example policy files for all supported ecosystems.
    """
    project_dir = Path(path)
    policy_dir = project_dir / "policies"

    if (project_dir / ".progonitelj.yaml").exists():
        console.print("[yellow].progonitelj.yaml already exists[/yellow]")
        if not click.confirm("Overwrite?"):
            return

    policy_dir.mkdir(exist_ok=True)

    # Write .progonitelj.yaml
    config_content = """\
# Progonitelj configuration
# Docs: https://github.com/your-org/progonitelj

policy_dir: ./policies

# Ecosystems to validate (auto-detected if not specified)
# ecosystems:
#   docker:
#     files: [Dockerfile, docker/Dockerfile.*]
#   python:
#     files: [requirements.txt, requirements/*.txt]
#   php:
#     files: [composer.json]
#   npm:
#     files: [package.json]
#   go:
#     files: [go.mod]

# Trivy scanner settings
trivy:
  severity: HIGH
  ignore_unfixed: true
"""
    (project_dir / ".progonitelj.yaml").write_text(config_content)

    # Write starter policy for each ecosystem
    starters = {
        "docker.yaml": """\
ecosystem: docker
default_allowed: false
max_cve_severity: HIGH

# Allowed container base images
packages:
  alpine:
    min_version: "3.19"
    pinned_versions: ["3.19.*", "3.20.*"]
    notes: "Preferred minimal base image"

  python:
    pinned_versions: ["3.11-slim", "3.12-slim", "3.13-slim"]
    notes: "Use slim variants only"

  node:
    pinned_versions: ["20-slim", "22-slim"]
    notes: "Use slim variants, LTS only"

  nginx:
    pinned_versions: ["1.27-alpine", "1.28-alpine"]
    notes: "Alpine-based nginx only"

  # Example: blocked image
  # ubuntu:
  #   allowed: false
  #   notes: "Use alpine instead for smaller attack surface"
""",
        "python.yaml": """\
ecosystem: python
default_allowed: false
max_cve_severity: HIGH

packages:
  # Web frameworks
  django:
    min_version: "4.2"
    notes: "LTS versions preferred"
  flask:
    min_version: "3.0.0"
  fastapi:
    min_version: "0.100.0"

  # Common libraries
  requests:
    min_version: "2.31.0"
  numpy:
    min_version: "1.26.0"
  pyyaml:
    min_version: "6.0"
  click:
    min_version: "8.1.0"
  rich:
    min_version: "13.0.0"
  packaging:
    min_version: "23.0"

  # Security
  cryptography:
    min_version: "41.0.0"
    notes: "Frequent CVEs - keep updated"

  # Example: blocked package
  # insecure-package:
  #   allowed: false
  #   notes: "Known supply chain compromise - use safe-alternative instead"
""",
        "php.yaml": """\
ecosystem: php
default_allowed: false
max_cve_severity: HIGH

packages:
  laravel/framework:
    min_version: "10.0"
    notes: "LTS versions preferred"
  symfony/symfony:
    min_version: "6.4"
  guzzlehttp/guzzle:
    min_version: "7.5"
  monolog/monolog:
    min_version: "3.0"
  phpunit/phpunit:
    min_version: "10.0"
""",
        "npm.yaml": """\
ecosystem: npm
default_allowed: false
max_cve_severity: HIGH

packages:
  # Frameworks
  react:
    min_version: "18.2.0"
  next:
    min_version: "14.0.0"
  express:
    min_version: "4.18.0"
  vue:
    min_version: "3.3.0"

  # Build tools
  typescript:
    min_version: "5.0.0"
  vite:
    min_version: "5.0.0"
  esbuild:
    min_version: "0.19.0"

  # Testing
  vitest:
    min_version: "1.0.0"
  jest:
    min_version: "29.0.0"

  # Utilities
  axios:
    min_version: "1.6.0"
  lodash:
    min_version: "4.17.21"
    notes: "Pin exact version - prototype pollution history"
  zod:
    min_version: "3.22.0"
""",
        "go.yaml": """\
ecosystem: go
default_allowed: false
max_cve_severity: HIGH

packages:
  # Web frameworks
  github.com/gin-gonic/gin:
    min_version: "1.9.0"
  github.com/labstack/echo/v4:
    min_version: "4.11.0"
  github.com/gofiber/fiber/v2:
    min_version: "2.50.0"

  # Database
  gorm.io/gorm:
    min_version: "1.25.0"
  github.com/jackc/pgx/v5:
    min_version: "5.4.0"

  # Observability
  go.uber.org/zap:
    min_version: "1.26.0"
  github.com/prometheus/client_golang:
    min_version: "1.17.0"

  # Utilities
  github.com/spf13/cobra:
    min_version: "1.7.0"
  github.com/spf13/viper:
    min_version: "1.17.0"
  google.golang.org/grpc:
    min_version: "1.58.0"
""",
    }

    for filename, content in starters.items():
        policy_file = policy_dir / filename
        if not policy_file.exists():
            policy_file.write_text(content)
            console.print(f"  Created {policy_file}")
        else:
            console.print(f"  [yellow]Skipped {policy_file} (already exists)[/yellow]")

    console.print(f"\n[green]Progonitelj initialized in {project_dir.resolve()}[/green]")
    console.print("Next steps:")
    console.print("  1. Edit policies in policies/*.yaml to match your allowed packages")
    console.print("  2. Run: progonitelj validate")
    console.print("  3. Add to CI: see .github/workflows/progoni.yml")


@cli.command()
@click.option("--policy-dir", "-p", default=None, help="Directory containing policy YAML files")
@click.option("--ecosystem", "-e", default=None, help="Filter by ecosystem")
def list_packages(policy_dir, ecosystem):
    """List all allowed packages across policies."""
    policy_path = Path(policy_dir) if policy_dir else _find_policy_dir()
    if not policy_path.is_dir():
        console.print(f"[red]Policy directory not found: {policy_path}[/red]")
        sys.exit(1)

    policies = load_policies_from_dir(policy_path)

    for eco_name, policy in sorted(policies.items()):
        if ecosystem and eco_name != ecosystem:
            continue

        table = Table(title=f"{eco_name.upper()} - Allowed Packages")
        table.add_column("Package")
        table.add_column("Status")
        table.add_column("Min Version")
        table.add_column("Max Version")
        table.add_column("Pinned Versions")
        table.add_column("Notes", style="dim")

        for pkg_name, constraint in sorted(policy.packages.items()):
            status = "[green]ALLOWED[/green]" if constraint.allowed else "[red]BLOCKED[/red]"
            table.add_row(
                pkg_name,
                status,
                constraint.min_version or "-",
                constraint.max_version or "-",
                ", ".join(constraint.pinned_versions) if constraint.pinned_versions else "-",
                constraint.notes,
            )

        console.print(table)
        console.print()


if __name__ == "__main__":
    cli()
