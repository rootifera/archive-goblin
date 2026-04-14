from __future__ import annotations

from pathlib import Path

from archive_goblin.storage.project_store import ProjectStore


class FolderScanner:
    def scan(self, folder: Path) -> list[Path]:
        if not folder.exists():
            return []
        return sorted(
            [
                path
                for path in folder.iterdir()
                if path.is_file() and path.name != ProjectStore.filename
            ],
            key=lambda path: path.name.casefold(),
        )
