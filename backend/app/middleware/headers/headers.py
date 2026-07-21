from __future__ import annotations

from beartype.typing import Any, Awaitable, Callable, MutableMapping
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.middleware.headers.presets import PRESETS
from app.middleware.headers.header_mapping import PARAM_TO_HEADER
from app.middleware.headers.csp_nonce_manager import CSPNonceManager


class HeadersMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: Callable[
            [
                MutableMapping[str, Any],
                Callable[[], Awaitable[MutableMapping[str, Any]]],
                Callable[[MutableMapping[str, Any]], Awaitable[None]],
            ],
            Awaitable[None],
        ],
        preset: str | None = None,
        use_csp_nonce: bool = True,
        auth_provider_origin: str | None = None,
        **custom_headers: Any,
    ):
        headers = PRESETS.get(preset, {}).copy() if preset else {}

        for param_name, value in custom_headers.items():
            if param_name not in PARAM_TO_HEADER:
                continue
            header_name = PARAM_TO_HEADER[param_name]
            if value is None:
                headers.pop(header_name, None)
            else:
                headers[header_name] = value

        self.headers = headers
        self.use_csp_nonce = use_csp_nonce
        self.auth_provider_origin = auth_provider_origin
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Generate unique nonce for this request
        nonce = CSPNonceManager.generate_nonce()
        request.state.csp_nonce = nonce

        response = await call_next(request)

        for header_name, header_value in self.headers.items():
            # Replace CSP header with nonce-based version if enabled
            if header_name == "Content-Security-Policy" and self.use_csp_nonce:
                header_value = CSPNonceManager.build_csp_header(
                    nonce,
                    auth_provider_origin=self.auth_provider_origin,
                )

            response.headers[header_name] = header_value

        return response
