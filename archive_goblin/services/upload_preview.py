from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from archive_goblin.models.file_item import FileItem, FileStatus
from archive_goblin.models.project_metadata import ProjectMetadata
from archive_goblin.services.archive_metadata import (
    ARCHIVE_COLLECTION_OPTIONS,
    ARCHIVE_LICENSE_OPTIONS,
    ArchiveMetadataService,
)


@dataclass(slots=True)
class UploadPreviewSummary:
    identifier: str
    page_url: str
    title: str
    collection_label: str
    license_label: str
    language_label: str
    effective_tags: list[str]
    description: str
    file_count: int
    total_size_bytes: int
    blocked_issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class UploadPreviewService:
    def __init__(self) -> None:
        self.archive_metadata_service = ArchiveMetadataService()

    def build_summary(
        self,
        folder: Path | None,
        files: list[FileItem],
        metadata: ProjectMetadata,
        title_pattern: str,
        page_url_pattern: str,
        default_tags: list[str],
        archive_access_key: str,
        archive_secret_key: str,
    ) -> UploadPreviewSummary:
        identifier = self.archive_metadata_service.build_identifier(page_url_pattern, metadata)
        page_url = self.archive_metadata_service.build_page_url(page_url_pattern, metadata)
        effective_tags = self.archive_metadata_service.effective_tags(metadata, default_tags)
        description = self.archive_metadata_service.generate_description(metadata, files, title_pattern)

        upload_files = [file_item for file_item in files if file_item.type.value != "ignore"]
        total_size_bytes = sum(self._safe_size(file_item.path) for file_item in upload_files)

        blocked_issues: list[str] = []
        warnings: list[str] = []

        if folder is None:
            blocked_issues.append("No folder is currently open.")
        if not metadata.title.strip():
            blocked_issues.append("Title cannot be blank.")
        if not metadata.platform.strip():
            blocked_issues.append("Platform cannot be blank.")
        if not metadata.collection.strip():
            blocked_issues.append("Collection must be selected.")
        if not identifier:
            blocked_issues.append("Archive.org identifier could not be generated.")
        if not archive_access_key.strip() or not archive_secret_key.strip():
            blocked_issues.append("Archive.org S3 credentials are not configured.")

        conflict_count = sum(1 for file_item in files if file_item.status is FileStatus.CONFLICT)
        unmatched_count = sum(1 for file_item in files if file_item.status is FileStatus.UNMATCHED)
        protected_count = sum(1 for file_item in files if file_item.status is FileStatus.PROTECTED)

        if conflict_count:
            blocked_issues.append(f"{conflict_count} file(s) still have naming conflicts.")
        if unmatched_count:
            warnings.append(f"{unmatched_count} file(s) are still unmatched.")
        if protected_count:
            warnings.append(f"{protected_count} protected file(s) will stay untouched unless explicitly overridden.")
        if not upload_files:
            blocked_issues.append("There are no files available for upload.")

        return UploadPreviewSummary(
            identifier=identifier,
            page_url=page_url,
            title=self.archive_metadata_service.format_display_title(metadata, title_pattern),
            collection_label=self.archive_metadata_service.option_label_for_value(
                ARCHIVE_COLLECTION_OPTIONS,
                metadata.collection,
            ),
            license_label=self.archive_metadata_service.option_label_for_value(
                ARCHIVE_LICENSE_OPTIONS,
                metadata.license,
            ) or "Leave license blank",
            language_label=self.archive_metadata_service.language_name_for_code(metadata.language),
            effective_tags=effective_tags,
            description=description,
            file_count=len(upload_files),
            total_size_bytes=total_size_bytes,
            blocked_issues=blocked_issues,
            warnings=warnings,
        )

    def _safe_size(self, path: Path) -> int:
        try:
            return path.stat().st_size
        except OSError:
            return 0
