import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from loguru import logger
from openai import OpenAI
from redis import Redis, RedisError
from sqlalchemy import not_, select
from sqlalchemy.orm import Session

from db_agent_ai.agent.long_term_memory import LongTermMemory
from agent_ai.utils.constants import OPENAI_EMBEDDING_PRICES
from agent_ai.utils.read_files import FileUtils


# =============================================================================
# Short Term Memory
# =============================================================================
class MemoryProvider(ABC):

    @abstractmethod
    def add_message(self, role: str, message: str):
        """Store a new message in memory."""
        pass

    @abstractmethod
    def get_messages(self, agent_name: str) -> List[Dict[str, str]]:
        """Retrieve the latest stored messages."""
        pass


class ShortTermMemoryProvider(MemoryProvider):
    """
    Short-term memory implementation using Redis.

    This provider stores conversational messages in a Redis list with a TTL
    (time-to-live), enabling ephemeral session-based memory.

    Parameters
    ----------
    config_path : Path
        Path to the JSON configuration file.
    user_id : str
        Unique user identifier.
    session_id : str
        Session identifier.
    ttl_seconds : int, optional
        Time to live (expiration) for memory keys in Redis. Default is 600 seconds.

    Attributes
    ----------
    ttl : int
        Time-to-live for the Redis key.
    key : str
        Redis key for the memory list.
    config : dict
        Configuration loaded from JSON.
    memory_size : int
        Maximum number of messages to retrieve from memory.
    redis : Redis
        Redis connection instance created from URL.
    """

    VALID_ROLES = {"user", "assistant"}  # constant for validation

    def __init__(
        self,
        config_path: Path,
        user_id: str,
        session_id: str,
        ttl_seconds: int = 600,
    ):
        self.ttl = ttl_seconds
        self.key = f"user:{user_id}:session:{session_id}"
        self.config = FileUtils.read_json(config_path)

        try:
            self.memory_size: int = self.config["short_term_memory"][
                "memory_size"
            ]
            redis_url: str = self.config["short_term_memory"]["link"]
        except KeyError as exc:
            raise KeyError(f"Missing key in memory config: {exc}") from exc

        try:
            self.redis: Redis = Redis.from_url(
                redis_url, decode_responses=True
            )
        except RedisError as exc:
            raise ConnectionError(
                f"Failed to connect to Redis: {exc}"
            ) from exc

    def add_message(self, role: str, message: str):
        """
        Store a new message in Redis-based memory.

        Parameters
        ----------
        role : str
            Role of the sender ('user' or 'assistant').
        message : str
            Text content to store.

        Raises
        ------
        ValueError
            If the role is not valid.
        ConnectionError
            If Redis operation fails.
        """

        if role not in self.VALID_ROLES:
            raise ValueError(
                f"Invalid role '{role}'. Expected one of {self.VALID_ROLES}."
            )

        item = {
            "role": role,
            "content": message,
            "timestamp": datetime.now().isoformat(),
        }

        try:
            self.redis.rpush(self.key, json.dumps(item))
            self.redis.expire(self.key, self.ttl)
        except RedisError as exc:
            raise ConnectionError(f"Failed to write to Redis: {exc}") from exc

    def get_messages(self, agent_name: str) -> List[Dict[str, str]]:
        """
        Retrieve the last N messages stored in Redis.

        Parameters
        ----------
        agent_name : str
            Name of the agent requesting memory. (Currently unused.)

        Returns
        -------
        List[Dict[str, str]]
            Decoded list of memory entries.

        Raises
        ------
        ConnectionError
            If Redis read operation fails.
        """
        try:
            raw_items = self.redis.lrange(self.key, -self.memory_size, -1)
        except RedisError as exc:
            raise ConnectionError(f"Failed to read from Redis: {exc}") from exc

        messages: List[Dict[str, str]] = []
        for raw_item in raw_items:
            try:
                messages.append(json.loads(raw_item))
            except json.JSONDecodeError:
                continue  # skip corrupted entries

        return messages


