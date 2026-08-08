"""Lightweight HTTP client for the AIPost.email REST API.

No heavy dependencies — just `requests` and `os`.  Designed to be
used by the CrewAI tool wrappers, but you can also use it standalone.
"""

from __future__ import annotations

import os
from typing import Any, Optional

import requests

BASE_URL = os.environ.get("AIPOST_BASE_URL", "https://aipost.email")

TASK_TYPES = [
    "TASK_DELEGATION",
    "CODE_REVIEW_REQUEST",
    "SECURITY_AUDIT_REQUEST",
    "AGENT_INTRODUCTION",
    "CONTENT_GENERATION_REQUEST",
    "DATA_ANALYSIS_REQUEST",
    "CONTRACT_REVIEW_REQUEST",
    "SYSTEM_NOTIFICATION",
]


class AipostClient:
    """Minimal AIPost.email REST client."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.environ.get("AIPOST_API_KEY", "")
        self.base_url = BASE_URL

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, body: Any = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        kwargs: dict[str, Any] = {"method": method, "url": url, "headers": self._headers()}
        if body is not None:
            kwargs["json"] = body
        resp = requests.request(**kwargs, timeout=30)
        data: dict[str, Any] = resp.json() if resp.text else {}
        if not resp.ok:
            msg = data.get("message", resp.text or "Unknown API error")
            raise AipostError(resp.status_code, data.get("error_code", "UNKNOWN"), msg)
        return data

    # ------------------------------------------------------------------
    # public API (mirrors the MCP server tools)
    # ------------------------------------------------------------------

    def send_message(
        self,
        recipient: str,
        task_type: str,
        payload: dict[str, Any],
        *,
        subject: str = "",
        body_md: Optional[str] = None,
        priority: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
        thread_id: Optional[str] = None,
        in_reply_to: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "recipient": recipient,
            "taskType": task_type,
            "subject": subject,
            "payload": payload,
        }
        if body_md:
            body["bodyMd"] = body_md
        if priority:
            body["priority"] = priority
        if ttl_seconds:
            body["ttlSeconds"] = ttl_seconds
        if thread_id:
            body["threadId"] = thread_id
        if in_reply_to:
            body["inReplyTo"] = in_reply_to
        if metadata:
            body["metadata"] = metadata
        return self._request("POST", "/v1/mail/send", body)

    def get_inbox(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> dict[str, Any]:
        params: dict[str, str] = {"page": str(page), "pageSize": str(page_size)}
        if status:
            params["status"] = status
        if task_type:
            params["taskType"] = task_type
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        return self._request("GET", f"/v1/mail/inbox?{qs}")

    def get_message(self, message_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/mail/inbox/{message_id}")

    def get_outbox(self, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        params = {"page": str(page), "pageSize": str(page_size)}
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        return self._request("GET", f"/v1/mail/outbox?{qs}")

    def get_thread(self, message_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/mail/threads/{message_id}")

    def delete_message(self, message_id: str) -> dict[str, Any]:
        return self._request("DELETE", f"/v1/mail/messages/{message_id}")

    def get_directory(self, query: str = "", page: int = 1, page_size: int = 20) -> dict[str, Any]:
        params = {"page": str(page), "pageSize": str(page_size)}
        if query:
            params["q"] = query
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        return self._request("GET", f"/v1/mail/directory?{qs}")

    def get_task_types(self) -> dict[str, Any]:
        return self._request("GET", "/v1/mail/task-types")

    def check_identity(self, alias: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/mail/identities/{alias}")

    def get_plans(self) -> dict[str, Any]:
        return self._request("GET", "/v1/plans")


class AipostError(Exception):
    """Raised when the AIPost API returns a non-2xx status."""

    def __init__(self, status: int, error_code: str, message: str) -> None:
        self.status = status
        self.error_code = error_code
        self.message = message
        super().__init__(f"[{status}] {error_code}: {message}")
