import asyncio

from httpx import ASGITransport, AsyncClient

from notification_service.main import app
from notification_service.settings import get_settings


def get(path, headers=None):
    async def request():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            return await client.get(path, headers=headers)

    return asyncio.run(request())


def test_liveness_and_openapi():
    assert get("/health/live").json() == {"status": "ok"}
    paths = get("/openapi.json").json()["paths"]
    assert "/api/v1/notifications/{id}/deliveries" in paths


def test_service_authentication_precedes_access():
    path = "/api/v1/notifications"
    response = get(path, headers={"X-User-ID": "00000000-0000-0000-0000-000000000001"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    response = get(path, headers={
        "X-Service-Token": get_settings().internal_service_token.get_secret_value(),
        "X-User-ID": "invalid",
    })
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
