"""Public-workspace access stays scoped to the authenticated visitor."""

import importlib
import os
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from energy_lab.db.hosted import HostedStore, HostedStoreError, access_token


class FakeHostedStore:
    def __init__(self):
        self.rows = {}

    def authenticate(self, token):
        if token == "unavailable":
            raise HostedStoreError("Auth service unavailable")
        return token in {"visitor-one", "visitor-two"}

    def put(self, kind, object_id, payload):
        self.rows[(access_token.get(), kind, object_id)] = payload

    def get(self, kind, object_id):
        return self.rows.get((access_token.get(), kind, object_id))

    def list(self, kind):
        return tuple(value for (owner, row_kind, _), value in self.rows.items()
                     if owner == access_token.get() and row_kind == kind)

    def delete(self, kind, object_id):
        self.rows.pop((access_token.get(), kind, object_id), None)


class HostedAccessTests(unittest.TestCase):
    def test_authentication_and_owner_isolation(self):
        module = importlib.import_module("energy_lab.api.app")
        store = FakeHostedStore()
        env = {"GRIDYN_SUPABASE_URL": "https://example.supabase.co",
               "GRIDYN_SUPABASE_PUBLISHABLE_KEY": "public-key",
               "GRIDYN_FRONTEND_ORIGIN": "https://gridyn.vercel.app"}
        with patch.dict(os.environ, env), patch.object(module, "HostedStore", return_value=store):
            client = TestClient(module.create_app())
            self.assertEqual(client.get("/v1/health").status_code, 200)
            preflight = client.options("/v1/sites", headers={"Origin": "https://gridyn.vercel.app",
                "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "authorization,content-type"})
            self.assertEqual(preflight.headers.get("access-control-allow-origin"), "https://gridyn.vercel.app")
            self.assertEqual(client.get("/v1/sites").status_code, 401)
            self.assertEqual(client.get("/v1/sites", headers={"Authorization": "Bearer unavailable"}).status_code, 503)
            first = {"Authorization": "Bearer visitor-one"}
            second = {"Authorization": "Bearer visitor-two"}
            site = client.post("/v1/sites", headers=first, json={
                "name": "Synthetic test", "timezone": "Asia/Kolkata",
                "grid": {"import_limit_kw": 50, "export_limit_kw": 0},
                "pv": {"ac_capacity_kw": 0},
            })
            self.assertEqual(site.status_code, 201, site.text)
            site_id = site.json()["site_id"]
            dataset = client.post(f"/v1/sites/{site_id}/synthetic-datasets", headers=first, json={
                "start_utc": "2026-01-01T00:00:00Z", "interval_count": 4,
            })
            self.assertEqual(dataset.status_code, 201, dataset.text)
            dataset_id = dataset.json()["dataset_id"]
            self.assertEqual(len(client.get("/v1/sites", headers=first).json()["sites"]), 1)
            self.assertEqual(client.get("/v1/sites", headers=second).json()["sites"], [])
            self.assertEqual(len(client.get(f"/v1/sites/{site_id}/datasets", headers=first).json()["datasets"]), 1)
            self.assertEqual(client.get(f"/v1/sites/{site_id}/datasets", headers=second).status_code, 404)
            self.assertEqual(client.get(f"/v1/datasets/{dataset_id}", headers=second).status_code, 404)
            self.assertEqual(client.get(f"/v1/sites/{site_id}", headers=second).status_code, 404)
            self.assertEqual(client.get(f"/v1/sites/{site_id}", headers=first).status_code, 200)
            self.assertEqual(client.delete(f"/v1/sites/{site_id}", headers=second).status_code, 404)
            self.assertEqual(client.delete(f"/v1/sites/{site_id}", headers=first).status_code, 204)
            self.assertEqual(client.get(f"/v1/sites/{site_id}", headers=first).status_code, 404)
            self.assertEqual(client.get(f"/v1/datasets/{dataset_id}", headers=first).status_code, 404)

    def test_hosted_store_uses_visitors_jwt(self):
        requests = []

        def respond(request):
            requests.append(request)
            if request.url.path.endswith("/auth/v1/user"):
                return httpx.Response(200, json={"id": "user-id"})
            if request.method == "POST":
                return httpx.Response(201)
            return httpx.Response(200, json=[{"payload": {"site_id": "example"}}])

        client = httpx.Client(transport=httpx.MockTransport(respond))
        store = HostedStore("https://example.supabase.co", "public-key", client=client)
        context = access_token.set("visitor-token")
        try:
            self.assertTrue(store.authenticate("visitor-token"))
            store.put("site", "10000000-0000-4000-8000-000000000000", {"site_id": "example"})
            self.assertEqual(store.get("site", "10000000-0000-4000-8000-000000000000"),
                             {"site_id": "example"})
            self.assertEqual(store.list("site"), ({"site_id": "example"},))
        finally:
            access_token.reset(context)
        self.assertTrue(all(request.headers["Authorization"] == "Bearer visitor-token"
                            for request in requests))
        self.assertTrue(all(request.headers["apikey"] == "public-key" for request in requests))


if __name__ == "__main__":
    unittest.main()
