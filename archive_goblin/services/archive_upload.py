from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from archive_goblin.models.file_item import FileItem
from archive_goblin.models.project_metadata import ProjectMetadata
from archive_goblin.services.archive_metadata import ArchiveMetadataService
from archive_goblin.storage.project_store import ProjectStore


@dataclass(slots=True)
class ArchiveUploadResult:
    success: bool
    message: str


@dataclass(slots=True)
class ArchiveUploadPlan:
    identifier: str
    page_url: str
    file_paths: list[Path]
    metadata_payload: dict[str, object]
    access_key: str
    secret_key: str
    is_resume: bool = False
    existing_remote_names: list[str] | None = None


@dataclass(slots=True)
class ArchiveRecoveryDetails:
    identifier: str
    page_url: str
    remote_file_names: list[str]
    missing_file_paths: list[Path]


class ArchiveUploadService:
    def __init__(self) -> None:
        self.archive_metadata_service = ArchiveMetadataService()

    def prepare_upload(
        self,
        folder: Path | None,
        files: list[FileItem],
        metadata: ProjectMetadata,
        title_pattern: str,
        page_url_pattern: str,
        default_tags: list[str],
        access_key: str,
        secret_key: str,
    ) -> ArchiveUploadPlan | ArchiveUploadResult:
        if folder is None:
            return ArchiveUploadResult(False, "No folder is currently open.")

        identifier = self.archive_metadata_service.build_identifier(page_url_pattern, metadata)
        if not identifier:
            return ArchiveUploadResult(False, "Archive.org identifier could not be generated.")
        page_url = self.archive_metadata_service.build_page_url(page_url_pattern, metadata)

        file_paths = [
            file_item.path
            for file_item in files
            if file_item.type.value != "ignore" and file_item.path.name != ProjectStore.filename
        ]
        if not file_paths:
            return ArchiveUploadResult(False, "There are no files available for upload.")

        metadata_payload = self._build_metadata_payload(metadata, title_pattern, default_tags)
        availability = self.archive_metadata_service.check_identifier_availability(identifier)
        if availability.available:
            return ArchiveUploadPlan(
                identifier=identifier,
                page_url=page_url,
                file_paths=file_paths,
                metadata_payload=metadata_payload,
                access_key=access_key.strip(),
                secret_key=secret_key.strip(),
            )

        recovery = self.inspect_existing_upload(identifier, page_url, file_paths)
        if recovery is None:
            return ArchiveUploadResult(False, availability.message)
        if not recovery.missing_file_paths:
            return ArchiveUploadResult(
                False,
                "This Archive.org item already exists and all uploadable files are already present.",
            )

        return ArchiveUploadPlan(
            identifier=identifier,
            page_url=page_url,
            file_paths=recovery.missing_file_paths,
            metadata_payload=metadata_payload,
            access_key=access_key.strip(),
            secret_key=secret_key.strip(),
            is_resume=True,
            existing_remote_names=recovery.remote_file_names,
        )

    def upload_plan(self, plan: ArchiveUploadPlan, started_callback=None, finished_callback=None) -> ArchiveUploadResult:
        try:
            from internetarchive import upload
        except ImportError:
            return ArchiveUploadResult(False, "The internetarchive package is not installed.")

        completed = 0
        for index, file_path in enumerate(plan.file_paths):
            file_name = file_path.name
            metadata_payload = plan.metadata_payload if index == 0 else None
            if started_callback is not None:
                started_callback(index, file_name)
            try:
                responses = upload(
                    plan.identifier,
                    files=[str(file_path)],
                    metadata=metadata_payload,
                    access_key=plan.access_key,
                    secret_key=plan.secret_key,
                    verbose=False,
                )
            except Exception as exc:
                return ArchiveUploadResult(
                    False,
                    f"Upload failed while sending {file_name}: {exc}\n\n"
                    "Some files may already be uploaded. Automatic retry is disabled for now.",
                )

            response_list = list(responses) if responses is not None else []
            failures = [response for response in response_list if not getattr(response, "ok", True)]
            if failures:
                first_failure = failures[0]
                status_code = getattr(first_failure, "status_code", "unknown")
                return ArchiveUploadResult(
                    False,
                    f"Upload failed while sending {file_name} (status {status_code}).\n\n"
                    "Some files may already be uploaded. Automatic retry is disabled for now.",
                )

            completed += 1
            if finished_callback is not None:
                finished_callback(index, file_name, completed)

        if plan.is_resume:
            return ArchiveUploadResult(True, f"Resumed upload and sent {len(plan.file_paths)} missing file(s) to Archive.org.")
        return ArchiveUploadResult(True, f"Uploaded {len(plan.file_paths)} file(s) to Archive.org.")

    def inspect_existing_upload(
        self,
        identifier: str,
        page_url: str,
        local_file_paths: list[Path],
    ) -> ArchiveRecoveryDetails | None:
        try:
            remote_file_names = self.archive_metadata_service.fetch_item_file_names(identifier)
        except Exception:
            return None

        remote_name_set = {name.casefold() for name in remote_file_names}
        missing_file_paths = [
            path
            for path in local_file_paths
            if path.name.casefold() not in remote_name_set
        ]
        return ArchiveRecoveryDetails(
            identifier=identifier,
            page_url=page_url,
            remote_file_names=remote_file_names,
            missing_file_paths=missing_file_paths,
        )

    def _build_metadata_payload(self, metadata: ProjectMetadata, title_pattern: str, default_tags: list[str]) -> dict[str, object]:
        effective_tags = self.archive_metadata_service.effective_tags(metadata, default_tags)
        mediatype, collection = self._split_collection_value(metadata.collection)
        payload: dict[str, object] = {
            "title": self.archive_metadata_service.format_display_title(metadata, title_pattern),
            "mediatype": mediatype,
            "collection": collection,
            "description": metadata.description.strip(),
        }
        if metadata.date.strip():
            payload["date"] = metadata.date.strip()
        if metadata.publisher.strip():
            payload["publisher"] = metadata.publisher.strip()
        if metadata.developer.strip():
            payload["creator"] = metadata.developer.strip()
        if metadata.language.strip():
            payload["language"] = metadata.language.strip()
        if effective_tags:
            payload["subject"] = effective_tags
        if metadata.license.strip():
            payload["license"] = metadata.license.strip()
        return payload

    def _split_collection_value(self, value: str) -> tuple[str, str]:
        cleaned = value.strip()
        if ":" not in cleaned:
            return "", cleaned
        mediatype, collection = cleaned.split(":", 1)
        return mediatype.strip(), collection.strip()
