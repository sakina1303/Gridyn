"""Authenticated, owner-scoped object storage for the public research workspace.

Supabase Row Level Security is the final access boundary. Every request uses the
visitor's access token; no service-role key is present in the application.
"""

from __future__ import annotations

import json
from contextvars import ContextVar
from datetime import datetime, timezone

import httpx


access_token: ContextVar[str | None] = ContextVar("gridyn_access_token", default=None)


class HostedStoreError(RuntimeError):
    pass


class HostedStore:
    def __init__(self, url: str, publishable_key: str, *, client: httpx.Client | None = None) -> None:
        self.url = url.rstrip("/")
        self.publishable_key = publishable_key
        self.client = client or httpx.Client(timeout=20)

    def _headers(self, *, write: bool = False) -> dict[str, str]:
        token = access_token.get()
        if not token:
            raise HostedStoreError("Authentication is required")
        headers = {"apikey": self.publishable_key, "Authorization": f"Bearer {token}"}
        if write:
            headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
            headers["Content-Type"] = "application/json"
        return headers

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        try:
            return self.client.request(method, f"{self.url}{path}", **kwargs)
        except httpx.HTTPError as exc:
            raise HostedStoreError("Hosted storage is unavailable") from exc

    def _read(self, params: dict[str, str]) -> list[dict]:
        response = self._request("GET", "/rest/v1/gridyn_objects",
                                 headers=self._headers(), params=params)
        if response.status_code != 200:
            raise HostedStoreError(f"Storage read failed ({response.status_code})")
        return response.json()

    def put(self, kind: str, object_id: str, payload: dict) -> None:
        # PostgreSQL fills owner_id from auth.uid(); clients cannot choose one.
        canonical = json.loads(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False))
        row = {"kind": kind, "id": object_id, "payload": canonical,
               "created_at_utc": datetime.now(timezone.utc).isoformat()}
        response = self._request("POST", "/rest/v1/gridyn_objects",
                                 headers=self._headers(write=True), json=row)
        if response.status_code not in (200, 201, 204):
            raise HostedStoreError(f"Storage write failed ({response.status_code})")

    def get(self, kind: str, object_id: str) -> dict | None:
        rows = self._read({"select": "payload", "kind": f"eq.{kind}", "id": f"eq.{object_id}", "limit": "1"})
        return None if not rows else rows[0]["payload"]

    def list(self, kind: str) -> tuple[dict, ...]:
        rows = self._read({"select": "payload", "kind": f"eq.{kind}", "order": "created_at_utc.asc"})
        return tuple(row["payload"] for row in rows)

    def delete(self, kind: str, object_id: str) -> None:
        response = self._request("DELETE", "/rest/v1/gridyn_objects",
                                 headers=self._headers(),
                                 params={"kind": f"eq.{kind}", "id": f"eq.{object_id}"})
        if response.status_code not in (200, 204):
            raise HostedStoreError(f"Storage delete failed ({response.status_code})")

    def authenticate(self, token: str) -> bool:
        response = self._request("GET", "/auth/v1/user",
                                 headers={"apikey": self.publishable_key,
                                          "Authorization": f"Bearer {token}"})
        if response.status_code >= 500:
            raise HostedStoreError("Hosted authentication is unavailable")
        return response.status_code == 200 and bool(response.json().get("id"))
