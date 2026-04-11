from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from archive_goblin.models.file_item import FileItem
from archive_goblin.models.rule import Rule


@dataclass(slots=True)
class Session:
    rules: list[Rule] = field(default_factory=list)
    protected_disk_image_extensions: list[str] = field(default_factory=list)
    folder: Path | None = None
    files: list[FileItem] = field(default_factory=list)
