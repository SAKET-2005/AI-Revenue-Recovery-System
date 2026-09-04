"""Tests for Webhooks (idempotency, signatures) and API endpoints."""

import pytest
import hashlib
import hmac
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings


@pytest.mark.asyncio
async def test_api_health_endpoint():
    """GET /api/health returns 200 and operational status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "ml_model_loaded" in data


@pytest.mark.asyncio
async def test_webhook_idempotency_and_duplicate_rejection(test_db):
    """Webhook processor must process first event and reject duplicates idempotently."""
    transport = ASGITransport(app=app)
    event_id = f"evt_test_{uuid.uuid4().hex[:8]}"

    payload = {
        "event_id": event_id,
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_123",
                    "amount": 450000,
                    "currency": "INR",
                    "status": "failed",
                }
            }
        },
    }

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # First request -> 200 OK
        resp1 = await ac.post("/api/webhooks/razorpay", json=payload)
        assert resp1.status_code == 200
        assert resp1.json()["status"] == "ok"

        # Duplicate request with same event_id -> handled as duplicate safely
        resp2 = await ac.post("/api/webhooks/razorpay", json=payload)
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "duplicate"


@pytest.mark.asyncio
async def test_generate_and_list_transactions(test_db):
    """Generate transactions via API and list them."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        gen_res = await ac.post("/api/transactions/generate", json={"count": 50})
        assert gen_res.status_code == 200
        assert gen_res.json()["total"] == 50

        list_res = await ac.get("/api/transactions?limit=10")
        assert list_res.status_code == 200
        data = list_res.json()
        assert len(data["transactions"]) == 10
        assert data["total"] == 50
