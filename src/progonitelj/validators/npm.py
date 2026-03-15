"""npm package validator - parses package.json."""

import json
import re

from .base import BaseValidator, Dependency


class NpmValidator(BaseValidator):
    ecosystem = "npm"

    def _lookup_key(self, name: str) -> str:
        # npm packages use exact names as written in package.json
        return name

    def parse_dependencies(self, path: str) -> list[Dependency]:
        deps = []
        with open(path) as f:
            data = json.load(f)

        for section in ("dependencies", "devDependencies"):
            for name, version_range in data.get(section, {}).items():
                version = self._extract_version(version_range)
                deps.append(Dependency(
                    name=name,
                    version=version,
                    file_path=path,
                ))
        return deps

    @staticmethod
    def _extract_version(version_range: str) -> str | None:
        """Extract a comparable version from an npm semver range."""
        # Handle workspace, file, git references
        if version_range.startswith(("workspace:", "file:", "git:", "github:", "http")):
            return None

        # Extract version number from semver range (^1.2.3, ~1.2.3, >=1.2.3, 1.2.3)
        match = re.match(r"^[^0-9]*(\d+\.\d+\.\d+(?:-[\w.]+)?)", version_range.strip())
        if match:
            return match.group(1)

        # Handle major.minor (e.g., ^1.2)
        match = re.match(r"^[^0-9]*(\d+\.\d+)", version_range.strip())
        if match:
            return match.group(1)

        return None
