from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FileType(StrEnum):
    COVER_FRONT = "cover_front"
    COVER_BACK = "cover_back"
    COVER_OTHER = "cover_other"
    MEDIA_SCAN = "media_scan"
    DOCUMENT = "document"
    CUSTOM = "custom"
    EXTRA = "extra"
    DISK_IMAGE = "disk_image"
    OTHER = "other"
    IGNORE = "ignore"


FILE_TYPE_VALUES: tuple[FileType, ...] = tuple(FileType)
FILE_TYPE_LABELS: dict[FileType, str] = {
    FileType.COVER_FRONT: "Cover Front",
    FileType.COVER_BACK: "Cover Back",
    FileType.COVER_OTHER: "Cover Other",
    FileType.MEDIA_SCAN: "Media Scan",
    FileType.DOCUMENT: "Document",
    FileType.CUSTOM: "Custom",
    FileType.EXTRA: "Extra",
    FileType.DISK_IMAGE: "Disk Image",
    FileType.OTHER: "Other",
    FileType.IGNORE: "Ignore",
}


def coerce_file_type(value: FileType | str) -> FileType:
    if isinstance(value, FileType):
        return value
    return FileType(str(value))


def file_type_label(value: FileType | str) -> str:
    return FILE_TYPE_LABELS[coerce_file_type(value)]


@dataclass(slots=True)
class Rule:
    pattern: str
    type: FileType
    index: int
    output_name: str | None = None

    def __post_init__(self) -> None:
        self.pattern = self.pattern.strip()
        self.type = coerce_file_type(self.type)
        self.index = max(1, int(self.index))
        if self.output_name is not None:
            self.output_name = self.output_name.strip() or None

    @property
    def normalized_pattern(self) -> str:
        return self.pattern.casefold()

    def matches(self, filename_stem: str) -> bool:
        return self.normalized_pattern == filename_stem.casefold()

    def to_dict(self) -> dict[str, str | int | None]:
        return {
            "pattern": self.pattern,
            "type": self.type.value,
            "index": self.index,
            "output_name": self.output_name,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "Rule":
        file_type = FileType(str(data["type"]))
        output_name = data.get("output_name")
        return cls(
            pattern=str(data["pattern"]),
            type=file_type,
            index=int(data["index"]),
            output_name=str(output_name) if output_name not in (None, "") else None,
        )
