from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, TIMESTAMP, Column, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import TEXT

from .. import Base


class LongTermMemory(Base):
    __tablename__ = "long_term_memory"
    __table_args__ = (
        Index(
            "long_termmemory_embedding_idx",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        {"schema": "agent"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    user_id = Column(TEXT, nullable=False)
    session_id = Column(TEXT, nullable=True)
    agent_name = Column(TEXT, nullable=True)
    role = Column(TEXT, nullable=True)
    message = Column(TEXT, nullable=True)
    embedding = Column(Vector(1536), nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    usage_info = Column(JSON, nullable=True)

    def __repr__(self):
        return (
            f"<LongTermMemory(id={self.id}, user_id={self.user_id}, "
            f"agent_name={self.agent_name}, session_id={self.session_id})>"
        )
