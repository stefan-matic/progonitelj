"""PHP package validator - parses composer.json."""

import json
import re

from .base import BaseValidator, Dependency


class PHPValidator(BaseValidator):
    ecosystem = "php"

    def _lookup_key(self, name: str) -> str:
        # PHP packages use vendor/package format, exact match
        return name

    def parse_dependencies(self, path: str) -> list[Dependency]:
        deps = []
        with open(path) as f:
            data = json.load(f)

        for section in ("require", "require-dev"):
            for name, constraint in data.get(section, {}).items():
                # Skip PHP version and extensions
                if name == "php" or name.startswith("ext-"):
                    continue

                # Extract the base version from constraint (^1.2, ~2.0, >=3.0, 1.0.*)
                version = self._extract_version(constraint)

                deps.append(Dependency(
                    name=name,
                    version=version,
                    file_path=path,
                ))
        return deps

    @staticmethod
    def _extract_version(constraint: str) -> str | None:
        """Extract a comparable version from a Composer version constraint."""
        # Handle exact versions first
        match = re.match(r"^v?(\d+\.\d+(?:\.\d+)?)", constraint.strip())
        if match:
            return match.group(1)

        # Strip operators and try again
        cleaned = re.sub(r"^[^0-9v]*", "", constraint.strip())
        match = re.match(r"^v?(\d+\.\d+(?:\.\d+)?)", cleaned)
        if match:
            return match.group(1)

        return None
