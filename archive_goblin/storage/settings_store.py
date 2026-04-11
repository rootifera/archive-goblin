from __future__ import annotations

import json
from json import JSONDecodeError
import os
from pathlib import Path

from archive_goblin.models.rule import Rule


class SettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or self.default_path()

    @staticmethod
    def default_path() -> Path:
        config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        return config_home / "archive-goblin" / "settings.json"

    def load_rules(self) -> list[Rule]:
        if not self.path.exists():
            return []

        try:
            with self.path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except JSONDecodeError:
            return []

        raw_rules = payload.get("rules", [])
        return [Rule.from_dict(rule_data) for rule_data in raw_rules]

    def save_rules(self, rules: list[Rule]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"rules": [rule.to_dict() for rule in rules]}
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
