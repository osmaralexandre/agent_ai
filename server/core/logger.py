import os
from typing import Any, ClassVar, Dict

from pydantic import BaseModel

from .settings import base_settings


class LogConfig(BaseModel):
    """
    Configuração dos logs da aplicação.
    """

    LOGGER_NAME: str = base_settings.PROJECT_NAME
    LOG_FORMAT: str = "%(levelprefix)s | %(asctime)s | %(message)s"
    DEFAUT_LOG_FORMAT: str = "%(levelprefix)s | %(asctime)s | %(message)s"
    SIMPLE_LOG_FORMAT: str = "{levelname} {message}"
    LOG_LEVEL: str = "DEBUG"

    # Logging config
    version: ClassVar[int] = 1
    disable_existing_loggers: ClassVar[bool] = False
    formatters: ClassVar[Dict[str, Dict[str, str]]] = {
        "standard": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": DEFAUT_LOG_FORMAT,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {
            "format": SIMPLE_LOG_FORMAT,
            "style": "{",
        },
    }
    handlers: ClassVar[Dict[str, Dict[str, Any]]] = {
        "console": {
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "file": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": os.path.join(base_settings.BASE_DIR, "logs/error.log"),
            "formatter": "standard",
        },
    }
    loggers: ClassVar[Dict[str, Dict[str, Any]]] = {
        "root": {"handlers": ["console", "file"], "level": LOG_LEVEL},
    }

    def to_dict(self) -> Dict[str, Any]:
        """
        Converte a configuração do log para um dicionário e inclui o campo 'version'.
        """
        config_dict = self.dict()
        config_dict['version'] = self.version  # Adiciona o 'version' explicitamente
        return config_dict