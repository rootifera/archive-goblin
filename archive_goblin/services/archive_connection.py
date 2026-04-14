from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(slots=True)
class ArchiveConnectionResult:
    success: bool
    message: str


class ArchiveConnectionService:
    rate_limit_url = "https://archive.org/services/tasks.php"

    def test_credentials(self, access_key: str, secret_key: str) -> ArchiveConnectionResult:
        normalized_access_key = access_key.strip()
        normalized_secret_key = secret_key.strip()
        if not normalized_access_key or not normalized_secret_key:
            return ArchiveConnectionResult(False, "Enter both S3 credentials first.")

        query = urlencode({"rate_limits": "1", "cmd": "modify_xml.php"})
        request = Request(
            f"{self.rate_limit_url}?{query}",
            method="GET",
            headers={
                "Authorization": f"LOW {normalized_access_key}:{normalized_secret_key}",
                "Accept": "application/json",
                "User-Agent": "Archive Goblin",
            },
        )
        try:
            with urlopen(request, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code in {401, 403}:
                return ArchiveConnectionResult(False, "Archive.org rejected these credentials.")
            return ArchiveConnectionResult(False, f"Archive.org returned HTTP {exc.code}.")
        except URLError as exc:
            return ArchiveConnectionResult(False, f"Could not reach Archive.org: {exc.reason}")
        except json.JSONDecodeError:
            return ArchiveConnectionResult(False, "Archive.org returned an unexpected response.")

        if isinstance(payload, dict) and payload.get("success") is True:
            limits = payload.get("value", {})
            task_limit = limits.get("task_limits")
            tasks_inflight = limits.get("tasks_inflight")
            if isinstance(task_limit, int) and isinstance(tasks_inflight, int):
                return ArchiveConnectionResult(
                    True,
                    f"Connected successfully. Current modify_xml.php usage: {tasks_inflight}/{task_limit}.",
                )
            return ArchiveConnectionResult(True, "Connected successfully.")

        error_message = ""
        if isinstance(payload, dict):
            error_message = str(payload.get("error") or payload.get("message") or "").strip()
        if error_message:
            return ArchiveConnectionResult(False, f"Archive.org error: {error_message}")
        return ArchiveConnectionResult(False, "Archive.org could not confirm these credentials.")
