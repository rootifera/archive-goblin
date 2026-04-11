from __future__ import annotations

import unittest
from pathlib import Path

from archive_goblin.models.rule import FileType, Rule
from archive_goblin.services.matcher import RuleMatcher


class RuleMatcherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.matcher = RuleMatcher()

    def test_matches_exact_stem_case_insensitively(self) -> None:
        rules = [Rule(pattern="A_FRONT", type=FileType.COVER_FRONT, index=1)]

        item = self.matcher.classify(Path("/tmp/a_front.JPG"), rules)

        self.assertEqual(item.type, FileType.COVER_FRONT)
        self.assertEqual(item.index, 1)

    def test_first_matching_rule_wins(self) -> None:
        rules = [
            Rule(pattern="fa", type=FileType.COVER_FRONT, index=1),
            Rule(pattern="fa", type=FileType.COVER_BACK, index=9),
        ]

        item = self.matcher.classify(Path("/tmp/fa.jpg"), rules)

        self.assertEqual(item.type, FileType.COVER_FRONT)
        self.assertEqual(item.index, 1)

    def test_unmatched_files_become_other(self) -> None:
        item = self.matcher.classify(Path("/tmp/unknown.png"), [])

        self.assertEqual(item.type, FileType.OTHER)

    def test_builtin_cover_copy_is_recognized(self) -> None:
        item = self.matcher.classify(Path("/tmp/000-cover-image-01.jpg"), [])

        self.assertTrue(item.is_cover_image_copy)
        self.assertEqual(item.type, FileType.EXTRA)

    def test_uses_configured_protected_extensions(self) -> None:
        item = self.matcher.classify(Path("/tmp/game.rom"), [], protected_extensions=["rom", ".iso"])

        self.assertEqual(item.type, FileType.DISK_IMAGE)
        self.assertTrue(item.is_protected)

    def test_protected_extension_can_still_match_rule(self) -> None:
        rules = [Rule(pattern="cd", type=FileType.MEDIA_SCAN, index=1)]

        item = self.matcher.classify(Path("/tmp/cd.iso"), rules)

        self.assertEqual(item.type, FileType.MEDIA_SCAN)
        self.assertTrue(item.is_protected)


if __name__ == "__main__":
    unittest.main()
