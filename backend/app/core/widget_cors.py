"""Narrow CORS handling for browser Widget bootstrap and chat requests."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.app.auth.origin import normalize_origin


_WIDGET_BROWSER_PATHS = {
    "/api/widget/bootstrap",
    "/api/widget/config",
    "/api/widget/connector/pair",
    "/api/chat",
}
_ALLOWED_REQUEST_HEADERS = {"authorization", "content-type"}


def _append_vary(response: Response, value: str) -> None:
    existing = {
        item.strip()
        for item in response.headers.get("Vary", "").split(",")
        if item.strip()
    }
    existing.add(value)
    response.headers["Vary"] = ", ".join(sorted(existing))


def apply_widget_cors(response: Response, origin: str) -> None:
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = (
        "Authorization, Content-Type"
    )
    response.headers["Access-Control-Expose-Headers"] = "X-Request-ID"
    response.headers["Access-Control-Max-Age"] = "600"
    _append_vary(response, "Origin")


class WidgetCORSMiddleware(BaseHTTPMiddleware):
    """Handle preflight and expose only origin-authorized actual responses.

    A preflight contains no bearer token or request body, so it cannot prove
    Widget ownership. It receives only protocol permission. The actual route
    performs database allow-list and token-origin checks, then marks the
    request state; only marked responses receive CORS access.
    """

    async def dispatch(self, request: Request, call_next):
        if request.url.path not in _WIDGET_BROWSER_PATHS:
            return await call_next(request)

        if request.method == "OPTIONS":
            origin = normalize_origin(request.headers.get("Origin"))
            requested_method = request.headers.get(
                "Access-Control-Request-Method",
                "",
            ).upper()
            requested_headers = {
                item.strip().casefold()
                for item in request.headers.get(
                    "Access-Control-Request-Headers",
                    "",
                ).split(",")
                if item.strip()
            }
            if (
                origin is None
                or requested_method != "POST"
                or not requested_headers.issubset(_ALLOWED_REQUEST_HEADERS)
            ):
                return Response(status_code=403)
            response = Response(status_code=204)
            apply_widget_cors(response, origin)
            return response

        response = await call_next(request)
        authorized_origin = getattr(
            request.state,
            "widget_cors_origin",
            None,
        )
        if authorized_origin is not None:
            apply_widget_cors(response, authorized_origin)
        return response
