# Progonitelj (Прогонитељ) - Supply Chain Gate

**Progonitelj** (Serbian for "the persecutor" / "the one who drives away") is a zero-cost, open-source tool that controls what packages, container images, and tool versions are allowed in your development and CI/CD pipelines.

Define security policies as code. Enforce them everywhere. Drive away unwanted dependencies.

**Izvajbano boga oca samo za PoC - ne koristi u produkciji**

## The Problem

- Developers pull arbitrary packages with unknown CVEs
- No visibility into what versions are used across projects
- Supply chain attacks via compromised or deleted upstream packages
- Inconsistent tooling versions between local dev and CI/CD
- No approval process for new dependencies

## How Progonitelj Solves It

```
Developer writes code
        |
        v
  [pre-commit hook]
        |
  progonitelj validate --strict  <-- checks against policies/*.yaml
        |
   Pass? ──No──> Block commit, show what's wrong
        |
       Yes
        |
   git push
        |
        v
  [CI/CD pipeline]
        |
  progonitelj validate + trivy scan  <-- same policies, same rules
        |
   Pass? ──No──> Block merge
        |
       Yes
        |
   Deploy with confidence
```

## Quick Start

```bash
# Install
pip install -e .

# Initialize policies in your project
progonitelj init

# Edit policies to match your allowed packages
vim policies/python.yaml

# Validate your project
progonitelj validate

# List all allowed packages
progonitelj list-packages

# Scan for vulnerabilities (requires Trivy)
progonitelj scan .
```

## Policy Format

Policies are YAML files in the `policies/` directory. Each ecosystem has its own file:

```yaml
# policies/python.yaml
ecosystem: python
default_allowed: false # deny unlisted packages
max_cve_severity: HIGH # block anything with HIGH+ CVEs

packages:
  requests:
    min_version: "2.31.0" # minimum allowed version
    max_version: "3.0.0" # maximum allowed version (optional)
    notes: "Primary HTTP library"

  numpy:
    min_version: "1.26.0"
    max_cve_severity: "CRITICAL" # per-package CVE threshold

  cryptography:
    min_version: "41.0.0"
    notes: "Frequent CVEs - keep updated"

  insecure-package:
    allowed: false # explicitly blocked
    notes: "Known supply chain compromise"
```

### Docker Image Policies

```yaml
# policies/docker.yaml
ecosystem: docker
default_allowed: false

packages:
  alpine:
    pinned_versions: ["3.19.*", "3.20.*"]

  python:
    pinned_versions: ["3.12-slim", "3.13-slim"]
    notes: "Slim variants only"

  ubuntu:
    allowed: false
    notes: "Use alpine instead"
```

## Supported Ecosystems

| Ecosystem | Files Parsed                         | Policy File            |
| --------- | ------------------------------------ | ---------------------- |
| Docker    | `Dockerfile`                         | `policies/docker.yaml` |
| Python    | `requirements.txt`, `pyproject.toml` | `policies/python.yaml` |
| PHP       | `composer.json`                      | `policies/php.yaml`    |
| npm       | `package.json`                       | `policies/npm.yaml`    |
| Go        | `go.mod`                             | `policies/go.yaml`     |

## CLI Commands

```bash
# Validate all detected dependency files
progonitelj validate

# Validate a specific file
progonitelj validate --file requirements.txt --ecosystem python

# Strict mode: treat warnings as errors
progonitelj validate --strict

# Scan filesystem for CVEs (requires Trivy)
progonitelj scan .

# Scan a Docker image
progonitelj scan --image alpine:3.20

# List allowed packages
progonitelj list-packages
progonitelj list-packages --ecosystem python

# Initialize progonitelj in a new project
progonitelj init
```

## Integration

### Pre-commit Hook

Add to your project's `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: progonitelj-validate
        name: Progonitelj - Validate dependencies
        entry: progonitelj validate --strict
        language: system
        pass_filenames: false
        always_run: true
