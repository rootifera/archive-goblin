from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType
from unittest.mock import patch

from archive_goblin.models.file_item import FileItem
from archive_goblin.models.project_metadata import ProjectMetadata
from archive_goblin.models.rule import FileType
from archive_goblin.services.archive_upload import ArchiveRecoveryDetails, ArchiveUploadPlan, ArchiveUploadService


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
            self.assertFalse(plan.is_resume)

    @patch("archive_goblin.services.archive_upload.ArchiveUploadService.inspect_existing_upload")
    @patch("archive_goblin.services.archive_upload.ArchiveMetadataService.check_identifier_availability")
    def test_prepare_upload_returns_resume_plan_for_partial_existing_item(
        self,
        mock_availability,
        mock_inspect,
    ) -> None:
        mock_availability.return_value.available = False
        mock_availability.return_value.message = "This Archive.org identifier already exists."

        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            existing_path = folder / "100-front-01.jpg"
            missing_path = folder / "200-disk-01.jpg"
            existing_path.write_text("a", encoding="utf-8")
            missing_path.write_text("b", encoding="utf-8")
            files = [
                FileItem(
                    path=existing_path,
                    detected_type=FileType.COVER_FRONT,
                    type=FileType.COVER_FRONT,
                    detected_index=1,
                    index=1,
                    proposed_name=existing_path.name,
                ),
                FileItem(
                    path=missing_path,
                    detected_type=FileType.MEDIA_SCAN,
                    type=FileType.MEDIA_SCAN,
                    detected_index=1,
                    index=1,
                    proposed_name=missing_path.name,
                ),
            ]

            mock_inspect.return_value = ArchiveRecoveryDetails(
                identifier="blade-runner",
                page_url="https://archive.org/details/blade-runner",
                remote_file_names=[existing_path.name],
                missing_file_paths=[missing_path],
            )
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

            self.assertTrue(plan.is_resume)
            self.assertEqual(plan.file_paths, [missing_path])

    @patch("archive_goblin.services.archive_upload.ArchiveUploadService.inspect_existing_upload")
    @patch("archive_goblin.services.archive_upload.ArchiveMetadataService.check_identifier_availability")
    def test_prepare_upload_blocks_when_existing_item_already_has_all_files(
        self,
        mock_availability,
        mock_inspect,
    ) -> None:
        mock_availability.return_value.available = False
        mock_availability.return_value.message = "This Archive.org identifier already exists."

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

            mock_inspect.return_value = ArchiveRecoveryDetails(
                identifier="blade-runner",
                page_url="https://archive.org/details/blade-runner",
                remote_file_names=[path.name],
                missing_file_paths=[],
            )
            result = self.service.prepare_upload(
                folder,
                files,
                ProjectMetadata(title="Blade Runner", collection="software:open_source_software"),
                "{title} ({release_year}) ({platform})",
                "{title}",
                [],
                "access",
                "secret",
            )

            self.assertFalse(result.success)
            self.assertIn("already present", result.message)

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

    def test_upload_plan_reports_byte_progress(self) -> None:
        events: list[tuple[int, str, int, int, float]] = []

        def fake_upload(_identifier, files, **_kwargs):
            upload_file = files[0]
            self.assertEqual(upload_file.name, "100-front-01.jpg")
            while upload_file.read(2):
                pass
            return [_FakeResponse()]

        fake_module = ModuleType("internetarchive")
        fake_module.upload = fake_upload

        with patch.dict("sys.modules", {"internetarchive": fake_module}):
            with TemporaryDirectory() as tmp:
                folder = Path(tmp)
                path = folder / "100-front-01.jpg"
                path.write_bytes(b"abcdef")
                plan = ArchiveUploadPlan(
                    identifier="blade-runner",
                    page_url="https://archive.org/details/blade-runner",
                    file_paths=[path],
                    metadata_payload={"title": "Blade Runner"},
                    access_key="access",
                    secret_key="secret",
                )

                result = self.service.upload_plan(
                    plan,
                    progress_callback=lambda *event: events.append(event),
                )

                self.assertTrue(result.success)
                self.assertTrue(events)
                self.assertEqual(events[-1][0], 0)
                self.assertEqual(events[-1][1], "100-front-01.jpg")
                self.assertEqual(events[-1][2], 6)
                self.assertEqual(events[-1][3], 6)
                self.assertGreater(events[-1][4], 0)


if __name__ == "__main__":
    unittest.main()
