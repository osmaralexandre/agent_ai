import datetime
import os
import sys

import pandas as pd
import requests
from dotenv import load_dotenv
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
from server.schemas.reference import DeviceAlarmsToolRequest

# =============================================================================
# Global Configurations
# =============================================================================
router = APIRouter()

logger.remove()
logger.add(sys.stderr, level="INFO")

client_tag = "localhost"
engine = create_engine(get_db_url(client_tag))

load_dotenv()
ALARMIMG_WTG_API = os.getenv("ALARMIMG_WTG_API")


# =============================================================================
# API Endpoint
# =============================================================================
@router.post("/device_alarms", response_model=dict)
def device_alarms_tool(request_body: DeviceAlarmsToolRequest):
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
        )
        device_alarms_result = manager.run(
            "device_alarms", request_body.message
        )
        end_time = device_alarms_result["response"]["end_time"]

        request_body = {
            "client_hash": request_body.client_hash,
            "end_time": (
                end_time
                if end_time != ""
                else datetime.now().strftime("%Y-%m-%d")
            ),
        }

        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
        }
        response = requests.post(
            ALARMIMG_WTG_API,
            headers=headers,
            json=request_body,
        )

        device_alarms_json = response.json()
        device_alarms_result_df = pd.DataFrame(device_alarms_json)

        device_name = device_alarms_result["response"]["device_name"]
        if device_name != "":
            device_alarms_result_df = device_alarms_result_df[
                device_alarms_result_df["name"] == device_name
            ]

            device_alarms_result["response"] = (
                f"Alarmes encontrados para o dispositivo {device_name} no período {end_time}:\n\n"
                + "\n\n".join(
                    f"Componente: {row.component_name}\n"
                    f"Variable: {row.output}\n"
                    f"Status: {row.status}\n"
                    f"Pontos acima do threshold: {row.total_above_threshold}\n"
                    f"Rank: {row.rank_text}\n"
                    for row in device_alarms_result_df.itertuples()
                )
            )

        else:
            device_alarms_result["response"] = (
                f"Por favor, informe o nome do dispositivo para buscar os alarmes."
            )

        return device_alarms_result

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=500,
            detail="There was an error processing your query. Please try again later.",
        )
