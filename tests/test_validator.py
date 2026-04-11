from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from archive_goblin.models.file_item import FileItem, FileStatus
from archive_goblin.models.rule import FileType
from archive_goblin.services.naming import NamingService
from archive_goblin.services.validator import RenameValidator


class RenameValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.naming = NamingService()
        self.validator = RenameValidator()

    def test_duplicate_targets_are_conflicts(self) -> None:
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            first = self._make_file(folder, "fa.jpg", FileType.COVER_FRONT, index=1)
            second = self._make_file(folder, "fb.jpg", FileType.COVER_FRONT, index=1)

            self.validator.validate(folder, [first, second])

            self.assertEqual(first.status, FileStatus.CONFLICT)
            self.assertEqual(second.status, FileStatus.CONFLICT)

    def test_existing_target_file_is_conflict(self) -> None:
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            self._write_file(folder / "100-front-01.jpg")
            item = self._make_file(folder, "fa.jpg", FileType.COVER_FRONT, index=1)

            self.validator.validate(folder, [item])

            self.assertEqual(item.status, FileStatus.CONFLICT)

    def test_done_status_for_already_normalized_file(self) -> None:
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            path = folder / "100-front-01.jpg"
            self._write_file(path)
            item = FileItem(
                path=path,
                detected_type=FileType.COVER_FRONT,
                type=FileType.COVER_FRONT,
                detected_index=1,
                index=1,
                descriptor="front-01",
                proposed_name=path.name,
            )

            self.validator.validate(folder, [item])

            self.assertEqual(item.status, FileStatus.DONE)

    def test_builtin_cover_copy_stays_ready(self) -> None:
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            path = folder / "000-cover-image-01.jpg"
            self._write_file(path)
            item = FileItem(
                path=path,
                detected_type=FileType.EXTRA,
                type=FileType.EXTRA,
                detected_index=1,
                index=1,
                proposed_name=path.name,
                is_cover_image_copy=True,
            )

            self.validator.validate(folder, [item])

            self.assertEqual(item.status, FileStatus.READY)

    def test_do_not_rename_with_cover_copy_is_ready(self) -> None:
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            item = self._make_file(folder, "scan.jpg", FileType.MEDIA_SCAN, index=1)
            item.do_not_rename = True
            item.set_as_cover_image = True
            self.naming.update_file_name(item)

            self.validator.validate(folder, [item])

            self.assertEqual(item.proposed_name, "scan.jpg")
            self.assertEqual(item.cover_image_name, "000-cover-image-01.jpg")
            self.assertEqual(item.status, FileStatus.READY)

    def test_protected_file_can_be_overridden_per_file(self) -> None:
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            item = self._make_file(folder, "cd.iso", FileType.MEDIA_SCAN, index=1)
            item.is_protected = True
            item.allow_protected_rename = True
            self.naming.update_file_name(item)

            self.validator.validate(folder, [item])

            self.assertEqual(item.proposed_name, "200-disk-01.iso")
            self.assertEqual(item.status, FileStatus.READY)

    def _make_file(self, folder: Path, name: str, file_type: FileType, index: int) -> FileItem:
        path = folder / name
        self._write_file(path)
        item = FileItem(
            path=path,
            detected_type=file_type,
            type=file_type,
            detected_index=index,
            index=index,
        )
        self.naming.update_file_name(item)
        return item

    def _write_file(self, path: Path) -> None:
        path.write_text("data", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
