import secrets
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Union

from pydantic import PostgresDsn, validator
from pydantic_settings import BaseSettings

try:
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv())

except ModuleNotFoundError:
    pass


class BaseAppSettings(BaseSettings):
    """
    Configurações base da aplicação, que devem ser utilizadas tanto
    em produção quanto em testes de integração.
    """

    BASE_DIR: ClassVar[Path] = Path(__file__).resolve().parent.parent.parent
    PROJECT_NAME: str = "Template API"
    DESCRIPTION: str = "Template API"
    VERSION: str = "0.0.0"
    ROUTE_V1: str = "/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # BACKEND_CORS_ORIGINS is a JSON-formatted list of origins
    # e.g: '["http://localhost", "http://localhost:4200",
    # "http://localhost:3000", "http://localhost:8080"
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(
        cls, v: Union[str, List[str]]
    ) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: Optional[str] = None
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_DATABASE: Optional[str] = None

    SQLALCHEMY_DATABASE_URI: Optional[PostgresDsn] = None

    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    def assemble_db_connection(
        cls, v: Optional[str], values: Dict[str, Any]
    ) -> Any:
        if isinstance(v, str):
            return v
        return (
            f"postgresql+psycopg2://{values.get('DB_USER')}:{values.get('DB_PASSWORD')}"
            f"@{values.get('DB_HOST')}:{values.get('DB_PORT')}/{values.get('DB_DATABASE') or ''}"
        )

    class Config:
        case_sensitive = True


base_settings = BaseAppSettings()
