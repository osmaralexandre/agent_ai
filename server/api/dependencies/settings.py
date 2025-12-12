from fastapi import Depends

from server.core.settings import BaseAppSettings


class AppSettings(BaseAppSettings):
    pass


app_settings = None


@Depends
def get_app_settings() -> AppSettings:
    global app_settings
    if app_settings is None:
        app_settings = AppSettings()

    return app_settings