```

### CI/CD (GitHub Actions)

Copy `.github/workflows/progoni.yml` to your project. It runs:

1. `progonitelj validate --strict` on dependency file changes
2. Trivy vulnerability scanning
3. Docker image scanning (when Dockerfiles change)

### justfile

Common tasks are available via `just`:

```bash
just validate          # Run validation
just validate-strict   # Strict mode
just scan .            # Vulnerability scan
just examples          # Run all examples
just check-tools       # Verify required tools are installed
```

### Tool Version Management (mise)

`.mise.toml` pins tool versions (Python, Node, Go, PHP) so every developer and CI runner uses the same versions:

```bash
mise install    # Install pinned tool versions
mise activate   # Activate in current shell
```

### Vendoring with vendir

`vendir.yml` mirrors critical upstream dependencies locally, protecting against:

- Sudden repository deletions
- Upstream compromises
- Registry outages

```bash
vendir sync    # Download and lock vendored content
```

## Requesting New Packages

When a developer needs a package not in the allowed list:

1. Open an issue using the **Package Request** template
2. Fill in the justification, security review, and checklist
3. Security team reviews and approves/denies
4. If approved, package is added to the relevant policy YAML via PR

## Tool Stack

| Tool                                                              | Purpose                        |
| ----------------------------------------------------------------- | ------------------------------ |
| **Progonitelj**                                                   | Policy engine & CLI            |
| [Trivy](https://github.com/aquasecurity/trivy)                    | CVE scanning                   |
| [mise](https://mise.jdx.dev/)                                     | Tool version management        |
| [vendir](https://carvel.dev/vendir/)                              | Dependency vendoring/mirroring |
| [pre-commit](https://pre-commit.com/)                             | Git hook framework             |
| [just](https://github.com/casey/just)                             | Task runner                    |
| [Renovate](https://github.com/renovatebot/renovate) (self-hosted) | Automated dependency updates   |
| [Forgejo](https://forgejo.org/)                                   | Self-hosted Git (optional)     |

## Example Branches

Each branch demonstrates what happens when dependencies violate the policy. Check them out and run `progonitelj validate` to see the violations in action.

| Branch | Ecosystem | Violations | Command |
| --- | --- | --- | --- |
| [`example/docker-violation`](https://github.com/stefan-matic/progonitelj/tree/example/docker-violation) | Docker | `ubuntu` (blocked), `centos` (blocked), `nginx:latest` (unpinned), `python:3.10` (not in pinned list) | `progonitelj validate -f Dockerfile -e docker` |
| [`example/python-violation`](https://github.com/stefan-matic/progonitelj/tree/example/python-violation) | Python | `flask` 2.0, `requests` 2.20, `cryptography` 40.0, `urllib3` 1.26, `pydantic` 1.10 (all below min), `some-shady-package` (unlisted) | `progonitelj validate -f requirements.txt -e python` |
| [`example/php-violation`](https://github.com/stefan-matic/progonitelj/tree/example/php-violation) | PHP | `laravel` ^9.0, `guzzle` ^6.5, `monolog` ^2.0, `phpunit` ^9.0 (all below min), `some-unknown/vendor-package` (unlisted) | `progonitelj validate -f composer.json -e php` |
| [`example/npm-violation`](https://github.com/stefan-matic/progonitelj/tree/example/npm-violation) | npm | `react` 17, `next` 13, `axios` 0.21, `lodash` 4.17.15, `typescript` 4.9 (all below min), `left-pad` & `event-stream` (unlisted) | `progonitelj validate -f package.json -e npm` |
| [`example/go-violation`](https://github.com/stefan-matic/progonitelj/tree/example/go-violation) | Go | `gin` 1.7, `gorm` 1.20, `zap` 1.20, `jwt` 5.0 (CVE), `x/crypto` 0.10 (all below min), `some-unknown/module` (unlisted) | `progonitelj validate -f go.mod -e go` |

## Development

```bash
# Clone and install
git clone https://github.com/stefan-matic/progonitelj.git
cd progonitelj
pip install -e ".[dev]"

# Run tests
just test

# Lint
just lint

# Run examples
just examples
```

## License

[WTFPL](LICENSE) - Do What The Fuck You Want To Public License
