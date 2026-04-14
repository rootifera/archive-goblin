from __future__ import annotations

import unittest

from pathlib import Path

from archive_goblin.models.file_item import FileItem
from archive_goblin.models.project_metadata import ProjectMetadata
from archive_goblin.models.rule import FileType
from archive_goblin.services.archive_metadata import ArchiveMetadataService


class ArchiveMetadataServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = ArchiveMetadataService()

    def test_build_identifier_from_pattern(self) -> None:
        metadata = ProjectMetadata(
            title="Warcraft: Orcs & Humans",
            date="1994",
            language="English",
        )

        identifier = self.service.build_identifier("{title}-{release_year}-{language}", metadata)

        self.assertEqual(identifier, "warcraft-orcs-humans-1994-english")

    def test_effective_tags_include_defaults_when_enabled(self) -> None:
        metadata = ProjectMetadata(tags=["big box"], use_default_tags=True)

        tags = self.service.effective_tags(metadata, ["software", "big box"])

        self.assertEqual(tags, ["software", "big box"])

    def test_effective_tags_skip_defaults_when_disabled(self) -> None:
        metadata = ProjectMetadata(tags=["big box"], use_default_tags=False)

        tags = self.service.effective_tags(metadata, ["software"])

        self.assertEqual(tags, ["big box"])

    def test_language_code_resolves_to_archive_label(self) -> None:
        metadata = ProjectMetadata(
            title="Warcraft",
            date="1994",
            language="eng",
        )

        identifier = self.service.build_identifier("{title}-{language}", metadata)

        self.assertEqual(identifier, "warcraft-english")
        self.assertEqual(self.service.language_code_for_value("English"), "eng")

    def test_license_and_collection_value_mapping(self) -> None:
        self.assertEqual(self.service.option_value_for_input([("CC0", "CC0 - No Rights Reserved")], "CC0 - No Rights Reserved"), "CC0")
        self.assertEqual(
            self.service.option_value_for_input(
                [("software:open_source_software", "Community software")],
                "Community software",
            ),
            "software:open_source_software",
        )

    def test_empty_metadata_payload_means_identifier_available(self) -> None:
        result = self.service._availability_from_payload([])

        self.assertTrue(result.available)

    def test_metadata_payload_means_identifier_taken(self) -> None:
        result = self.service._availability_from_payload({"metadata": {"identifier": "example"}})

        self.assertFalse(result.available)

    def test_generated_description_uses_normalized_archive_goblin_layout(self) -> None:
        metadata = ProjectMetadata(
            title="Warcraft",
            date="1994",
            publisher="Blizzard",
            developer="Blizzard",
            notes="Includes big box scans.",
        )
        files = [
            FileItem(Path("disc1.iso"), FileType.DISK_IMAGE, FileType.DISK_IMAGE, None, None),
            FileItem(Path("disc-scan.jpg"), FileType.MEDIA_SCAN, FileType.MEDIA_SCAN, 1, 1),
            FileItem(Path("front.jpg"), FileType.COVER_FRONT, FileType.COVER_FRONT, 1, 1),
            FileItem(Path("manual.pdf"), FileType.DOCUMENT, FileType.DOCUMENT, 1, 1),
            FileItem(Path("poster.jpg"), FileType.EXTRA, FileType.EXTRA, 1, 1),
            FileItem(Path("misc.txt"), FileType.OTHER, FileType.OTHER, None, 1),
        ]

        description = self.service.generate_description(metadata, files)

        self.assertIn("Warcraft (1994)", description)
        self.assertIn("Developer: Blizzard", description)
        self.assertIn("Publisher: Blizzard", description)
        self.assertIn("1 x Disk images", description)
        self.assertIn("1 x Disk scans", description)
        self.assertIn("1 x Cover Images", description)
        self.assertIn("1 x Documents", description)
        self.assertIn("1 x Extras", description)
        self.assertIn("1 x Other files", description)
        self.assertIn("Notes:", description)
        self.assertIn("Includes big box scans.", description)
        self.assertIn("Prepared with Archive Goblin:", description)
        self.assertIn("https://github.com/rootifera/archive-goblin", description)

    def test_disk_image_sidecar_files_are_counted_as_one_disk(self) -> None:
        metadata = ProjectMetadata(title="Game")
        files = [
            FileItem(Path("disc1.ccd"), FileType.DISK_IMAGE, FileType.DISK_IMAGE, None, None),
            FileItem(Path("disc1.cue"), FileType.DISK_IMAGE, FileType.DISK_IMAGE, None, None),
            FileItem(Path("disc1.img"), FileType.DISK_IMAGE, FileType.DISK_IMAGE, None, None),
            FileItem(Path("disc1.sub"), FileType.DISK_IMAGE, FileType.DISK_IMAGE, None, None),
            FileItem(Path("disc2.ccd"), FileType.DISK_IMAGE, FileType.DISK_IMAGE, None, None),
            FileItem(Path("disc2.cue"), FileType.DISK_IMAGE, FileType.DISK_IMAGE, None, None),
            FileItem(Path("disc2.img"), FileType.DISK_IMAGE, FileType.DISK_IMAGE, None, None),
            FileItem(Path("disc2.sub"), FileType.DISK_IMAGE, FileType.DISK_IMAGE, None, None),
        ]

        description = self.service.generate_description(metadata, files)

        self.assertIn("2 x Disk images", description)

    def test_format_display_title_includes_platform_when_present(self) -> None:
        title = self.service.format_display_title(
            ProjectMetadata(
                title="Beneath a Steel Sky",
                date="1994",
                platform="PC",
            )
        )

        self.assertEqual(title, "Beneath a Steel Sky (1994) (PC)")

    def test_page_url_override_wins_over_pattern(self) -> None:
        metadata = ProjectMetadata(
            title="Warcraft",
            date="1994",
            language="eng",
            page_url_override="https://archive.org/details/warcraft-custom-edit",
        )

        identifier = self.service.build_identifier("{title}-{release_year}-{language}", metadata)

        self.assertEqual(identifier, "warcraft-custom-edit")

    def test_page_url_override_preserves_underscores(self) -> None:
        identifier = self.service.normalize_identifier_input("https://archive.org/details/expendable_202604")

        self.assertEqual(identifier, "expendable_202604")


if __name__ == "__main__":
    unittest.main()
