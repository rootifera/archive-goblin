from __future__ import annotations

import os
import shutil
from pathlib import Path
from uuid import uuid4

from archive_goblin.models.file_item import FileItem, FileStatus


class RenameService:
    def apply(self, folder: Path, files: list[FileItem]) -> int:
        ready_files = [
            file_item
            for file_item in files
            if file_item.status is FileStatus.READY
        ]
        if not ready_files:
            return 0

        created_copies: list[Path] = []
        temp_copy_paths: list[Path] = []
        temp_paths: list[tuple[Path, Path, Path]] = []

        try:
            for file_item in ready_files:
                if file_item.cover_image_name is not None and file_item.has_pending_cover_copy:
                    copy_target = folder / file_item.cover_image_name
                    temp_copy_target = folder / f"archive-goblin-copy-{uuid4().hex[:8]}-{copy_target.name}"
                    temp_copy_paths.append(temp_copy_target)
                    with file_item.path.open("rb") as source_handle, temp_copy_target.open("wb") as target_handle:
                        shutil.copyfileobj(source_handle, target_handle, length=1024 * 1024)
                        target_handle.flush()
                        os.fsync(target_handle.fileno())
                    os.replace(temp_copy_target, copy_target)
                    created_copies.append(copy_target)

            rename_index = 0
            for file_item in ready_files:
                if not file_item.has_pending_rename or file_item.proposed_name is None:
                    continue
                rename_index += 1
                original_path = file_item.path
                temp_name = f"archive-goblin-{uuid4().hex[:8]}-{rename_index}{original_path.suffix}"
                temp_path = folder / temp_name
                original_path.rename(temp_path)
                temp_paths.append((temp_path, original_path, folder / file_item.proposed_name))

            for temp_path, _original_path, final_path in temp_paths:
                os.replace(temp_path, final_path)
        except Exception:
            for temp_path, original_path, final_path in reversed(temp_paths):
                if temp_path.exists():
                    os.replace(temp_path, original_path)
                elif final_path.exists() and not original_path.exists():
                    os.replace(final_path, original_path)
            for created_copy in reversed(created_copies):
                if created_copy.exists():
                    created_copy.unlink()
            for temp_copy_path in reversed(temp_copy_paths):
                if temp_copy_path.exists():
                    temp_copy_path.unlink()
            raise

        return len(ready_files)
