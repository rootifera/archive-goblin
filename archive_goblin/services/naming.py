from __future__ import annotations

import re

from archive_goblin.models.file_item import FileItem
from archive_goblin.models.rule import FileType, Rule, coerce_file_type


class NamingService:
    def update_file_name(self, file_item: FileItem) -> None:
        file_item.type = coerce_file_type(file_item.type)
        if file_item.is_cover_image_copy:
            file_item.descriptor = "cover-image-01"
            file_item.proposed_name = file_item.original_name
            file_item.cover_image_name = None
            return

        descriptor = self._descriptor_for(file_item)
        file_item.descriptor = descriptor
        file_item.cover_image_name = self._cover_image_name_for(file_item)

        if file_item.do_not_rename or file_item.is_protected or file_item.type in {
            FileType.OTHER,
            FileType.IGNORE,
            FileType.DISK_IMAGE,
        }:
            file_item.proposed_name = file_item.original_name
            return

        prefix = self._prefix_for(file_item.type, file_item.index or 1)
        file_item.proposed_name = f"{prefix:03d}-{descriptor}{file_item.extension}"

    def build_preview_name(self, rule: Rule, extension: str = ".jpg") -> str:
        if rule.type in {FileType.OTHER, FileType.DISK_IMAGE, FileType.IGNORE}:
            return "No automatic rename"
        descriptor = self._descriptor_for_rule(rule)
        prefix = self._prefix_for(rule.type, rule.index)
        normalized_extension = extension if extension.startswith(".") else f".{extension}"
        return f"{prefix:03d}-{descriptor}{normalized_extension}"

    def _cover_image_name_for(self, file_item: FileItem) -> str | None:
        if not file_item.set_as_cover_image:
            return None
        return f"000-cover-image-01{file_item.extension}"

    def _prefix_for(self, file_type: FileType | str, index: int) -> int:
        resolved_file_type = coerce_file_type(file_type)
        normalized_index = max(1, index)
        if resolved_file_type is FileType.COVER_FRONT:
            return 100 + (normalized_index - 1) * 2
        if resolved_file_type is FileType.COVER_BACK:
            return 101 + (normalized_index - 1) * 2
        if resolved_file_type is FileType.COVER_OTHER:
            return 120 + (normalized_index - 1)
        if resolved_file_type is FileType.MEDIA_SCAN:
            return 200 + (normalized_index - 1)
        if resolved_file_type is FileType.DOCUMENT:
            return 300 + (normalized_index - 1)
        if resolved_file_type is FileType.CUSTOM:
            return 500 + (normalized_index - 1)
        if resolved_file_type is FileType.EXTRA:
            return 900 + (normalized_index - 1)
        raise ValueError(f"Unsupported file type for naming: {resolved_file_type.value}")

    def _descriptor_for(self, file_item: FileItem) -> str:
        index = max(1, file_item.index or 1)
        existing = self._sanitize_descriptor(file_item.descriptor)
        if existing:
            return existing

        if file_item.type is FileType.COVER_FRONT:
            return f"front-{index:02d}"
        if file_item.type is FileType.COVER_BACK:
            return f"back-{index:02d}"
        if file_item.type is FileType.COVER_OTHER:
            return f"cover-other-{index:02d}"
        if file_item.type is FileType.MEDIA_SCAN:
            return f"disk-{index:02d}"
        if file_item.type is FileType.DOCUMENT:
            return f"document-{index:02d}"
        if file_item.type is FileType.CUSTOM:
            if file_item.rule_output_name:
                return self._sanitize_descriptor(file_item.rule_output_name) or f"custom-{index:02d}"
            return f"custom-{index:02d}"
        if file_item.type is FileType.EXTRA:
            return f"extra-{index:02d}"
        return file_item.original_name

    def _descriptor_for_rule(self, rule: Rule) -> str:
        index = max(1, rule.index)
        if rule.type is FileType.COVER_FRONT:
            return f"front-{index:02d}"
        if rule.type is FileType.COVER_BACK:
            return f"back-{index:02d}"
        if rule.type is FileType.COVER_OTHER:
            return f"cover-other-{index:02d}"
        if rule.type is FileType.MEDIA_SCAN:
            return f"disk-{index:02d}"
        if rule.type is FileType.DOCUMENT:
            return f"document-{index:02d}"
        if rule.type is FileType.CUSTOM:
            if rule.output_name:
                return self._sanitize_descriptor(rule.output_name) or f"custom-{index:02d}"
            return f"custom-{index:02d}"
        if rule.type is FileType.EXTRA:
            return f"extra-{index:02d}"
        if rule.type is FileType.DISK_IMAGE:
            return "disk-image"
        if rule.type is FileType.IGNORE:
            return "ignored"
        return "other"

    def _sanitize_descriptor(self, descriptor: str | None) -> str:
        if descriptor is None:
            return ""

        cleaned = descriptor.strip().casefold().replace("_", "-")
        cleaned = re.sub(r"\s+", "-", cleaned)
        cleaned = re.sub(r"[^a-z0-9-]+", "-", cleaned)
        cleaned = re.sub(r"-{2,}", "-", cleaned)
        return cleaned.strip("-")
