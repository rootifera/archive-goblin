from __future__ import annotations

import os
from collections import Counter
from pathlib import Path

from archive_goblin.models.file_item import FileItem, FileStatus
from archive_goblin.models.rule import FileType


class RenameValidator:
    def validate(self, folder: Path | None, files: list[FileItem]) -> None:
        operation_targets = [
            file_item
            for file_item in files
            if self._has_pending_operation(file_item)
        ]
        target_counts = Counter(self._iter_target_names(operation_targets))
        moving_source_names = {
            file_item.original_name
            for file_item in operation_targets
            if file_item.has_pending_rename
        }

        for file_item in files:
            file_item.conflict_message = None

            if file_item.type is FileType.IGNORE:
                file_item.status = FileStatus.IGNORED
                continue

            if file_item.is_protected and not file_item.allow_protected_rename:
                file_item.status = FileStatus.PROTECTED
                continue

            if file_item.type is FileType.OTHER:
                file_item.status = FileStatus.UNCHANGED if file_item.do_not_rename else FileStatus.UNMATCHED
                continue

            has_rename = file_item.has_pending_rename
            has_cover_copy = file_item.has_pending_cover_copy
            if not has_rename and not has_cover_copy:
                if file_item.is_cover_image_copy:
                    file_item.status = FileStatus.DONE
                    continue
                if file_item.do_not_rename:
                    file_item.status = FileStatus.UNCHANGED
                    continue
                if file_item.type in {FileType.OTHER, FileType.DISK_IMAGE}:
                    file_item.status = FileStatus.UNCHANGED
                else:
                    file_item.status = FileStatus.DONE
                continue

            conflict_message = self._conflict_for_file(file_item, folder, target_counts, moving_source_names)
            if conflict_message is not None:
                file_item.status = FileStatus.CONFLICT
                file_item.conflict_message = conflict_message
                continue

            file_item.status = FileStatus.READY

    def _has_pending_operation(self, file_item: FileItem) -> bool:
        return (
            (not file_item.is_protected or file_item.allow_protected_rename)
            and file_item.type is not FileType.IGNORE
            and (file_item.has_pending_rename or file_item.has_pending_cover_copy)
        )

    def _iter_target_names(self, files: list[FileItem]) -> list[str]:
        names: list[str] = []
        for file_item in files:
            if file_item.has_pending_rename and file_item.proposed_name is not None:
                names.append(file_item.proposed_name)
            if file_item.has_pending_cover_copy and file_item.cover_image_name is not None:
                names.append(file_item.cover_image_name)
        return names

    def _conflict_for_file(
        self,
        file_item: FileItem,
        folder: Path | None,
        target_counts: Counter[str],
        moving_source_names: set[str],
    ) -> str | None:
        for target_name in self._iter_target_names([file_item]):
            if target_counts[target_name] > 1:
                return "Another file resolves to the same target name."

            if folder is None:
                continue

            target_path = folder / target_name
            target_exists = target_path.exists()
            same_existing_file = False
            if target_exists and file_item.path.exists():
                try:
                    same_existing_file = os.path.samefile(file_item.path, target_path)
                except OSError:
                    same_existing_file = False
            occupied_by_unmoved_file = (
                target_exists
                and not same_existing_file
                and target_name != file_item.original_name
                and target_name not in moving_source_names
            )
            if occupied_by_unmoved_file:
                return "Target filename already exists in the folder."

        return None
