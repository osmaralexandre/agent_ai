from typing import List

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
