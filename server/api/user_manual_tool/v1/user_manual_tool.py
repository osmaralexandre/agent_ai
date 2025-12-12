import os
import sys

from fastapi import APIRouter, HTTPException
from loguru import logger
from sqlalchemy import create_engine

from agent_ai.agent.agent_builder import AgentManager
from agent_ai.memory.memory_manager import (
    LongTermMemoryProvider,
    ShortTermMemoryProvider,
)
from agent_ai.utils.constants import MODEL_CONFIG_FILE_PATH, PROMPT_PATH
from server.api.dependencies.database_v2 import get_db_url
from server.schemas.reference import UserManualToolRequest

# =============================================================================
# Global Configurations
# =============================================================================
router = APIRouter()

logger.remove()
logger.add(sys.stderr, level="INFO")

client_tag = "localhost"
engine = create_engine(get_db_url(client_tag))


# =============================================================================
# API Endpoint
# =============================================================================
@router.post("/user_manual", response_model=dict)
def user_manual_tool(request_body: UserManualToolRequest):
    try:
        # Short Term Memory shared between all agents
        short_term_memory_provider = ShortTermMemoryProvider(
            config_path=MODEL_CONFIG_FILE_PATH,
            user_id=request_body.user_id,
            session_id=request_body.session_id,
        )

        # Long Term Memory shared between all agents
        long_term_memory_provider = LongTermMemoryProvider(
            db_engine=engine,
            config_path=MODEL_CONFIG_FILE_PATH,
            user_id=request_body.user_id,
            session_id=request_body.session_id,
        )

        manager = AgentManager(
            config_path=MODEL_CONFIG_FILE_PATH,
            prompt_dir=PROMPT_PATH,
            short_term_memory_provider=short_term_memory_provider,
            long_term_memory_provider=long_term_memory_provider,
            context_text=request_body.context,
        )
        user_manual_result = manager.run("user_manual", request_body.message)

        return user_manual_result

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=500,
            detail="There was an error processing your query. Please try again later.",
        )
