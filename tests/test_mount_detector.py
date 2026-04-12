from __future__ import annotations

import unittest
from pathlib import Path

from archive_goblin.services.mount_detector import MountDetector


class MountDetectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.detector = MountDetector()

    def test_detects_cifs_mount(self) -> None:
        self.detector._read_mountinfo = lambda: [  # type: ignore[method-assign]
            (Path("/"), "ext4", "/dev/nvme0n1p2"),
            (Path("/mnt/nas/share"), "cifs", "//192.168.1.90/share"),
        ]

        details = self.detector.detect(Path("/mnt/nas/share/folder"))

        self.assertIsNotNone(details)
        assert details is not None
        self.assertTrue(details.is_smb_share)
        self.assertTrue(details.is_network_share)

    def test_detects_gvfs_smb_path(self) -> None:
        self.detector._read_mountinfo = lambda: [  # type: ignore[method-assign]
            (Path("/run/user/1000/gvfs"), "fuse.gvfsd-fuse", "gvfsd-fuse"),
        ]

        details = self.detector.detect(
            Path("/run/user/1000/gvfs/smb-share:server=nas.local,share=share/folder")
        )

        self.assertIsNotNone(details)
        assert details is not None
        self.assertTrue(details.is_smb_share)

    def test_non_network_mount_is_not_flagged(self) -> None:
        self.detector._read_mountinfo = lambda: [  # type: ignore[method-assign]
            (Path("/"), "ext4", "/dev/nvme0n1p2"),
        ]

        details = self.detector.detect(Path("/home/omur/projects"))

        self.assertIsNotNone(details)
        assert details is not None
        self.assertFalse(details.is_network_share)
        self.assertFalse(details.is_smb_share)


if __name__ == "__main__":
    unittest.main()