# =============================================================================
# Long Term Memory
# =============================================================================
class LongTermMemoryProvider(MemoryProvider):
    """
    Long-term memory implementation using PostgreSQL.

    This provider stores conversational messages in a PostgreSQL database.

    Parameters
    ----------
    db_engine : Engine
        SQLAlchemy database engine instance.
    config_path : Path
        Path to the JSON configuration file.
    user_id : str
        Unique user identifier.
    session_id : str
        Session identifier.

    Attributes
    ----------
    config : dict
        Configuration loaded from JSON.
    rag_search_k : int
        Maximum number of messages to retrieve from memory.
    embedding_model_name : str
        Name of the embedding model to use.
    embedding_dimensions : int
        Dimensions of the embedding vector.
    db_engine : Engine
        SQLAlchemy database engine instance.
    client : OpenAI
        OpenAI client instance.
    """

    def __init__(
        self,
        db_engine,
        config_path: Path,
        user_id: str,
        session_id: str,
    ):
        self.user_id = user_id
        self.session_id = session_id
        self.config = FileUtils.read_json(config_path)
        self.rag_search_k = self.config["long_term_memory"]["rag_search_k"]
        self.embedding_model_name = self.config["embeddings"]["model"]
        self.embedding_dimensions = self.config["embeddings"]["dimensions"]
        self._engine = db_engine
        self.client = OpenAI()

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

        embedding_response = self.client.embeddings.create(
            model=self.embedding_model_name,
            input=query,
            dimensions=self.embedding_dimensions,
        )

        embedding = embedding_response.data[0].embedding
        total_tokens = embedding_response.usage.total_tokens
        cost_usd = self._compute_cost(self.embedding_model_name, total_tokens)

        cost_info = {
            "tokens_prompt": total_tokens,
            "tokens_completion": 0,
            "tokens_total": total_tokens,
            "cost_usd": cost_usd,
        }

        return embedding, cost_info

    def add_message(self, agent_name: str, role: str, result: Dict[str, Any]):
        """
        Store a message and its embedding in long-term memory.

        Parameters
        ----------
        agent_name : str
            Name of the agent that generated the message.
        role : str
            Role of the message author (e.g., 'assistant', 'user').
        result : dict
            Dictionary containing the message data. Must include:
            - ``response`` : str
                The message text.
            - Additional token and cost information (optional).

        Returns
        -------
        dict
            A dictionary containing:
            - ``response`` : str
            - ``tokens_prompt`` : int
            - ``tokens_completion`` : int
            - ``tokens_total`` : int
            - ``cost_usd`` : float
                Total aggregated cost from the embedding + input result.

        Notes
        -----
        This method:
        1. Generates an embedding for the message.
        2. Aggregates usage statistics (tokens, costs).
        3. Stores the record in database via SQLAlchemy.
        """

        # Generate embedding
        embedding, cost_info = self._embed_query(result["response"])

        logger.info(
            f"Add {role.capitalize()} Long Term Memory Result: {cost_info}"
        )

        # Combine cost dictionaries (input + embedding)
        cost_results_dicts = [
            result,
            cost_info,
        ]

        total_cost = {
            k: sum(d[k] for d in cost_results_dicts)
            for k in (
                "tokens_prompt",
                "tokens_completion",
                "tokens_total",
                "cost_usd",
            )
        }

        updated_result = {
            "response": result["response"],
            **total_cost,
        }

        usage_info = {
            **{k: v for k, v in updated_result.items() if k != "response"},
        }

        # Persist in database
        with Session(self._engine) as session:
            record = LongTermMemory(
                user_id=self.user_id,
                session_id=self.session_id,
                agent_name=agent_name,
                role=role,
                message=result["response"],
                embedding=embedding,
                usage_info=usage_info,
            )

            session.add(record)
            session.commit()
            session.refresh(record)

        return updated_result

    def get_messages(self, query: str, top_n: int = 5) -> List[Dict[str, str]]:
        """
        Retrieve the most similar messages from long-term memory using cosine similarity.

        Parameters
        ----------
        query : str
            Input text used to generate the embedding for similarity search.
        top_n : int, optional
            Number of most similar messages to return. Default is 5.

        Returns
        -------
        list of dict
            A list of dictionaries, each containing:
            - ``id`` : int
            - ``user_id`` : str
            - ``session_id`` : str
            - ``agent_name`` : str
            - ``role`` : str
            - ``message`` : str
            - ``score`` : float
            Cosine similarity between query and stored message.

        Notes
        -----
        Performs a vector similarity search via ``embedding.cosine_distance`` using pgvector.
        """

        # Generate embedding
        query_embedding, long_term_memory_embedding_cost = self._embed_query(
            query
        )

        # logger.info(
        #     f"Query Embedding to Get Long Term Memory Result: {long_term_memory_embedding_cost}"
        # )

        # Perform vector search in the database
        with Session(self._engine) as session:
            stmt = (
                select(
                    LongTermMemory.id,
                    LongTermMemory.user_id,
                    LongTermMemory.session_id,
                    LongTermMemory.agent_name,
                    LongTermMemory.role,
                    LongTermMemory.message,
                    (
                        1
                        - LongTermMemory.embedding.cosine_distance(
                            query_embedding
                        )
                    ).label("cosine_similarity"),
                )
                .where(LongTermMemory.user_id == self.user_id)
                .order_by(
                    (
                        1
                        - LongTermMemory.embedding.cosine_distance(
                            query_embedding
                        )
                    ).desc()
                )
                .limit(top_n)
            )

            rows = session.execute(stmt).all()

        similar_messages = [
            {
                "id": row.id,
                "user_id": row.user_id,
                "session_id": row.session_id,
                "agent_name": row.agent_name,
                "role": row.role,
                "message": row.message,
                "score": row.cosine_similarity,
            }
            for row in rows
        ]

        return similar_messages, long_term_memory_embedding_cost
