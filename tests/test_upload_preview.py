from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from archive_goblin.models.file_item import FileItem, FileStatus
from archive_goblin.models.project_metadata import ProjectMetadata
from archive_goblin.models.rule import FileType
from archive_goblin.services.upload_preview import UploadPreviewService


class UploadPreviewServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = UploadPreviewService()

    def test_builds_summary_and_flags_blockers(self) -> None:
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
                    status=FileStatus.DONE,
                ),
                FileItem(
                    path=folder / "other.bin",
                    detected_type=FileType.OTHER,
                    type=FileType.OTHER,
                    detected_index=None,
                    index=1,
                    status=FileStatus.UNMATCHED,
                ),
            ]
            metadata = ProjectMetadata(
                title="Blade Runner",
                date="1997",
                platform="PC",
                collection="software:open_source_software",
                language="eng",
            )

            summary = self.service.build_summary(
                folder,
                files,
                metadata,
                "{title}-{release_year}",
                ["retro"],
                "",
                "",
            )

            self.assertEqual(summary.identifier, "blade-runner-1997")
            self.assertEqual(summary.file_count, 2)
            self.assertTrue(any("credentials" in issue.casefold() for issue in summary.blocked_issues))
            self.assertTrue(any("unmatched" in warning.casefold() for warning in summary.warnings))


if __name__ == "__main__":
    unittest.main()
