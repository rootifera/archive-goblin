from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ProjectMetadata:
    title: str = ""
    date: str = ""
    publisher: str = ""
    developer: str = ""
    platform: str = ""
    language: str = ""
    license: str = ""
    cc_allow_remixing: bool = False
    cc_require_share_alike: bool = False
    cc_prohibit_commercial_use: bool = False
    collection: str = ""
    page_url_override: str = ""
    description: str = ""
    notes: str = ""
    use_default_tags: bool = True
    tags: list[str] | None = None

    def __post_init__(self) -> None:
        self.tags = self._normalize_tags(self.tags)

    def to_dict(self) -> dict[str, object]:
        return {
            "title": self.title.strip(),
            "date": self.date.strip(),
            "publisher": self.publisher.strip(),
            "developer": self.developer.strip(),
            "platform": self.platform.strip(),
            "language": self.language.strip(),
            "license": self.license.strip(),
            "cc_allow_remixing": bool(self.cc_allow_remixing),
            "cc_require_share_alike": bool(self.cc_require_share_alike),
            "cc_prohibit_commercial_use": bool(self.cc_prohibit_commercial_use),
            "collection": self.collection.strip(),
            "page_url_override": self.page_url_override.strip(),
            "description": self.description.strip(),
            "notes": self.notes.strip(),
            "use_default_tags": bool(self.use_default_tags),
            "tags": list(self.tags or []),
        }

    @classmethod
    def from_dict(cls, payload: object) -> ProjectMetadata:
        data = payload if isinstance(payload, dict) else {}
        return cls(
            title=str(data.get("title", "")),
            date=str(data.get("date", "")),
            publisher=str(data.get("publisher", "")),
            developer=str(data.get("developer", "")),
            platform=str(data.get("platform", "")),
            language=str(data.get("language", "")),
            license=str(data.get("license", "")),
            cc_allow_remixing=bool(data.get("cc_allow_remixing", False)),
            cc_require_share_alike=bool(data.get("cc_require_share_alike", False)),
            cc_prohibit_commercial_use=bool(data.get("cc_prohibit_commercial_use", False)),
            collection=str(data.get("collection", "")),
            page_url_override=str(data.get("page_url_override", "")),
            description=str(data.get("description", "")),
            notes=str(data.get("notes", "")),
            use_default_tags=bool(data.get("use_default_tags", True)),
            tags=data.get("tags"),
        )

    @property
    def tags_text(self) -> str:
        return ", ".join(self.tags or [])

    def set_tags_from_text(self, value: str) -> None:
        self.tags = self._normalize_tags(value.split(","))

    @property
    def readiness_summary(self) -> str:
        required_fields = {
            "title": self.title,
            "platform": self.platform,
            "description": self.description,
        }
        completed = sum(1 for value in required_fields.values() if value.strip())
        return f"{completed}/{len(required_fields)} core fields filled"

    @staticmethod
    def _normalize_tags(values: object) -> list[str]:
        if not isinstance(values, list):
            return []
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
