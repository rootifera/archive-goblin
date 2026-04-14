from __future__ import annotations

import json
from json import JSONDecodeError
import os
from pathlib import Path

from archive_goblin.models.rule import Rule
from archive_goblin.services.archive_metadata import ArchiveMetadataService
from archive_goblin.services.matcher import DEFAULT_PROTECTED_DISK_IMAGE_EXTENSIONS, RuleMatcher


class SettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or self.default_path()

    @staticmethod
    def default_path() -> Path:
        config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        return config_home / "archive-goblin" / "settings.json"

    def load_settings(self) -> tuple[list[Rule], list[str], bool, str, str, list[str], str, str]:
        if not self.path.exists():
            return (
                [],
                sorted(DEFAULT_PROTECTED_DISK_IMAGE_EXTENSIONS),
                True,
                ArchiveMetadataService.default_title_pattern,
                ArchiveMetadataService.default_page_url_pattern,
                [],
                "",
                "",
            )

        try:
            with self.path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except JSONDecodeError:
            return (
                [],
                sorted(DEFAULT_PROTECTED_DISK_IMAGE_EXTENSIONS),
                True,
                ArchiveMetadataService.default_title_pattern,
                ArchiveMetadataService.default_page_url_pattern,
                [],
                "",
                "",
            )

        raw_rules = payload.get("rules", [])
        raw_extensions = payload.get("protected_disk_image_extensions", sorted(DEFAULT_PROTECTED_DISK_IMAGE_EXTENSIONS))
        show_smb_warning = bool(payload.get("show_smb_warning", True))
        title_pattern = str(payload.get("title_pattern", ArchiveMetadataService.default_title_pattern)).strip()
        page_url_pattern = str(payload.get("page_url_pattern", ArchiveMetadataService.default_page_url_pattern)).strip()
        default_tags = self._normalize_tags(payload.get("default_tags", []))
        archive_access_key = str(payload.get("archive_access_key", ""))
        archive_secret_key = str(payload.get("archive_secret_key", ""))
        rules = [Rule.from_dict(rule_data) for rule_data in raw_rules]
        extensions = self._normalize_extensions(raw_extensions)
        return (
            rules,
            extensions,
            show_smb_warning,
            title_pattern or ArchiveMetadataService.default_title_pattern,
            page_url_pattern or ArchiveMetadataService.default_page_url_pattern,
            default_tags,
            archive_access_key.strip(),
            archive_secret_key.strip(),
        )

    def load_rules(self) -> list[Rule]:
        rules, _extensions, _show_smb_warning, _title_pattern, _page_url_pattern, _default_tags, _archive_access_key, _archive_secret_key = self.load_settings()
        return rules

    def save_settings(
        self,
        rules: list[Rule],
        protected_disk_image_extensions: list[str],
        show_smb_warning: bool = True,
        title_pattern: str = ArchiveMetadataService.default_title_pattern,
        page_url_pattern: str = ArchiveMetadataService.default_page_url_pattern,
        default_tags: list[str] | None = None,
        archive_access_key: str = "",
        archive_secret_key: str = "",
    ) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "rules": [rule.to_dict() for rule in rules],
            "protected_disk_image_extensions": self._normalize_extensions(protected_disk_image_extensions),
            "show_smb_warning": bool(show_smb_warning),
            "title_pattern": title_pattern.strip() or ArchiveMetadataService.default_title_pattern,
            "page_url_pattern": page_url_pattern.strip() or ArchiveMetadataService.default_page_url_pattern,
            "default_tags": self._normalize_tags(default_tags or []),
            "archive_access_key": archive_access_key.strip(),
            "archive_secret_key": archive_secret_key.strip(),
        }
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")

    def save_rules(self, rules: list[Rule]) -> None:
        self.save_settings(rules, sorted(DEFAULT_PROTECTED_DISK_IMAGE_EXTENSIONS), True)

    def _normalize_extensions(self, raw_extensions: object) -> list[str]:
        values = raw_extensions if isinstance(raw_extensions, list) else []
        normalized = {
            RuleMatcher.normalize_extension(str(value))
            for value in values
            if RuleMatcher.normalize_extension(str(value))
        }
        if not normalized:
            normalized = set(DEFAULT_PROTECTED_DISK_IMAGE_EXTENSIONS)
        return sorted(normalized)

    def _normalize_tags(self, raw_tags: object) -> list[str]:
        values = raw_tags if isinstance(raw_tags, list) else []
        normalized: list[str] = []
        seen: set[str] = set()
        for value in values:
            cleaned = str(value).strip()
            if not cleaned:
                continue
            lowered = cleaned.casefold()
            if lowered in seen:
                continue
            seen.add(lowered)
            normalized.append(cleaned)
        return normalized
