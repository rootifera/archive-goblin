from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from archive_goblin.models.file_item import FileStatus
from archive_goblin.models.rule import FileType
from archive_goblin.services.naming import NamingService
from archive_goblin.services.renamer import RenameService
from archive_goblin.services.validator import RenameValidator


class RenameServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.naming = NamingService()
        self.validator = RenameValidator()
        self.renamer = RenameService()

    def test_apply_renames_file_and_creates_cover_copy(self) -> None:
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source = folder / "fa.jpg"
            source.write_text("image-data", encoding="utf-8")

            from archive_goblin.models.file_item import FileItem

            item = FileItem(
                path=source,
                detected_type=FileType.COVER_FRONT,
                type=FileType.COVER_FRONT,
                detected_index=1,
                index=1,
                set_as_cover_image=True,
            )
            self.naming.update_file_name(item)
            self.validator.validate(folder, [item])

            self.assertEqual(item.status, FileStatus.READY)

            count = self.renamer.apply(folder, [item])

            self.assertEqual(count, 1)
            renamed_path = folder / "100-front-01.jpg"
            cover_copy_path = folder / "000-cover-image-01.jpg"
            self.assertTrue(renamed_path.exists())
            self.assertTrue(cover_copy_path.exists())
            self.assertEqual(renamed_path.read_text(encoding="utf-8"), "image-data")
            self.assertEqual(cover_copy_path.read_text(encoding="utf-8"), "image-data")

    def test_apply_supports_multi_file_swap(self) -> None:
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            first = folder / "first.txt"
            second = folder / "second.txt"
            first.write_text("A", encoding="utf-8")
            second.write_text("B", encoding="utf-8")

            from archive_goblin.models.file_item import FileItem

            first_item = FileItem(
                path=first,
                detected_type=FileType.DOCUMENT,
                type=FileType.DOCUMENT,
                detected_index=1,
                index=1,
                proposed_name="second.txt",
                descriptor="second",
            )
            second_item = FileItem(
                path=second,
                detected_type=FileType.DOCUMENT,
                type=FileType.DOCUMENT,
                detected_index=2,
                index=2,
                proposed_name="first.txt",
                descriptor="first",
            )
            first_item.status = FileStatus.READY
            second_item.status = FileStatus.READY

            count = self.renamer.apply(folder, [first_item, second_item])

            self.assertEqual(count, 2)
            self.assertEqual((folder / "first.txt").read_text(encoding="utf-8"), "B")
            self.assertEqual((folder / "second.txt").read_text(encoding="utf-8"), "A")


if __name__ == "__main__":
    unittest.main()
