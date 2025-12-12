import logging
from logging.config import dictConfig

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.cors import CORSMiddleware
from starlette.templating import _TemplateResponse

from server.api.routes import router
from server.core.logger import LogConfig
from server.core.middlewares import LogPerformance
from server.core.settings import base_settings

dictConfig(LogConfig().to_dict())
logging.getLogger("uvicorn").handlers.clear()
logger = logging.getLogger(__name__)
logger.info(base_settings.PROJECT_NAME)

templates = Jinja2Templates(directory="templates")

app = FastAPI(
    title=base_settings.PROJECT_NAME,
    description=base_settings.DESCRIPTION,
    version=base_settings.VERSION,
)

if base_settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            str(origin) for origin in base_settings.BACKEND_CORS_ORIGINS
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def retrieve_index(request: Request) -> _TemplateResponse:
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "name": base_settings.PROJECT_NAME},
    )


app.include_router(router, prefix=base_settings.ROUTE_V1)

# app.add_middleware(LogPerformance)
