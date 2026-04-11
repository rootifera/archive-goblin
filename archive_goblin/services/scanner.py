from __future__ import annotations

from pathlib import Path


class FolderScanner:
    def scan(self, folder: Path) -> list[Path]:
        if not folder.exists():
            return []
        return sorted(
            [path for path in folder.iterdir() if path.is_file()],
            key=lambda path: path.name.casefold(),
        )
