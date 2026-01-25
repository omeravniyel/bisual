from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi import Request as FastAPIRequest
import secrets
import typing

class CSRFMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, secret_key: str = "secret"):
        super().__init__(app)
        self.secret_key = secret_key

    async def dispatch(self, request: Request, call_next):
        # 1. Allow Safe Methods (GET, HEAD, OPTIONS)
        if request.method in ("GET", "HEAD", "OPTIONS"):
            response = await call_next(request)
            # Ensure cookie is set if not present
            if "csrf_token" not in request.cookies:
                token = secrets.token_hex(32)
                response.set_cookie("csrf_token", token, httponly=False, samesite="lax")
            return response

        # 2. Check for Exclusions (Webhooks, internal APIs if any)
        # (Add exclusions here if needed)

        # 3. Verify Token
        cookie_token = request.cookies.get("csrf_token")
        header_token = request.headers.get("x-csrf-token")
        
        # Check form data if header is missing (for traditional forms)
        if not header_token and request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded"):
             form = await request.form()
             header_token = form.get("csrf_token")

        if not cookie_token or not header_token or cookie_token != header_token:
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF doğrulaması başarısız. Lütfen sayfayı yenileyin."}
            )

        response = await call_next(request)
        return response

def get_csrf_token(request: FastAPIRequest):
    return request.cookies.get("csrf_token", "")
