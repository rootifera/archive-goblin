from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from archive_goblin.models.rule import FileType, Rule
from archive_goblin.storage.settings_store import SettingsStore


class SettingsStoreTests(unittest.TestCase):
    def test_round_trips_rules_and_protected_extensions(self) -> None:
        with TemporaryDirectory() as tmp:
            store = SettingsStore(Path(tmp) / "settings.json")
            rules = [Rule(pattern="fa", type=FileType.COVER_FRONT, index=1)]
            extensions = ["iso", ".bin", ".cue"]
            default_tags = ["software", "retro pc"]

            store.save_settings(
                rules,
                extensions,
                False,
                "{title} ({release_year}) ({platform})",
                "{title}-{release_year}",
                default_tags,
                "access123",
                "secret456",
            )
            (
                loaded_rules,
                loaded_extensions,
                show_smb_warning,
                title_pattern,
                page_url_pattern,
                loaded_default_tags,
                archive_access_key,
                archive_secret_key,
            ) = store.load_settings()

            self.assertEqual(len(loaded_rules), 1)
            self.assertEqual(loaded_rules[0].pattern, "fa")
            self.assertEqual(loaded_extensions, [".bin", ".cue", ".iso"])
            self.assertFalse(show_smb_warning)
            self.assertEqual(title_pattern, "{title} ({release_year}) ({platform})")
            self.assertEqual(page_url_pattern, "{title}-{release_year}")
            self.assertEqual(loaded_default_tags, default_tags)
            self.assertEqual(archive_access_key, "access123")
            self.assertEqual(archive_secret_key, "secret456")


if __name__ == "__main__":
    unittest.main()
