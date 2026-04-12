from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from archive_goblin.models.rule import FileType, coerce_file_type


class FileStatus(StrEnum):
    READY = "ready"
    DONE = "done"
    UNCHANGED = "unchanged"
    PROTECTED = "protected"
    CONFLICT = "conflict"
    UNMATCHED = "unmatched"
    IGNORED = "ignored"


@dataclass(slots=True)
class FileItem:
    path: Path
    detected_type: FileType
    type: FileType
    detected_index: int | None
    index: int | None
    matched_rule_pattern: str | None = None
    rule_output_name: str | None = None
    descriptor: str | None = None
    proposed_name: str | None = None
    manual_proposed_name: str | None = None
    cover_image_name: str | None = None
    is_protected: bool = False
    is_cover_image_copy: bool = False
    allow_protected_rename: bool = False
    set_as_cover_image: bool = False
    do_not_rename: bool = False
    status: FileStatus = FileStatus.UNCHANGED
    conflict_message: str | None = None

    def __post_init__(self) -> None:
        self.detected_type = coerce_file_type(self.detected_type)
        self.type = coerce_file_type(self.type)
        self.detected_index = None if self.detected_index is None else max(1, int(self.detected_index))
        self.index = None if self.index is None else max(1, int(self.index))

    @property
    def original_name(self) -> str:
        return self.path.name

    @property
    def extension(self) -> str:
        return self.path.suffix

    @property
    def stem(self) -> str:
        return self.path.stem

    @property
    def has_pending_rename(self) -> bool:
        return self.proposed_name not in (None, self.original_name)

    @property
    def is_locked(self) -> bool:
        return self.status is FileStatus.DONE

    @property
    def has_pending_cover_copy(self) -> bool:
        return self.cover_image_name not in (None, self.original_name)
