from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from archive_goblin.services.scanner import FolderScanner
from archive_goblin.storage.project_store import ProjectStore


class FolderScannerTests(unittest.TestCase):
    def test_ignores_archive_goblin_project_file(self) -> None:
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "cover.jpg").write_text("image", encoding="utf-8")
            (folder / ProjectStore.filename).write_text("{}", encoding="utf-8")

            scanned = FolderScanner().scan(folder)

            self.assertEqual([path.name for path in scanned], ["cover.jpg"])


if __name__ == "__main__":
    unittest.main()
