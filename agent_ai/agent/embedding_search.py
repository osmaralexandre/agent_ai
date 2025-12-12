from pathlib import Path
from typing import Any, Dict, List, Tuple

from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from db_agent_ai.agent.agent_knowledge_embeddings import AgentKnowledgeEmbeddings
from agent_ai.utils.constants import OPENAI_EMBEDDING_PRICES
from agent_ai.utils.read_files import FileUtils


# =============================================================================
# Embedding Search
# =============================================================================
class EmbeddingSearch:
    """
    Infrastructure component responsible for generating embeddings using the
    OpenAI API and performing similarity search in a database.

    Parameters
    ----------
    db_engine : sqlalchemy.Engine
        SQLAlchemy engine connected to the database.
    model : str, optional
        Embedding model name used by OpenAI. Default is "text-embedding-3-small".

    Attributes
    ----------
    _engine : sqlalchemy.Engine
        SQLAlchemy engine for DB operations.
    _model : str
        OpenAI embedding model used for inference.
    _client : OpenAI
        OpenAI client object to call embedding APIs.
    """

    def __init__(self, db_engine, config_path: Path,):
        self._engine = db_engine
        self._config = FileUtils.read_json(config_path)
        self._model = self._config["embeddings"]["model"]
        self._dimensions = self._config["embeddings"]["dimensions"]
        self._client = OpenAI()

    # -------------------------------------------------------------------------
    # Cost Calculation
    # -------------------------------------------------------------------------
    def _compute_cost(self, model: str, total_tokens: int) -> float:
        """
        Compute the cost (USD) for an embedding request based on token usage.

        Parameters
        ----------
        model : str
            The embedding model used.
        total_tokens : int
            Total tokens consumed for the embedding request.

        Returns
        -------
        float
            Cost in USD. Returns 0.0 if pricing for this model is not defined.
        """
        price_per_mtoken = OPENAI_EMBEDDING_PRICES.get(model)
        if price_per_mtoken is None:
            return 0.0
        return (total_tokens / 1_000_000) * price_per_mtoken

    # -------------------------------------------------------------------------
    # Embedding Generation
    # -------------------------------------------------------------------------
    def _embed_query(self, query: str) -> Tuple[List[float], Dict[str, Any]]:
        """
        Generate an embedding vector using the OpenAI API.

        Parameters
        ----------
        query : str
            Input text to embed.

        Returns
        -------
        tuple
            A tuple containing:
            - embedding : list of float
                Vector of embedding values.
            - cost_info : dict
                Dictionary with token usage and cost details.

        Notes
        -----
        Embeddings consume only prompt tokens (no completion).
        """

        embedding_response = self._client.embeddings.create(
            model=self._model,
            input=query,
            dimensions=self._dimensions,
        )

        embedding = embedding_response.data[0].embedding
        total_tokens = embedding_response.usage.total_tokens
        cost_usd = self._compute_cost(self._model, total_tokens)

        cost_info = {
            "tokens_prompt": total_tokens,
            "tokens_completion": 0,
            "tokens_total": total_tokens,
            "cost_usd": cost_usd,
        }

        return embedding, cost_info

    # -------------------------------------------------------------------------
    # Vector Search in Database
    # -------------------------------------------------------------------------
    def get_similar_embeddings(
        self, query: str, top_n: int = 5
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Generate a query embedding and perform a similarity search in the database.

        Parameters
        ----------
        query : str
            Input query text for which embeddings will be generated.
        top_n : int, optional
            Number of similar documents to retrieve. Default is 5.

        Returns
        -------
        tuple
            A tuple containing:
            - results : list of dict
                List of search results sorted by cosine similarity.
                Each dict contains: id, file_name, application, content, score.
            - embedding_cost : dict
                Cost information from the embedding generation.

        Notes
        -----
        Cosine similarity is computed as `1 - cosine_distance`.
        """

        # Generate embedding
        query_embedding, embedding_cost = self._embed_query(query)

        # Perform vector search in the database
        with Session(self._engine) as session:
            stmt = (
                select(
                    AgentKnowledgeEmbeddings.id,
                    AgentKnowledgeEmbeddings.file_name,
                    AgentKnowledgeEmbeddings.application,
                    AgentKnowledgeEmbeddings.content,
                    (
                        1
                        - AgentKnowledgeEmbeddings.embedding.cosine_distance(query_embedding)
                    ).label("cosine_similarity"),
                )
                .order_by(
                    (
                        1
                        - AgentKnowledgeEmbeddings.embedding.cosine_distance(query_embedding)
                    ).desc()
                )
                .limit(top_n)
            )

            rows = session.execute(stmt).all()

        similar_docs = [
            {
                "id": row.id,
                "file_name": row.file_name,
                "application": row.application,
                "content": row.content,
                "score": row.cosine_similarity,
            }
            for row in rows
        ]

        return similar_docs, embedding_cost,
