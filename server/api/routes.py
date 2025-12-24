from fastapi import APIRouter

from server.api.agent_ai_brain.v1 import agent_ai_brain
from server.api.device_alarms_tool.v1 import device_alarms_tool
from server.api.user_manual_tool.v1 import user_manual_tool


router = APIRouter()

router.include_router(agent_ai_brain.router, tags=["Agent AI [Brain]"])
router.include_router(user_manual_tool.router, tags=["Agent AI [Tools]"])
router.include_router(device_alarms_tool.router, tags=["Agent AI [Tools]"])
