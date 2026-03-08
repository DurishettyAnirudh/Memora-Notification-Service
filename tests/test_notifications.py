"""Tests for notification microservice endpoints."""

from datetime import datetime, timedelta, timezone

import pytest


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_subscribe_requires_auth(client):
    res = client.post("/subscribe", json={"endpoint": "https://push.example.com", "p256dh": "key", "auth": "auth"})
    assert res.status_code == 422 or res.status_code == 401


def test_subscribe_success(client, auth_headers):
    res = client.post(
        "/subscribe",
        json={"endpoint": "https://push.example.com/sub1", "p256dh": "p256dh_key", "auth": "auth_key"},
        headers=auth_headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["id"] == 1
    assert data["endpoint"] == "https://push.example.com/sub1"


def test_subscribe_upsert(client, auth_headers):
    payload = {"endpoint": "https://push.example.com/sub2", "p256dh": "old_key", "auth": "old_auth"}
    res1 = client.post("/subscribe", json=payload, headers=auth_headers)
    sub_id = res1.json()["id"]

    payload["p256dh"] = "new_key"
    res2 = client.post("/subscribe", json=payload, headers=auth_headers)
    assert res2.status_code == 201
    assert res2.json()["id"] == sub_id  # same subscription updated


def test_schedule_notification(client, auth_headers):
    # Create subscription first
    sub = client.post(
        "/subscribe",
        json={"endpoint": "https://push.example.com/s", "p256dh": "k", "auth": "a"},
        headers=auth_headers,
    ).json()

    trigger = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    res = client.post(
        "/notify/schedule",
        json={
            "id": "reminder-001",
            "subscription_id": sub["id"],
            "title": "Take medication",
            "body": "Time for your evening meds",
            "trigger_at": trigger,
        },
        headers=auth_headers,
    )
    assert res.status_code == 201
    assert res.json()["id"] == "reminder-001"


def test_schedule_validates_title_length(client, auth_headers):
    sub = client.post(
        "/subscribe",
        json={"endpoint": "https://push.example.com/v", "p256dh": "k", "auth": "a"},
        headers=auth_headers,
    ).json()

    trigger = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    res = client.post(
        "/notify/schedule",
        json={
            "id": "t-001",
            "subscription_id": sub["id"],
            "title": "x" * 101,
            "body": "ok",
            "trigger_at": trigger,
        },
        headers=auth_headers,
    )
    assert res.status_code == 422


def test_cancel_notification(client, auth_headers):
    sub = client.post(
        "/subscribe",
        json={"endpoint": "https://push.example.com/c", "p256dh": "k", "auth": "a"},
        headers=auth_headers,
    ).json()

    trigger = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    client.post(
        "/notify/schedule",
        json={"id": "cancel-me", "subscription_id": sub["id"], "title": "Test", "body": "Test", "trigger_at": trigger},
        headers=auth_headers,
    )

    res = client.delete("/notify/cancel-me", headers=auth_headers)
    assert res.status_code == 204


def test_cancel_missing_returns_404(client, auth_headers):
    res = client.delete("/notify/nonexistent", headers=auth_headers)
    assert res.status_code == 404


def test_snooze_notification(client, auth_headers):
    sub = client.post(
        "/subscribe",
        json={"endpoint": "https://push.example.com/sn", "p256dh": "k", "auth": "a"},
        headers=auth_headers,
    ).json()

    trigger = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    client.post(
        "/notify/schedule",
        json={"id": "snooze-me", "subscription_id": sub["id"], "title": "Test", "body": "Test", "trigger_at": trigger},
        headers=auth_headers,
    )

    res = client.put("/notify/snooze-me/snooze", json={"snooze_minutes": 15}, headers=auth_headers)
    assert res.status_code == 200
    new_trigger = datetime.fromisoformat(res.json()["trigger_at"])
    assert new_trigger > datetime.now(timezone.utc)


def test_invalid_api_key_rejected(client):
    res = client.post(
        "/subscribe",
        json={"endpoint": "https://push.example.com/bad", "p256dh": "k", "auth": "a"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert res.status_code == 401
