"""Ecosystem validators for Progonitelj."""

from .docker import DockerValidator
from .python import PythonValidator
from .php import PHPValidator
from .npm import NpmValidator
from .golang import GoValidator

VALIDATORS = {
    "docker": DockerValidator,
    "python": PythonValidator,
    "php": PHPValidator,
    "npm": NpmValidator,
    "go": GoValidator,
}

# Map filenames to ecosystems for auto-detection
DETECT_FILES = {
    "Dockerfile": "docker",
    "requirements.txt": "python",
    "pyproject.toml": "python",
    "composer.json": "php",
    "package.json": "npm",
    "go.mod": "go",
}

__all__ = [
    "VALIDATORS",
    "DETECT_FILES",
    "DockerValidator",
    "PythonValidator",
    "PHPValidator",
    "NpmValidator",
    "GoValidator",
]
