from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlparse
from urllib.request import Request, urlopen

from archive_goblin.models.file_item import FileItem
from archive_goblin.models.rule import FileType
from archive_goblin.models.project_metadata import ProjectMetadata
from archive_goblin.services.archive_language_data import ARCHIVE_LANGUAGE_OPTIONS_HTML

LANGUAGE_OPTION_RE = re.compile(r'<option value="(?P<value>[^"]*)"[^>]*>(?P<label>.*?)</option>', re.IGNORECASE)

ARCHIVE_LICENSE_OPTIONS = [
    ("", "Leave license blank"),
    ("CC0", "CC0 - No Rights Reserved"),
    ("CC", "Creative Commons"),
    ("PD", "Public Domain"),
]

ARCHIVE_COLLECTION_OPTIONS = [
    ("", "- - - Pick a collection - - -"),
    ("movies:opensource_movies", "Community movies"),
    ("audio:opensource_audio", "Community audio"),
    ("texts:opensource", "Community texts"),
    ("software:open_source_software", "Community software"),
    ("image:opensource_image", "Community image"),
    ("data:opensource_media", "Community data"),
]


@dataclass(slots=True)
class IdentifierAvailability:
    available: bool
    message: str


def _parse_language_options() -> list[tuple[str, str]]:
    seen: set[tuple[str, str]] = set()
    options: list[tuple[str, str]] = []
    for match in LANGUAGE_OPTION_RE.finditer(ARCHIVE_LANGUAGE_OPTIONS_HTML):
        value = html.unescape(match.group("value")).strip()
        label = html.unescape(match.group("label")).strip()
        if not value or not label or label == "---":
            continue
        key = (value, label)
        if key in seen:
            continue
        seen.add(key)
        options.append(key)
    return options


ARCHIVE_LANGUAGE_OPTIONS = _parse_language_options()


