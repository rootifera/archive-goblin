from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from archive_goblin.services.archive_upload import ArchiveUploadPlan, ArchiveUploadService


class UploadWorker(QObject):
    started = Signal(list)
    file_started = Signal(int, str)
    file_finished = Signal(int, str, int)
    finished = Signal(object, str)

    def __init__(self, service: ArchiveUploadService, plan: ArchiveUploadPlan) -> None:
        super().__init__()
        self.service = service
        self.plan = plan

    def run(self) -> None:
        file_names = [path.name for path in self.plan.file_paths]
        self.started.emit(file_names)

        def progress(index: int, file_name: str, completed: int) -> None:
            self.file_started.emit(index, file_name)
            self.file_finished.emit(index, file_name, completed)

        result = self.service.upload_plan(self.plan, progress)
        self.finished.emit(result, self.plan.page_url)
