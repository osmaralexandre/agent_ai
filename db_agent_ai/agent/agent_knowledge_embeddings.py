from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import TEXT

from .. import Base


class AgentKnowledgeEmbeddings(Base):
    __tablename__ = "agent_knowledge_embeddings"
    __table_args__ = (
        UniqueConstraint("content_hash", name="embeddings_content_hash_key"),
        Index(
            "embeddings_embedding_idx",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        {"schema": "agent"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    application = Column(TEXT, nullable=True)
    file_name = Column(TEXT, nullable=True)
    content = Column(TEXT, nullable=True)
    embedding = Column(Vector(1536), nullable=True)
    content_hash = Column(TEXT, nullable=True)

    def __repr__(self):
        return f"<Embedding(id={self.id}, application={self.application}, file_name={self.file_name}, content_hash={self.content_hash})>"
