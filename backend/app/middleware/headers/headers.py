from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp
from app.middleware.headers.presets import PRESETS
from app.middleware.headers.header_mapping import PARAM_TO_HEADER
from app.middleware.headers.csp_nonce_manager import CSPNonceManager


class HeadersMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        preset: str = None,
        use_csp_nonce: bool = True,
        **custom_headers,
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
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        # Generate unique nonce for this request
        nonce = CSPNonceManager.generate_nonce()
        request.state.csp_nonce = nonce

        response = await call_next(request)

        for header_name, header_value in self.headers.items():
            # Replace CSP header with nonce-based version if enabled
            if header_name == "Content-Security-Policy" and self.use_csp_nonce:
                header_value = CSPNonceManager.build_csp_header(nonce)

            response.headers[header_name] = header_value

        return response
