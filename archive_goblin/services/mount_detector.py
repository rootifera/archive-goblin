from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class MountDetails:
    mount_point: Path
    filesystem_type: str
    source: str
    is_network_share: bool
    is_smb_share: bool


class MountDetector:
    def detect(self, path: Path) -> MountDetails | None:
        if os.name != "posix":
            return None

        resolved_path = path.resolve()
        mount_info = self._read_mountinfo()
        best_match: tuple[Path, str, str] | None = None

        for mount_point, filesystem_type, source in mount_info:
            if resolved_path == mount_point or mount_point in resolved_path.parents:
                if best_match is None or len(str(mount_point)) > len(str(best_match[0])):
                    best_match = (mount_point, filesystem_type, source)

        if best_match is None:
            return None

        mount_point, filesystem_type, source = best_match
        is_smb_share = self._is_smb_path(resolved_path, filesystem_type, source)
        is_network_share = is_smb_share or filesystem_type in {
            "nfs",
            "nfs4",
            "sshfs",
            "fuse.sshfs",
            "davfs",
            "fuse.davfs",
        }
        return MountDetails(
            mount_point=mount_point,
            filesystem_type=filesystem_type,
            source=source,
            is_network_share=is_network_share,
            is_smb_share=is_smb_share,
        )

    def _read_mountinfo(self) -> list[tuple[Path, str, str]]:
        mountinfo_path = Path("/proc/self/mountinfo")
        if not mountinfo_path.exists():
            return []

        entries: list[tuple[Path, str, str]] = []
        for line in mountinfo_path.read_text(encoding="utf-8").splitlines():
            separator = " - "
            if separator not in line:
                continue
            left, right = line.split(separator, 1)
            left_parts = left.split()
            right_parts = right.split()
            if len(left_parts) < 5 or len(right_parts) < 2:
                continue

            mount_point = Path(left_parts[4].replace("\\040", " "))
            filesystem_type = right_parts[0]
            source = right_parts[1]
            entries.append((mount_point, filesystem_type, source))

        return entries

    def _is_smb_path(self, path: Path, filesystem_type: str, source: str) -> bool:
        if filesystem_type in {"cifs", "smb3"}:
            return True
        if "gvfs" in path.parts and "smb-share:" in str(path):
            return True
        if source.startswith("//"):
            return True
        return False