class ArchiveMetadataService:
    default_title_pattern = "{title} ({release_year}) ({platform})"
    default_page_url_pattern = "{title}-{release_year}-{language}"

    def format_display_title(self, metadata: ProjectMetadata, pattern: str | None = None) -> str:
        title = metadata.title.strip() or "Untitled item"
        release_year = self._release_year(metadata.date)
        platform = metadata.platform.strip()
        resolved_pattern = (pattern or self.default_title_pattern).strip() or self.default_title_pattern
        values = {
            "title": title,
            "release_year": release_year,
            "platform": platform,
            "date": metadata.date.strip(),
            "language": self.language_name_for_code(metadata.language).strip(),
            "publisher": metadata.publisher.strip(),
            "developer": metadata.developer.strip(),
            "collection": metadata.collection.strip(),
        }
        rendered = resolved_pattern.format_map(_SafeFormatDict(values))
        rendered = re.sub(r"\s+", " ", rendered).strip()
        rendered = re.sub(r"\(\s*\)", "", rendered)
        rendered = re.sub(r"\[\s*\]", "", rendered)
        rendered = re.sub(r"\s{2,}", " ", rendered).strip(" -,:")
        return rendered or title

    def build_identifier(self, pattern: str, metadata: ProjectMetadata) -> str:
        override = self.normalize_identifier_input(metadata.page_url_override)
        if override:
            return override

        resolved_pattern = pattern.strip() or self.default_page_url_pattern
        language_code = metadata.language
        language_name = self.language_name_for_code(language_code) or metadata.language
        values = {
            "title": metadata.title,
            "date": metadata.date,
            "release_year": self._release_year(metadata.date),
            "language": language_name,
            "language_code": language_code,
            "language_name": language_name,
            "publisher": metadata.publisher,
            "developer": metadata.developer,
            "platform": metadata.platform,
            "collection": metadata.collection,
        }
        rendered = resolved_pattern.format_map({key: self._slugify(value) for key, value in values.items()})
        rendered = re.sub(r"-{2,}", "-", rendered)
        return rendered.strip("-")

    def build_page_url(self, pattern: str, metadata: ProjectMetadata) -> str:
        identifier = self.build_identifier(pattern, metadata)
        if not identifier:
            return ""
        return f"https://archive.org/details/{quote(identifier)}"

    def effective_tags(self, metadata: ProjectMetadata, default_tags: list[str]) -> list[str]:
        seen: set[str] = set()
        values: list[str] = []
        if metadata.use_default_tags:
            for tag in default_tags:
                self._add_tag(values, seen, tag)
        for tag in metadata.tags or []:
            self._add_tag(values, seen, tag)
        return values

    def check_identifier_availability(self, identifier: str) -> IdentifierAvailability:
        normalized_identifier = identifier.strip()
        if not normalized_identifier:
            return IdentifierAvailability(False, "Enter enough metadata to generate a page URL first.")

        url = f"https://archive.org/metadata/{quote(normalized_identifier)}"
        request = Request(url, method="GET", headers={"User-Agent": "Archive Goblin"})
        try:
            with urlopen(request, timeout=6) as response:
                payload = json.loads(response.read().decode("utf-8"))
                return self._availability_from_payload(payload)
        except HTTPError as exc:
            return IdentifierAvailability(False, f"Archive.org returned HTTP {exc.code}.")
        except URLError as exc:
            return IdentifierAvailability(False, f"Could not check Archive.org availability: {exc.reason}")
        except json.JSONDecodeError:
            return IdentifierAvailability(False, "Archive.org returned an unexpected response.")

        return IdentifierAvailability(False, "This Archive.org identifier could not be confirmed as available.")

    def language_name_for_code(self, code: str) -> str:
        normalized_code = code.strip()
        for option_code, label in ARCHIVE_LANGUAGE_OPTIONS:
            if option_code == normalized_code:
                return label
        return normalized_code

    def language_code_for_value(self, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            return ""
        for option_code, label in ARCHIVE_LANGUAGE_OPTIONS:
            if option_code == normalized_value or label.casefold() == normalized_value.casefold():
                return option_code
        return normalized_value

    def option_label_for_value(self, options: list[tuple[str, str]], value: str) -> str:
        normalized_value = value.strip()
        for option_value, label in options:
            if option_value == normalized_value:
                return label
        return normalized_value

    def option_value_for_input(self, options: list[tuple[str, str]], value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            return ""
        for option_value, label in options:
            if option_value == normalized_value or label.casefold() == normalized_value.casefold():
                return option_value
        return normalized_value

    def normalize_identifier_input(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            return ""

        if "://" in cleaned:
            parsed = urlparse(cleaned)
            path = parsed.path.strip("/")
            if path.startswith("details/"):
                cleaned = path[len("details/") :]
            else:
                cleaned = path.rsplit("/", 1)[-1]

        cleaned = unquote(cleaned)
        cleaned = cleaned.strip()
        cleaned = re.sub(r"\s+", "-", cleaned)
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", cleaned)
        cleaned = re.sub(r"-{2,}", "-", cleaned)
        return cleaned.strip("-")

    def generate_description(
        self,
        metadata: ProjectMetadata,
        files: list[FileItem] | None = None,
        title_pattern: str | None = None,
    ) -> str:
        lines: list[str] = []
        lines.append(self.format_display_title(metadata, title_pattern))

        developer = metadata.developer.strip()
        publisher = metadata.publisher.strip()
        if developer or publisher:
            lines.append("")
            if developer:
                lines.append(f"Developer: {developer}")
            if publisher:
                lines.append(f"Publisher: {publisher}")

        counts = self._content_counts(files or [])
        lines.append("")
        lines.append("Content:")
        lines.append("")
        lines.append(f"{counts['disk_images']} x Disk images")
        lines.append(f"{counts['disk_scans']} x Disk scans")
        lines.append(f"{counts['cover_images']} x Cover Images")
        lines.append(f"{counts['documents']} x Documents")
        lines.append(f"{counts['extras']} x Extras")
        lines.append(f"{counts['other_files']} x Other files")

        notes = metadata.notes.strip()
        if notes:
            lines.append("")
            lines.append("Notes:")
            lines.append("")
            lines.append(notes)

        lines.append("")
        lines.append("Prepared with Archive Goblin:")
        lines.append("https://github.com/rootifera/archive-goblin")

        return "\n".join(lines).strip()

    def _availability_from_payload(self, payload: object) -> IdentifierAvailability:
        if payload in ([], {}):
            return IdentifierAvailability(True, "This Archive.org identifier appears to be available.")
        if isinstance(payload, dict) and payload.get("metadata"):
            return IdentifierAvailability(False, "This Archive.org identifier already exists.")
        if isinstance(payload, dict) and payload.get("error"):
            return IdentifierAvailability(False, f"Archive.org returned an error: {payload['error']}")
        if isinstance(payload, dict) and any(
            key in payload
            for key in {"created", "updated", "files", "files_count", "d1", "d2", "dir", "server", "item_size", "uniq"}
        ):
            return IdentifierAvailability(False, "This Archive.org identifier already exists.")
        return IdentifierAvailability(False, "Archive.org returned an unexpected metadata response.")

    def _release_year(self, value: str) -> str:
        match = re.search(r"(19|20)\d{2}", value)
        return match.group(0) if match else ""

    def _content_counts(self, files: list[FileItem]) -> dict[str, int]:
        counts = {
            "disk_images": 0,
            "disk_scans": 0,
            "cover_images": 0,
            "documents": 0,
            "extras": 0,
            "other_files": 0,
        }
        disk_image_groups: set[str] = set()
        for file_item in files:
            file_type = file_item.type
            if file_item.is_cover_image_copy or file_type in {
                FileType.COVER_FRONT,
                FileType.COVER_BACK,
                FileType.COVER_OTHER,
            }:
                counts["cover_images"] += 1
            elif file_type is FileType.DISK_IMAGE:
                disk_image_groups.add(file_item.path.stem.casefold())
            elif file_type is FileType.MEDIA_SCAN:
                counts["disk_scans"] += 1
            elif file_type is FileType.DOCUMENT:
                counts["documents"] += 1
            elif file_type is FileType.EXTRA:
                counts["extras"] += 1
            elif file_type not in {FileType.IGNORE}:
                counts["other_files"] += 1
        counts["disk_images"] = len(disk_image_groups)
        return counts

    def _slugify(self, value: str) -> str:
        cleaned = value.strip().casefold().replace("_", "-")
        cleaned = re.sub(r"\s+", "-", cleaned)
        cleaned = re.sub(r"[^a-z0-9-]+", "-", cleaned)
        cleaned = re.sub(r"-{2,}", "-", cleaned)
        return cleaned.strip("-")

    def _add_tag(self, values: list[str], seen: set[str], tag: str) -> None:
        cleaned = tag.strip()
        if not cleaned:
            return
        lowered = cleaned.casefold()
        if lowered in seen:
            return
        seen.add(lowered)
        values.append(cleaned)


class _SafeFormatDict(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return ""
