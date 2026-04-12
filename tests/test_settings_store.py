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

            store.save_settings(rules, extensions, False)
            loaded_rules, loaded_extensions, show_smb_warning = store.load_settings()

            self.assertEqual(len(loaded_rules), 1)
            self.assertEqual(loaded_rules[0].pattern, "fa")
            self.assertEqual(loaded_extensions, [".bin", ".cue", ".iso"])
            self.assertFalse(show_smb_warning)


if __name__ == "__main__":
    unittest.main()
