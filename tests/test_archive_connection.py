from __future__ import annotations

import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from archive_goblin.services.archive_connection import ArchiveConnectionService


class _FakeResponse:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


class ArchiveConnectionServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = ArchiveConnectionService()

    def test_requires_both_credentials(self) -> None:
        result = self.service.test_credentials("", "")

        self.assertFalse(result.success)
        self.assertIn("Enter both", result.message)

    @patch("archive_goblin.services.archive_connection.urlopen")
    def test_reports_success_for_valid_authenticated_response(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _FakeResponse(
            {"success": True, "value": {"task_limits": 500, "tasks_inflight": 12}}
        )

        result = self.service.test_credentials("access", "secret")

        self.assertTrue(result.success)
        self.assertIn("12/500", result.message)

    @patch("archive_goblin.services.archive_connection.urlopen")
    def test_reports_auth_rejection(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = HTTPError(
            self.service.rate_limit_url,
            403,
            "Forbidden",
            hdrs=None,
            fp=None,
        )

        result = self.service.test_credentials("access", "secret")

        self.assertFalse(result.success)
        self.assertIn("rejected", result.message)


if __name__ == "__main__":
    unittest.main()
