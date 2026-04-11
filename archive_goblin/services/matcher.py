from __future__ import annotations

from pathlib import Path
import re

from archive_goblin.models.file_item import FileItem
from archive_goblin.models.rule import FileType, Rule


DEFAULT_PROTECTED_DISK_IMAGE_EXTENSIONS = {
    ".cue",
    ".ccd",
    ".img",
    ".sub",
    ".bin",
    ".iso",
}

NORMALIZED_NAME_RE = re.compile(r"^(?P<prefix>\d{3})-(?P<descriptor>.+)$", re.IGNORECASE)
BUILTIN_COVER_COPY_RE = re.compile(r"^000-cover-image-01$", re.IGNORECASE)


class RuleMatcher:
    def classify(
        self,
        path: Path,
        rules: list[Rule],
        protected_extensions: list[str] | set[str] | None = None,
    ) -> FileItem:
        active_protected_extensions = {
            self.normalize_extension(extension)
            for extension in (protected_extensions or DEFAULT_PROTECTED_DISK_IMAGE_EXTENSIONS)
        }
        extension = path.suffix.casefold()
        is_protected_extension = extension in active_protected_extensions

        normalized_match = self._match_normalized_name(path)
        if normalized_match is not None:
            return normalized_match

        for rule in rules:
            if rule.matches(path.stem):
                return FileItem(
                    path=path,
                    detected_type=rule.type,
                    type=rule.type,
                    detected_index=rule.index,
                    index=rule.index,
                    matched_rule_pattern=rule.pattern,
                    rule_output_name=rule.output_name,
                    is_protected=is_protected_extension,
                )

        if is_protected_extension:
            return FileItem(
                path=path,
                detected_type=FileType.DISK_IMAGE,
                type=FileType.DISK_IMAGE,
                detected_index=None,
                index=None,
                is_protected=True,
            )

        return FileItem(
            path=path,
            detected_type=FileType.OTHER,
            type=FileType.OTHER,
            detected_index=None,
            index=1,
        )

    def _match_normalized_name(self, path: Path) -> FileItem | None:
        if BUILTIN_COVER_COPY_RE.match(path.stem):
            return FileItem(
                path=path,
                detected_type=FileType.EXTRA,
                type=FileType.EXTRA,
                detected_index=1,
                index=1,
                descriptor="cover-image-01",
                proposed_name=path.name,
                is_cover_image_copy=True,
            )

        match = NORMALIZED_NAME_RE.match(path.stem)
        if not match:
            return None

        prefix = int(match.group("prefix"))
        descriptor = match.group("descriptor").strip().casefold()
        resolved = self._type_and_index_from_prefix(prefix)
        if resolved is None:
            return None

        file_type, index = resolved
        return FileItem(
            path=path,
            detected_type=file_type,
            type=file_type,
            detected_index=index,
            index=index,
            descriptor=descriptor,
            proposed_name=path.name,
        )

    def _type_and_index_from_prefix(self, prefix: int) -> tuple[FileType, int] | None:
        if 100 <= prefix <= 119:
            offset = prefix - 100
            if offset % 2 == 0:
                return FileType.COVER_FRONT, (offset // 2) + 1
            return FileType.COVER_BACK, (offset // 2) + 1
        if 120 <= prefix <= 199:
            return FileType.COVER_OTHER, (prefix - 120) + 1
        if 200 <= prefix <= 299:
            return FileType.MEDIA_SCAN, (prefix - 200) + 1
        if 300 <= prefix <= 399:
            return FileType.DOCUMENT, (prefix - 300) + 1
        if 500 <= prefix <= 599:
            return FileType.CUSTOM, (prefix - 500) + 1
        if 900 <= prefix <= 999:
            return FileType.EXTRA, (prefix - 900) + 1
        return None

    @staticmethod
    def normalize_extension(value: str) -> str:
        cleaned = value.strip().casefold()
        if not cleaned:
            return ""
        if not cleaned.startswith("."):
            cleaned = f".{cleaned}"
        return cleaned
