"""Security headers middleware"""

from fastapi import Request
from fastapi.responses import Response
from typing import Callable


async def add_security_headers(request: Request, call_next: Callable) -> Response:
    """
    Add security headers to all responses

    Implements OWASP recommendations:
    - HSTS (HTTP Strict Transport Security)
    - CSP (Content Security Policy)
    - X-Frame-Options
    - X-Content-Type-Options
    - Referrer-Policy
    - Permissions-Policy
    """
    response = await call_next(request)

    # HSTS - Force HTTPS
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    # CSP - Content Security Policy
    csp_directives = [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com",
        "img-src 'self' data: https:",
        "connect-src 'self' https:",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'"
    ]
    response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"

    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"

    # XSS Protection (for older browsers)
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # Referrer Policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Permissions Policy (formerly Feature Policy)
    permissions = [
        "geolocation=(self)",
        "microphone=()",
        "camera=()",
        "payment=(self)",
        "usb=()",
        "magnetometer=()",
        "gyroscope=()",
        "speaker=(self)"
    ]
    response.headers["Permissions-Policy"] = ", ".join(permissions)

    # Remove Server header (don't reveal server info)
    if "Server" in response.headers:
        del response.headers["Server"]

    # Remove X-Powered-By if present
    if "X-Powered-By" in response.headers:
        del response.headers["X-Powered-By"]

    return response


async def add_cors_headers(request: Request, call_next: Callable) -> Response:
    """
    Add CORS headers with security considerations
    """
    response = await call_next(request)

    # Note: FastAPI's CORSMiddleware should handle most CORS
    # This is for additional security headers

    # Prevent credentials exposure
    if response.headers.get("Access-Control-Allow-Credentials") == "true":
        # Ensure origin is not wildcard when credentials are allowed
        origin = response.headers.get("Access-Control-Allow-Origin")
        if origin == "*":
            # This is a security risk, remove credentials
            if "Access-Control-Allow-Credentials" in response.headers:
                del response.headers["Access-Control-Allow-Credentials"]

    return response
