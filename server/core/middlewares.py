import json
import logging
from datetime import datetime
from time import time
from typing import Any, Awaitable, Callable, Dict
from urllib.parse import parse_qs

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LogPerformance(BaseHTTPMiddleware):
    """
    Loga metadados envolvendo a request enviada, o status da resposta
    e o tempo gasto no processamento. Baseado no projeto:
    https://github.com/12345k/fastapi_logging
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """
        Método principal do middleware.
        """
        start_time = time()

        try:
            body = await self._get_body(request)
            body = json.loads(body)
        except json.decoder.JSONDecodeError:
            body = None

        try:
            response = await call_next(request)

            process_time = (time() - start_time) * 1000
            formatted_process_time = "{0:.2f}".format(process_time)

            metrics_json = {
                "type": "metrics",
                "method": request.method,
                "url": request.url.path,
                "query": parse_qs(str(request.query_params)),
                "body": body,
                "status_code": response.status_code,
                "length": response.headers["content-length"],
                "latency": formatted_process_time,
                "ts": f"{datetime.now():%Y-%m-%d %H:%M:%S%z}",
            }
            logger.info(json.dumps(metrics_json, indent=4))

            return response

        except Exception as exc:
            process_time = (time() - start_time) * 1000
            formatted_process_time = "{0:.2f}".format(process_time)

            metrics_json = {
                "type": "metrics",
                "method": request.method,
                "url": request.url.path,
                "query": parse_qs(str(request.query_params)),
                "body": body,
                "status_code": 500,
                "msg": exc.args[0],
                "length": None,
                "latency": formatted_process_time,
                "ts": f"{datetime.now():%Y-%m-%d %H:%M:%S%z}",
            }
            logger.info(json.dumps(metrics_json, indent=4))

            raise exc

    async def _get_body(self, request: Request) -> bytes:
        """
        Resgata o body da request e o "reconstrói" para que possa ser
        repassado para a rota da API.
        """
        body = await request.body()
        await self._set_body(request, body)
        return body

    async def _set_body(self, request: Request, body: bytes) -> None:
        """
        Seta o body de uma request.
        """

        async def receive() -> Dict[str, Any]:
            return {"type": "http.request", "body": body}

        request._receive = receive
