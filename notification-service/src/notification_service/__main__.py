import uvicorn

from notification_service.settings import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run("notification_service.main:app", host=settings.app_host, port=settings.app_port)
