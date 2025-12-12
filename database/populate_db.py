import hashlib
import html
import json
import logging
import os
import re
from pathlib import Path
from typing import Optional

import numpy as np
import psycopg2
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from openai import OpenAI
from tqdm import tqdm

load_dotenv()

# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

# -------------------------------------------------------------------
# PostgreSQL configuration
# -------------------------------------------------------------------
DB_PARAMS = {
    "dbname": os.getenv("DB_DATABASE_LOCAL", "agent_ai"),
    "user": os.getenv("DB_USER_LOCAL", "postgres"),
    "password": os.getenv("DB_PASSWORD_LOCAL", "password"),
    "host": os.getenv("DB_HOST_LOCAL", "localhost"),
    "port": os.getenv("DB_PORT_LOCAL", "5432"),
}

SCHEMA_NAME = "agent"
TABLE_NAME = "agent_knowledge_embeddings"

# -------------------------------------------------------------------
# OpenAI
# -------------------------------------------------------------------
client = OpenAI()
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def prepare_text_for_embedding(
    text: str,
    lowercase: bool = False,
    strip_html: bool = True,
    collapse_spaces: bool = True,
) -> str:
    """
    Prepara texto bruto para geração de embeddings.
    
    Parâmetros
    ----------
    text : str
        Texto original.
    lowercase : bool
        Se deve converter tudo para minúsculas.
    strip_html : bool
        Remove tags HTML simples.
    collapse_spaces : bool
        Normaliza múltiplos espaços e quebras de linha.
    
    Retorna
    -------
    str : texto limpo, normalizado e pronto para embedding.
    """

    # 1. Remover caracteres invisíveis / unicode estranho
    text = text.replace("\u200b", "").replace("\ufeff", "")

    # 2. Decodificar entidades HTML (&nbsp;, &amp;, etc.)
    text = html.unescape(text)

    # 3. Remover HTML (simples)
    if strip_html:
        text = re.sub(r"<[^>]+>", " ", text)
        
    # 4. Remover múltiplas quebras de linha
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 5. Remover múltiplos espaços
    if collapse_spaces:
        text = re.sub(r"[ \t]{2,}", " ", text)

    # 6. Reformatar listas tipo "-   item" → "- item"
    text = re.sub(r"^-+\s+", "- ", text, flags=re.MULTILINE)

    # 7. Remover espaços no começo/fim das linhas
    text = "\n".join(line.strip() for line in text.splitlines())

    # 8. Remover linhas totalmente vazias duplicadas
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 9. Normalizar minúsculas (opcional)
    if lowercase:
        text = text.lower()

    # 10. Trim final
    return text.strip()


def calculate_hash(content: str) -> str:
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def is_content_processed(content_hash: str, cursor) -> bool:
    cursor.execute(
        f"""
        SELECT COUNT(*)
        FROM {SCHEMA_NAME}.{TABLE_NAME}
        WHERE content_hash = %s;
        """,
        (content_hash,),
    )
    return cursor.fetchone()[0] > 0


def insert_embedding_cursor(
    cursor,
    application: str,
    file_name: str,
    content: str,
    embedding: list[float],
    content_hash: str,
):
    """
    Insere os embeddings no banco usando um cursor existente.
    REMOVIDO: source_hash
    """

    embedding_str = f"[{', '.join(map(str, embedding))}]"

    cursor.execute(
        f"""
        INSERT INTO {SCHEMA_NAME}.{TABLE_NAME}
        (application, file_name, content, embedding, content_hash)
        VALUES (%s, %s, %s, %s::vector, %s)
        """,
        (application, file_name, content, embedding_str, content_hash),
    )


def load_config():
    config_path = Path("agent_ai/config/agent_config.json")
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def clean_text(text: str) -> str:
    """Remove o YAML header e espaços extras."""
    yaml_pattern = re.compile(r"---\s*.*?\s*---", re.DOTALL)
    return re.sub(yaml_pattern, "", text).strip()


# -------------------------------------------------------------------
# Text splitter
# -------------------------------------------------------------------
def chunk_markdown(content: str):
    """
    Usa RecursiveCharacterTextSplitter para quebrar o conteúdo em pedaços consistentes.
    """

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=100,
        separators=[
            "\n## ",
            "\n### ",
            "\n#### ",
            "\n##### ",
            "\n",
            " ",
            "",
        ],
        length_function=len,
    )

    return splitter.split_text(content)


# -------------------------------------------------------------------
# Main pipeline
# -------------------------------------------------------------------
def process_markdown_files():
    config = load_config()

    embedding_model_name = config.get("embeddings", {}).get(
        "model", DEFAULT_EMBEDDING_MODEL
    )
    embedding_dimensions = config.get("embeddings", {}).get(
        "dimensions", 1536
    )

    folder_path = "server/api/user_manual_tool/markdowns/eólica"

    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    logging.info("Conectado ao Postgres.")

    try:
        for file in os.listdir(folder_path):
            if not file.endswith(".md"):
                continue

            file_path = os.path.join(folder_path, file)
            logging.info(f"Processando arquivo: {file}")

            with open(file_path, "r", encoding="utf-8") as f:
                raw_content = f.read()

            clean_content = clean_text(raw_content)
            treated_content = prepare_text_for_embedding(clean_content)
            chunks = chunk_markdown(treated_content)

            logging.info(f"{len(chunks)} chunks gerados para {file}")

            base_name = Path(file).stem
            application = "user_manual"

            for idx, chunk in enumerate(
                tqdm(chunks, desc=f"Processando {base_name}")
            ):

                content_hash = calculate_hash(chunk)

                if is_content_processed(content_hash, cursor):
                    logging.info(f"Pulado (já existe): {base_name} idx={idx}")
                    continue

                # Cria embedding usando OpenAI
                try:
                    embedding_response = client.embeddings.create(
                        model=embedding_model_name,
                        input=chunk,
                        dimensions=embedding_dimensions,
                    )
                    embedding = embedding_response.data[0].embedding

                except Exception as e:
                    logging.error(f"Erro ao gerar embedding: {e}")
                    raise

                # Insere no banco
                try:
                    insert_embedding_cursor(
                        cursor=cursor,
                        application=application,
                        file_name=base_name,
                        content=chunk,
                        embedding=embedding,
                        content_hash=content_hash,
                    )
                except Exception as e:
                    logging.error(
                        f"Erro ao inserir embedding no banco: {base_name} idx={idx}"
                    )
                    logging.error(e)
                    raise

        conn.commit()
        logging.info("Commit realizado com sucesso.")

    except Exception as e:
        conn.rollback()
        logging.error("Rollback realizado devido a erro crítico.")
        logging.error(f"Erro no pipeline: {e}")
        raise

    finally:
        cursor.close()
        conn.close()
        logging.info("Conexão com PostgreSQL encerrada.")


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------
if __name__ == "__main__":
    process_markdown_files()
