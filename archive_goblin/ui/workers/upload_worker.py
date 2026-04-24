from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from archive_goblin.services.archive_upload import ArchiveUploadPlan, ArchiveUploadService


class UploadWorker(QObject):
    started = Signal(list)
    file_started = Signal(int, str)
    file_progress = Signal(int, str, object, object, float)
    file_finished = Signal(int, str, int)
    finished = Signal(object, str)

    def __init__(self, service: ArchiveUploadService, plan: ArchiveUploadPlan) -> None:
        super().__init__()
        self.service = service
        self.plan = plan

    def run(self) -> None:
        file_names = [path.name for path in self.plan.file_paths]
        self.started.emit(file_names)

        def on_started(index: int, file_name: str) -> None:
            self.file_started.emit(index, file_name)

        def on_finished(index: int, file_name: str, completed: int) -> None:
            self.file_finished.emit(index, file_name, completed)

        def on_progress(
            index: int,
            file_name: str,
            bytes_sent: int,
            total_bytes: int,
            bytes_per_second: float,
        ) -> None:
            self.file_progress.emit(index, file_name, bytes_sent, total_bytes, bytes_per_second)

        result = self.service.upload_plan(self.plan, on_started, on_finished, on_progress)
        self.finished.emit(result, self.plan.page_url)
