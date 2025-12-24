from typing import List, Literal

from pydantic import BaseModel, Field


class Asset(BaseModel):
    solar_field: str
    inverter: str


class ReferenceData(BaseModel):
    inverter_id: int = 7
    start_time: str = "2023-01-01"
    end_time: str = "2024-01-01"


class FilterResponse(BaseModel):
    filter_percentages: dict


class AgentAIBrainRequest(BaseModel):
    user_id: str = Field(..., description="The ID of the user")
    session_id: str = Field(..., description="The ID of the session")
    client_hash: str = Field(..., description="The hash of the client")
    message: str = Field(
        ..., description="The message to be sent to the Agent AI Brain"
    )


class UserManualToolRequest(BaseModel):
    user_id: str = Field(..., description="The ID of the user")
    session_id: str = Field(..., description="The ID of the session")
    client_hash: str = Field(..., description="The hash of the client")
    context: str = Field(
        ..., description="The context for the User Manual Tool"
    )
    message: str = Field(
        ..., description="The message to be sent to the User Manual Tool"
    )
    
class DeviceAlarmsToolRequest(BaseModel):
    user_id: str = Field(..., description="The ID of the user")
    session_id: str = Field(..., description="The ID of the session")
    client_hash: str = Field(..., description="The hash of the client")
    message: str = Field(
        ..., description="The message to be sent to the Device Alarm Tool"
    )

class AlarmQuery(BaseModel):
    device_name: str = Field(
        default="",
        description="Device identifier (example: GOB-02) or empty string"
    )
    end_time: str = Field(
        default="",
        description="Analysis date in ISO YYYY-MM-DD format (example: 2025-01-01) or empty string"
    )

class IntentClassifier(BaseModel):
    intent: Literal[
        "user_manual",
        "energy_only",
        "device_alarms",
    ]
    confidence: float