"""Go module validator - parses go.mod files."""

import re

from .base import BaseValidator, Dependency


class GoValidator(BaseValidator):
    ecosystem = "go"

    def _lookup_key(self, name: str) -> str:
        # Go modules use full paths, keep as-is
        return name

    def parse_dependencies(self, path: str) -> list[Dependency]:
        deps = []
        in_require = False
        in_replace = False

        with open(path) as f:
            for i, line in enumerate(f, 1):
                raw = line
                line = line.strip()

                if not line or line.startswith("//"):
                    continue

                # Track block boundaries
                if line.startswith("require ("):
                    in_require = True
                    continue
                if line.startswith("replace (") or line.startswith("exclude ("):
                    in_replace = True
                    continue
                if line == ")":
                    in_require = False
                    in_replace = False
                    continue

                # Skip replace/exclude blocks
                if in_replace:
                    continue

                # Parse require lines (both block and single-line)
                if in_require:
                    match = re.match(r"^(\S+)\s+(v?\S+)", line)
                elif line.startswith("require "):
                    match = re.match(r"^require\s+(\S+)\s+(v?\S+)", line)
                else:
                    continue

                if match:
                    module = match.group(1)
                    version = match.group(2).lstrip("v")

                    # Strip +incompatible suffix
                    version = re.sub(r"\+incompatible$", "", version)

                    deps.append(Dependency(
                        name=module,
                        version=version,
                        file_path=path,
                        line_number=i,
                    ))
        return deps
