"""Integration test verifying strict exception sanitization and zero leakage of internals."""

import pytest
from httpx import AsyncClient, ASGITransport
import sys
import os

# Add frontend to sys.path
sys.path.insert(0, os.path.abspath("frontend"))
from main import app


@pytest.mark.asyncio
async def test_error_sanitization_on_simulated_crash(monkeypatch):
    """Verify that any internal copilot exception produces sanitized user output.

    Must return:
      'EventOps couldn't complete that request. No event data was changed.'
    With request_id, and zero leakage of endpoints, 400s, tracebacks, or classes.
    """
    # Force _get_firestore to raise an unexpected runtime error
    def _exploding_firestore():
        raise RuntimeError("GCP Endpoint connection failure to https://us-central1-aiplatform.googleapis.com/v1/reasoningEngines/1788548626868338688: HTTPStatusError 400 Bad Request")

    monkeypatch.setattr("main._get_firestore", _exploding_firestore)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/chat",
            json={"message": "What am I forgetting?", "event_id": "evt_test"},
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["status"] == "error"
        assert "request_id" in data
        assert data["request_id"].startswith("req_")

        expected_msg = "EventOps couldn't complete that request. No event data was changed."
        assert data["structured"]["summary"] == expected_msg
        assert data["parts"][0]["text"] == expected_msg

        # Strict checks that zero internal data leaked
        raw_json = resp.text
        assert "RuntimeError" not in raw_json
        assert "HTTPStatusError" not in raw_json
        assert "400 Bad Request" not in raw_json
        assert "googleapis.com" not in raw_json
        assert "reasoningEngines" not in raw_json
        assert "Traceback" not in raw_json
