from functools import cache
from os import getenv

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


@cache
def get_meta_url():
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    url = URL.create(
        query={"application_name": "Assets DB"},
        drivername="postgresql+psycopg2",
        host=getenv("DB_HOST", "localhost"),
        port=getenv("DB_PORT", 5435),
        database=getenv("DB_DATABASE", "postgres"),
        username=getenv("DB_USER", "postgres"),
        password=getenv("DB_PASSWORD", "postgres"),
    )

    return url


@cache
def get_meta_engine():
    meta_engine = create_engine(get_meta_url())
    return meta_engine

def get_localhost():
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    url = URL.create(
        query={"application_name": "Assets DB"},
        drivername="postgresql+psycopg2",
        host=getenv("DB_HOST_LOCAL", "localhost"),
        port=getenv("DB_PORT_LOCAL", 5432),
        database=getenv("DB_DATABASE_LOCAL", "agent_ai"),
        username=getenv("DB_USER_LOCAL", "postgres"),
        password=getenv("DB_PASSWORD_LOCAL", "password"),
    )

    return url

def get_db_url(client_tag="localhost"):
    if client_tag == "localhost":
        return get_localhost()
    else:
        query = text(
            """
            SELECT con_database AS database
            FROM manage.client
            WHERE tag = :client_tag
        """
        ).bindparams(client_tag=client_tag)

        meta_engine = get_meta_engine()
        with meta_engine.connect() as connection:
            result = connection.execute(query)
            row = next(result)
            db = row["database"]

    return URL.create(
        query={"application_name": "Assets DB"},
        drivername="postgresql+psycopg2",
        host=db["host"],
        port=db["port"],
        database=db["database"],
        username=db["user"],
        password=db["password"],
    )


if __name__ == "__main__":
    from sys import argv

    print(get_db_url(argv[1]))  # noqa: T201
