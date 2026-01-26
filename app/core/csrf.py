from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi import Request as FastAPIRequest, HTTPException
import secrets
import typing

class CSRFMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, secret_key: str = "secret"):
        super().__init__(app)
        self.secret_key = secret_key

    async def dispatch(self, request: Request, call_next):
        # 1. Allow Safe Methods logic for Cookie Setting
        # We always want to ensure the cookie exists on the response if it's missing
        # But usually we only set it on initial page loads (GET)
        
        response = await call_next(request)
        
        # Set CSRF cookie if it doesn't exist (simplistic approach)
        # Check if the request had it, if not, we might want to adding it to response
        # But checking request.cookies is easier in the Validation step? 
        # No, validation might block it.
        
        # Better approach: Check if we need to set it on the RESPONSE
        if "csrf_token" not in request.cookies:
             # We can't easily see if the response already set it, but we can try
             # Actually, if we generated one in memory, we should stash it.
             pass

        return response

# Simplified Middleware just to Inject Cookie on GET if missing
# AND we will use a separate Dependency for checking.

async def validate_csrf(request: FastAPIRequest):
    if request.method in ("GET", "HEAD", "OPTIONS") or request.url.path.startswith("/ws/"):
        # Ensure cookie exists for the validation logic (if we wanted to enforce it exists even on GET? No)
        return

    cookie_token = request.cookies.get("csrf_token")
    header_token = request.headers.get("x-csrf-token")
    
    # Check form data if header is missing
    if not header_token and request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded"):
            form = await request.form()
            header_token = form.get("csrf_token")

    if not cookie_token or not header_token or cookie_token != header_token:
        raise HTTPException(
            status_code=403,
            detail="CSRF doğrulaması başarısız. Lütfen sayfayı yenileyin."
        )

# Re-implement Middleware to simply be a "Cookie Setter" for GET requests
class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        
        response = await call_next(request)
        
        # If it was a GET request and no cookie existed, set one.
        if request.method == "GET" and "csrf_token" not in request.cookies:
            # Check if logic downstream already set it?
            # It's safer to generate one if missing.
            token = secrets.token_hex(32)
            response.set_cookie("csrf_token", token, httponly=False, samesite="lax")
            
        return response

def get_csrf_token(request: FastAPIRequest):
    # This helper is used in templates
    # If the cookie is present, return it.
    # If not, we might need to generate one? 
    # But template rendering happens in the VIEW.
    # The view is a GET request usually.
    # The Middleware (above) runs AFTER the view returns (response).
    # So we need to ensure the token is available for the template.
    
    token = request.cookies.get("csrf_token")
    if not token:
        # We can't easily valid set cookie here.
        # But we can generate it and allow the Middleware to save it?
        # Or simply return a text placeholder and JS handles it? No.
        # We just return empty string or handle it gracefully.
        # Ideally, middleware ensures it on GET.
        pass
    return token

# Wait, there's a chicken-egg problem.
# If Middleware runs AFTER, how does template get the token?
# Middleware dispatch:
#   response = await call_next(request)
#   return response
#
# If we modify the response headers AFTER, we are good. 
# But the template needs the value DURING processing.
#
# Helper function logic needs to be smart.
# Usage: {{ csrf_token(request) }}
#
# If we change get_csrf_token to ensure it returns a token, 
# and somehow verify that token is set?
#
# Let's fix get_csrf_token to return a specific value if missing, 
# and maybe the middleware can check for that? 
# OR, use a request state.

def get_csrf_token(request: FastAPIRequest):
    token = request.cookies.get("csrf_token")
    if not token:
        # Check if we already generated one in this request scope
        if not hasattr(request.state, "csrf_token"):
             request.state.csrf_token = secrets.token_hex(32)
        return request.state.csrf_token
    return token

class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Logic to persist the token if it was generated during request
        if hasattr(request.state, "csrf_token"):
             response.set_cookie("csrf_token", request.state.csrf_token, httponly=False, samesite="lax")
        elif request.method == "GET" and "csrf_token" not in request.cookies:
             # Fallback
             token = secrets.token_hex(32)
             response.set_cookie("csrf_token", token, httponly=False, samesite="lax")
             
        return response

