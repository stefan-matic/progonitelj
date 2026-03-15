"""Python package validator - parses requirements.txt and pyproject.toml."""

import re
from pathlib import Path

from .base import BaseValidator, Dependency


class PythonValidator(BaseValidator):
    ecosystem = "python"

    def parse_dependencies(self, path: str) -> list[Dependency]:
        p = Path(path)
        if p.name == "pyproject.toml":
            return self._parse_pyproject(path)
        return self._parse_requirements(path)

    def _parse_requirements(self, path: str) -> list[Dependency]:
        """Parse requirements.txt format."""
        deps = []
        with open(path) as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue

                # Handle inline comments
                line = line.split("#")[0].strip()

                # Parse: package==1.0, package>=1.0, package~=1.0, etc.
                match = re.match(
                    r"^([a-zA-Z0-9][a-zA-Z0-9._-]*)\s*(?:([=!<>~]=?)\s*([a-zA-Z0-9_.* +-]+))?",
                    line,
                )
                if match:
                    name = match.group(1)
                    version = match.group(3)
                    if version:
                        # Take only the first version specifier for simple comparison
                        version = version.split(",")[0].strip()

                    deps.append(Dependency(
                        name=name,
                        version=version,
                        file_path=path,
                        line_number=i,
                    ))
        return deps

    def _parse_pyproject(self, path: str) -> list[Dependency]:
        """Parse pyproject.toml [project.dependencies]."""
        deps = []
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                return deps

        with open(path, "rb") as f:
            data = tomllib.load(f)

        dep_list = data.get("project", {}).get("dependencies", [])
        for i, spec in enumerate(dep_list, 1):
            match = re.match(r"^([a-zA-Z0-9][a-zA-Z0-9._-]*)\s*(?:[=!<>~]=?\s*(.+))?", spec)
            if match:
                name = match.group(1)
                version = match.group(2)
                if version:
                    version = version.split(",")[0].strip()
                deps.append(Dependency(
                    name=name,
                    version=version,
                    file_path=path,
                    line_number=i,
                ))
        return deps
