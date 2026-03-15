# Progonitelj - Supply chain gate
# Run `just --list` to see all available recipes

# Default recipe
default:
    @just --list

# Install progonitelj and development dependencies
install:
    pip install -e ".[dev]"

# Validate current project dependencies against policies
validate *ARGS:
    progonitelj validate {{ ARGS }}

# Validate with strict mode (warnings = errors)
validate-strict *ARGS:
    progonitelj validate --strict {{ ARGS }}

# Scan a directory or image for vulnerabilities with Trivy
scan TARGET *ARGS:
    progonitelj scan {{ TARGET }} {{ ARGS }}

# Scan a container image for vulnerabilities
scan-image IMAGE *ARGS:
    progonitelj scan --image {{ IMAGE }} {{ ARGS }}

# List all allowed packages
list-packages *ARGS:
    progonitelj list-packages {{ ARGS }}

# Initialize progonitelj in current project
init:
    progonitelj init

# Run all example validations
examples:
    @echo "=== Docker (good) ==="
    progonitelj validate --file examples/docker/Dockerfile -e docker || true
    @echo ""
    @echo "=== Docker (bad) ==="
    progonitelj validate --file examples/docker/Dockerfile.bad -e docker || true
    @echo ""
    @echo "=== Python (good) ==="
    progonitelj validate --file examples/python-app/requirements.txt -e python || true
    @echo ""
    @echo "=== Python (bad) ==="
    progonitelj validate --file examples/python-app/requirements-bad.txt -e python || true
    @echo ""
    @echo "=== PHP ==="
    progonitelj validate --file examples/php-app/composer.json -e php || true
    @echo ""
    @echo "=== npm ==="
    progonitelj validate --file examples/npm-app/package.json -e npm || true
    @echo ""
    @echo "=== Go ==="
    progonitelj validate --file examples/go-app/go.mod -e go || true

# Run linter
lint:
    ruff check src/
    ruff format --check src/

# Format code
fmt:
    ruff format src/
    ruff check --fix src/

# Run tests
test:
    pytest tests/ -v

# Run pre-commit hooks on all files
pre-commit:
    pre-commit run --all-files

# Check if required tools are installed
check-tools:
    @echo "Checking required tools..."
    @which progonitelj > /dev/null 2>&1 && echo "  progonitelj: OK" || echo "  progonitelj: MISSING (run: just install)"
    @which trivy > /dev/null 2>&1 && echo "  trivy: OK" || echo "  trivy: MISSING (https://aquasecurity.github.io/trivy)"
    @which pre-commit > /dev/null 2>&1 && echo "  pre-commit: OK" || echo "  pre-commit: MISSING (pip install pre-commit)"
    @which vendir > /dev/null 2>&1 && echo "  vendir: OK" || echo "  vendir: MISSING (https://carvel.dev/vendir)"
    @which mise > /dev/null 2>&1 && echo "  mise: OK" || echo "  mise: MISSING (https://mise.jdx.dev)"

# Vendor dependencies using vendir
vendor:
    vendir sync

# CI pipeline: full validation + scan
ci: validate-strict
    @echo "All checks passed"
