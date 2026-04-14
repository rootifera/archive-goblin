from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from archive_goblin.models.project_metadata import ProjectMetadata
from archive_goblin.storage.project_store import ProjectStore


class ProjectStoreTests(unittest.TestCase):
    def test_round_trips_project_metadata(self) -> None:
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            store = ProjectStore()
            metadata = ProjectMetadata(
                title="Warcraft: Orcs & Humans",
                platform="DOS",
                description="Big box PC release.",
                license="CC",
                cc_allow_remixing=True,
                cc_require_share_alike=True,
                page_url_override="warcraft-custom-edit",
                tags=["pc", "dos", "big box"],
            )

            store.save_metadata(folder, metadata)
            loaded = store.load_metadata(folder)

            self.assertEqual(loaded.title, metadata.title)
            self.assertEqual(loaded.platform, metadata.platform)
            self.assertEqual(loaded.tags, metadata.tags)
            self.assertTrue(loaded.cc_allow_remixing)
            self.assertTrue(loaded.cc_require_share_alike)
            self.assertEqual(loaded.page_url_override, "warcraft-custom-edit")

    def test_missing_project_file_returns_empty_metadata(self) -> None:
        with TemporaryDirectory() as tmp:
            store = ProjectStore()
            loaded = store.load_metadata(Path(tmp))

            self.assertEqual(loaded.title, "")
            self.assertEqual(loaded.tags, [])


if __name__ == "__main__":
    unittest.main()
