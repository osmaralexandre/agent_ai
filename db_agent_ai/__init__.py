# from sqlalchemy_extensions import custom_declarative_base
from sqlalchemy.orm import (
    declarative_base,
)
# Base = custom_declarative_base()
Base = declarative_base()
metadata = Base.metadata

# isort: off
from . import agent
from .agent.agent_knowledge_embeddings import AgentKnowledgeEmbeddings
from .agent.long_term_memory import LongTermMemory