"""Docker image validator - parses Dockerfiles and checks FROM images against policy."""

import re

from .base import BaseValidator, Dependency


class DockerValidator(BaseValidator):
    ecosystem = "docker"

    def _lookup_key(self, name: str) -> str:
        # Docker images keep their original name (no normalization)
        return name

    def parse_dependencies(self, path: str) -> list[Dependency]:
        deps = []
        with open(path) as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                # Match FROM instructions, handle --platform and AS alias
                match = re.match(
                    r"^FROM\s+(?:--platform=\S+\s+)?(\S+?)(?:\s+AS\s+\S+)?$",
                    line,
                    re.IGNORECASE,
                )
                if not match:
                    continue

                image_ref = match.group(1)

                # Skip build args like $BASE_IMAGE
                if image_ref.startswith("$"):
                    continue

                # Strip digest
                if "@" in image_ref:
                    image_ref = image_ref.split("@")[0]

                # Split image:tag
                if ":" in image_ref:
                    name, tag = image_ref.rsplit(":", 1)
                else:
                    name, tag = image_ref, "latest"

                deps.append(Dependency(
                    name=name,
                    version=tag,
                    file_path=path,
                    line_number=i,
                ))
        return deps
