"""Token-protected admin routes next to /mcp: /admin/stats, /admin/reset, /admin/insert.

Why a separate HTTP interface and not MCP tools: the tools list is what a model can call.
Resetting the lab or planting a poisoned ticket is the operator's job, so it lives outside
that list. The routes need a bearer token (ADMIN_TOKEN); with no token set they are not
registered at all.
"""

from __future__ import annotations

import hmac

from starlette.requests import Request
from starlette.responses import JSONResponse

from . import helpdesk
from .tools import Lab


def register_admin(server, lab: Lab, token: str) -> None:
    def authorized(request: Request) -> bool:
        supplied = request.headers.get("authorization", "")
        return hmac.compare_digest(supplied.encode(), f"Bearer {token}".encode())

    async def body_of(request: Request) -> dict:
        try:
            data = await request.json()
        except Exception:
            return {}
        return data if isinstance(data, dict) else {}

    @server.custom_route("/admin/stats", methods=["GET"])
    async def stats(request: Request) -> JSONResponse:
        if not authorized(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return JSONResponse(helpdesk.stats(lab))

    @server.custom_route("/admin/reset", methods=["POST"])
    async def reset(request: Request) -> JSONResponse:
        if not authorized(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        body = await body_of(request)
        result = helpdesk.reset(lab, str(body.get("scenario", "empty")), bool(body.get("full", False)))
        return JSONResponse(result, status_code=400 if "error" in result else 200)

    @server.custom_route("/admin/insert", methods=["POST"])
    async def insert(request: Request) -> JSONResponse:
        if not authorized(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        body = await body_of(request)
        try:
            result = helpdesk.insert(
                lab, str(body.get("kind", "normal")), int(body.get("count", 1)),
                str(body.get("poison_kind", helpdesk.DEFAULT_POISON_KIND)),
            )
        except (TypeError, ValueError):
            return JSONResponse({"error": "count must be a number"}, status_code=400)
        return JSONResponse(result, status_code=400 if "error" in result else 200)
