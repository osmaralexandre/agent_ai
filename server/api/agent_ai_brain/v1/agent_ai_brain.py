import os
import sys

import requests
from fastapi import APIRouter, HTTPException
from loguru import logger
from sqlalchemy import create_engine

from agent_ai.agent.agent_builder import AgentManager
from agent_ai.agent.embedding_search import EmbeddingSearch
from agent_ai.memory.memory_manager import (
    LongTermMemoryProvider,
    ShortTermMemoryProvider,
)
from agent_ai.utils.constants import (
    INPUT_GUARDRAIL_DENIED_RESPONSE,
    MODEL_CONFIG_FILE_PATH,
    PROMPT_PATH,
)
from server.api.dependencies.database_v2 import get_db_url
from server.schemas.reference import AgentAIBrainRequest

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
@router.post("/agent_ai_brain", response_model=dict)
def agent_ai_brain(request_body: AgentAIBrainRequest):
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

        # Load all agents
        manager = AgentManager(
            config_path=MODEL_CONFIG_FILE_PATH,
            prompt_dir=PROMPT_PATH,
            short_term_memory_provider=short_term_memory_provider,
            long_term_memory_provider=long_term_memory_provider,
        )

        # ---------------------------------------------------------------------
        # 1. Input Guardrail Agent
        # ---------------------------------------------------------------------
        input_guardrail_result = manager.run(
            "input_guardrail", request_body.message
        )

        logger.info(f"Guardrail: {input_guardrail_result}")

        if input_guardrail_result["response"] == "DENIED":
            input_guardrail_result.update(
                {"response": INPUT_GUARDRAIL_DENIED_RESPONSE}
            )
            return input_guardrail_result

        # Add a user message to the short term memory
        short_term_memory_provider.add_message("user", request_body.message)

        # Add a user message to the long term memory
        add_user_long_term_memory_result = (
            long_term_memory_provider.add_message(
                agent_name="user",
                role="user",
                result={
                    "response": request_body.message,
                    "tokens_prompt": 0,
                    "tokens_completion": 0,
                    "tokens_total": 0,
                    "cost_usd": 0,
                },
            )
        )

        # ---------------------------------------------------------------------
        # 2. Rewriter Agent
        # ---------------------------------------------------------------------
        rewriter_result = manager.run("rewriter", request_body.message)

        logger.info(f"Rewriter + Get LTM: {rewriter_result}")

        # ---------------------------------------------------------------------
        # 3. Embedding Search Agent to retrieve relevant documents and for intent classification
        # ---------------------------------------------------------------------
        embedding_search = EmbeddingSearch(
            db_engine=engine,
            config_path=MODEL_CONFIG_FILE_PATH,
        )
        similar_docs, embedding_result = (
            embedding_search.get_similar_embeddings(
                rewriter_result["response"], top_n=5
            )
        )
        logger.info(f"Embedding Search: {embedding_result}")

        # ---------------------------------------------------------------------
        # 4. Intent Classifier Agent
        # ---------------------------------------------------------------------
        agent_name = "intent_classifier"
        intent_classifier_agent_result = manager.run(
            agent_name, rewriter_result["response"]
        )
        logger.info(f"Intent Classifier: {intent_classifier_agent_result}")

        agent_tool = intent_classifier_agent_result["response"]["intent"]
        if agent_tool == "user_manual":
            agent_name = "user_manual"
            # -----------------------------------------------------------------
            # 5. User Manual Tool Agent
            # -----------------------------------------------------------------
            context = "\n\n".join([doc["content"] for doc in similar_docs])

            request_body = {
                "user_id": request_body.user_id,
                "session_id": request_body.session_id,
                "client_hash": request_body.client_hash,
                "context": context,
                "message": rewriter_result["response"],
            }

            headers = {
                "accept": "application/json",
                "Content-Type": "application/json",
            }

            response = requests.post(
                "http://localhost:8000/v1/user_manual",
                headers=headers,
                json=request_body,
            )

            intent_classifier_result = response.json()

            logger.info(f"User Manual: {intent_classifier_result}")

        elif agent_tool == "device_alarms":
            agent_name = "device_alarms"
            # -----------------------------------------------------------------
            # 6. Device Alarms Tool Agent
            # -----------------------------------------------------------------

            request_body = {
                "user_id": request_body.user_id,
                "session_id": request_body.session_id,
                "client_hash": request_body.client_hash,
                "message": rewriter_result["response"],
            }

            headers = {
                "accept": "application/json",
                "Content-Type": "application/json",
            }

            response = requests.post(
                "http://localhost:8000/v1/device_alarms",
                headers=headers,
                json=request_body,
            )

            intent_classifier_result = response.json()

            logger.info(f"Device Alarms + Get LTM: {intent_classifier_result}")

        else:
            # -----------------------------------------------------------------
            # 7. Energy Only Tool Agent
            # -----------------------------------------------------------------
            agent_name = "energy_only"
            intent_classifier_result = manager.run(
                agent_name, rewriter_result["response"]
            )
            logger.info(f"Energy Only: {intent_classifier_result}")

        # Add an assistant message to the short term memory
        short_term_memory_provider.add_message(
            role="assistant", message=intent_classifier_result["response"]
        )

        # ---------------------------------------------------------------------
        # 8. Cost Calculation
        # ---------------------------------------------------------------------
        cost_results_dicts = [
            input_guardrail_result,
            add_user_long_term_memory_result,
            rewriter_result,
            embedding_result,
            intent_classifier_agent_result,
            intent_classifier_result,
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

        result = {
            "response": intent_classifier_result["response"],
            **total_cost,
        }

        # Add an assistant message to the long term memory
        result = long_term_memory_provider.add_message(
            agent_name=agent_name,
            role="assistant",
            result=result,
        )
        logger.info(f"Total Cost: {result}")

        return result

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=500,
            detail="There was an error processing your query. Please try again later.",
        )
