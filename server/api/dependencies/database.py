from __future__ import annotations

from abc import abstractmethod
from functools import cache
from os import getenv
from typing import Iterator, cast
from urllib.parse import quote_plus

from fastapi import Depends, Header
from pydantic import PostgresDsn
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.sql.elements import TextClause

from server.api.dependencies.settings import AppSettings, get_app_settings
from server.utils.singleton import AbstractSingleton

DEBUG: bool = bool(getenv("DEBUG", None))


class BaseMetaDAO(AbstractSingleton):
    @abstractmethod
    def get_sessionmaker(self, client_hash: str) -> sessionmaker[Session]:
        pass

    @abstractmethod
    def get_sessionmaker_from_tag(
        self, client_tag: str
    ) -> sessionmaker[Session]:
        pass


class MetaDAO(BaseMetaDAO):
    def __init__(self, settings: AppSettings):
        """Returns singleton engine for access to meta Database."""
        url = cast(str, settings.SQLALCHEMY_DATABASE_URI)
        self.engine = create_engine(
            url,
            pool_pre_ping=True,
            poolclass=NullPool,
        )

    def get_sessionmaker(self, client_hash: str) -> sessionmaker[Session]:
        url = self._get_db_url(client_hash)
        return self._get_sessionmaker_from_url(url)

    def get_sessionmaker_from_tag(
        self, client_tag: str
    ) -> sessionmaker[Session]:
        url = self._get_db_url_from_tag(client_tag)
        return self._get_sessionmaker_from_url(url)

    @cache
    def _get_sessionmaker_from_url(self, url: str) -> sessionmaker[Session]:
        engine = self._get_engine(url)
        return sessionmaker(autocommit=False, autoflush=False, bind=engine)

    @cache
    def _get_engine(self, url: str) -> Engine:
        engine = create_engine(url, pool_pre_ping=True)
        return engine

    @cache
    def _get_db_url(self, client_hash: str) -> str:
        query = text(
            """
            SELECT con_database AS database
            FROM manage.client
            WHERE hash = :client_hash
        """
        ).bindparams(client_hash=client_hash)

        return self._build_client_db_url(query)

    @cache
    def _get_db_url_from_tag(self, client_tag: str) -> str:
        query = text(
            """
            SELECT con_database AS database
            FROM manage.client
            WHERE tag = :client_tag
        """
        ).bindparams(client_tag=client_tag)

        return self._build_client_db_url(query)

    def _build_client_db_url(self, query: TextClause) -> PostgresDsn:
        with self.engine.connect() as connection:
            result = connection.execute(query)
            row = next(result)
            db = row["database"]

        return PostgresDsn.build(
            scheme="postgresql+psycopg2",
            user=db["user"],
            password=quote_plus(db["password"]),
            host=db["host"],
            path=f"/{db['database'] or ''}",
            port=str(db["port"]),
        )


@Depends
def get_meta_dao(settings: AppSettings = get_app_settings) -> MetaDAO:
    return MetaDAO(settings)


@Depends
def get_session(
    client_hash: str = Header(...),
    meta_dao: MetaDAO = get_meta_dao,
) -> Iterator[Session]:
    with meta_dao.get_sessionmaker(client_hash).begin() as session:
        yield session

