from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path

from archive_goblin.models.project_metadata import ProjectMetadata


class ProjectStore:
    filename = ".archive-goblin-project.json"

    def path_for_folder(self, folder: Path) -> Path:
        return folder / self.filename

    def load_metadata(self, folder: Path | None) -> ProjectMetadata:
        if folder is None:
            return ProjectMetadata()

        path = self.path_for_folder(folder)
        if not path.exists():
            return ProjectMetadata()

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except JSONDecodeError:
            return ProjectMetadata()

        return ProjectMetadata.from_dict(payload)

    def save_metadata(self, folder: Path | None, metadata: ProjectMetadata) -> None:
        if folder is None:
            return

        path = self.path_for_folder(folder)
        path.write_text(json.dumps(metadata.to_dict(), indent=2) + "\n", encoding="utf-8")
