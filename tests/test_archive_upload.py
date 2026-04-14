from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType
from unittest.mock import patch

from archive_goblin.models.file_item import FileItem
from archive_goblin.models.project_metadata import ProjectMetadata
from archive_goblin.models.rule import FileType
from archive_goblin.services.archive_upload import ArchiveUploadService


class _FakeResponse:
    ok = True


class ArchiveUploadServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = ArchiveUploadService()

    def test_splits_collection_value_into_mediatype_and_collection(self) -> None:
        payload = self.service._build_metadata_payload(
            ProjectMetadata(
                title="Blade Runner",
                collection="software:open_source_software",
            ),
            "{title} ({release_year}) ({platform})",
            [],
        )

        self.assertEqual(payload["mediatype"], "software")
        self.assertEqual(payload["collection"], "open_source_software")

    @patch("archive_goblin.services.archive_upload.ArchiveMetadataService.check_identifier_availability")
    def test_blocks_existing_identifier(self, mock_availability) -> None:
        mock_availability.return_value.available = False
        mock_availability.return_value.message = "This Archive.org identifier already exists."

        result = self.service.prepare_upload(
            None,
            [],
            ProjectMetadata(),
            "{title} ({release_year}) ({platform})",
            "{title}",
            [],
            "access",
            "secret",
        )

        self.assertFalse(result.success)

    @patch("archive_goblin.services.archive_upload.ArchiveMetadataService.check_identifier_availability")
    def test_prepare_upload_returns_plan_for_available_identifier(self, mock_availability) -> None:
        mock_availability.return_value.available = True
        mock_availability.return_value.message = "available"

        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            path = folder / "100-front-01.jpg"
            path.write_text("data", encoding="utf-8")
            files = [
                FileItem(
                    path=path,
                    detected_type=FileType.COVER_FRONT,
                    type=FileType.COVER_FRONT,
                    detected_index=1,
                    index=1,
                    proposed_name=path.name,
                )
            ]

            plan = self.service.prepare_upload(
                folder,
                files,
                ProjectMetadata(title="Blade Runner", collection="software:open_source_software"),
                "{title} ({release_year}) ({platform})",
                "{title}",
                [],
                "access",
                "secret",
            )

            self.assertEqual(plan.identifier, "blade-runner")

    @patch("archive_goblin.services.archive_upload.ArchiveMetadataService.check_identifier_availability")
    def test_uploads_new_item_when_identifier_is_available(self, mock_availability) -> None:
        mock_availability.return_value.available = True
        mock_availability.return_value.message = "available"
        fake_module = ModuleType("internetarchive")
        fake_module.upload = lambda *args, **kwargs: [_FakeResponse()]

        with patch.dict("sys.modules", {"internetarchive": fake_module}):
            with TemporaryDirectory() as tmp:
                folder = Path(tmp)
                path = folder / "100-front-01.jpg"
                path.write_text("data", encoding="utf-8")
                files = [
                    FileItem(
                        path=path,
                        detected_type=FileType.COVER_FRONT,
                        type=FileType.COVER_FRONT,
                        detected_index=1,
                        index=1,
                        proposed_name=path.name,
                    )
                ]
                metadata = ProjectMetadata(
                    title="Blade Runner",
                    platform="PC",
                    collection="software:open_source_software",
                    description="Prepared with Archive Goblin:\nhttps://github.com/rootifera/archive-goblin",
                )

                plan = self.service.prepare_upload(
                    folder,
                    files,
                    metadata,
                    "{title} ({release_year}) ({platform})",
                    "{title}",
                    ["retro"],
                    "access",
                    "secret",
                )
                result = self.service.upload_plan(plan)

                self.assertTrue(result.success)


if __name__ == "__main__":
    unittest.main()
