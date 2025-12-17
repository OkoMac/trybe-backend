"""Sentry error tracking configuration"""

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
import logging

from app.core.config import settings


def init_sentry():
    """
    Initialize Sentry for error tracking and performance monitoring

    Features:
    - Automatic error capture
    - Performance monitoring
    - Request breadcrumbs
    - Database query tracking
    - Redis operation tracking
    - Celery task tracking
    """
    if not settings.SENTRY_DSN or settings.SENTRY_DSN in ["", "None", "null"]:
        logging.info("Sentry DSN not configured. Error tracking disabled.")
        return

    try:
        sentry_sdk.init(
        dsn=settings.SENTRY_DSN,

        # Environment
        environment=settings.ENVIRONMENT,

        # Release tracking
        release=f"trybe-backend@{settings.VERSION}",

        # Performance monitoring
        traces_sample_rate=0.1 if settings.ENVIRONMENT == "production" else 1.0,
        profiles_sample_rate=0.1 if settings.ENVIRONMENT == "production" else 1.0,

        # Integrations
        integrations=[
            # FastAPI integration
            FastApiIntegration(
                transaction_style="url",  # Group by URL pattern
                failed_request_status_codes=[500, 599],  # Only 5xx errors
            ),

            # SQLAlchemy integration
            SqlalchemyIntegration(),

            # Redis integration
            RedisIntegration(),

            # Celery integration
            CeleryIntegration(
                monitor_beat_tasks=True,
                propagate_traces=True,
            ),

            # Logging integration
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR,
            ),
        ],

        # Error filtering
        ignore_errors=[
            # Don't report common client errors
            "fastapi.exceptions.RequestValidationError",
            "starlette.exceptions.HTTPException",
        ],

        # PII filtering
        send_default_pii=False,

        # Additional options
        attach_stacktrace=True,
        debug=settings.ENVIRONMENT == "development",

        # Request data
        max_request_body_size="medium",  # Don't send large request bodies

        # Breadcrumbs
        max_breadcrumbs=50,

        # Before send hook for additional filtering
        before_send=before_send_filter,
        )

        logging.info(f"Sentry initialized for environment: {settings.ENVIRONMENT}")

    except Exception as e:
        logging.error(f"Failed to initialize Sentry: {e}")
        logging.info("Continuing without Sentry error tracking")


def before_send_filter(event, hint):
    """
    Filter and modify events before sending to Sentry

    Use this to:
    - Remove sensitive data
    - Filter out noisy errors
    - Add additional context
    """
    # Don't send health check errors
    if event.get("request", {}).get("url", "").endswith("/health"):
        return None

    # Filter out 404 errors (too noisy)
    if event.get("exception", {}).get("values", [{}])[0].get("type") == "HTTPException":
        if "404" in str(event.get("exception", {}).get("values", [{}])[0].get("value", "")):
            return None

    # Scrub sensitive data from breadcrumbs
    if "breadcrumbs" in event:
        for breadcrumb in event["breadcrumbs"].get("values", []):
            if breadcrumb.get("category") == "httpx":
                # Remove authorization headers
                if "data" in breadcrumb and "headers" in breadcrumb["data"]:
                    breadcrumb["data"]["headers"].pop("authorization", None)
                    breadcrumb["data"]["headers"].pop("cookie", None)

    return event


def capture_exception(exception: Exception, **kwargs):
    """
    Manually capture an exception with additional context

    Usage:
        from app.core.sentry import capture_exception

        try:
            dangerous_operation()
        except Exception as e:
            capture_exception(
                e,
                user_id=user.id,
                operation="dangerous_operation"
            )
    """
    with sentry_sdk.push_scope() as scope:
        # Add custom context
        for key, value in kwargs.items():
            scope.set_context(key, {"value": value})

        # Capture the exception
        sentry_sdk.capture_exception(exception)


def capture_message(message: str, level: str = "info", **kwargs):
    """
    Capture a message with additional context

    Usage:
        from app.core.sentry import capture_message

        capture_message(
            "Payment processing started",
            level="info",
            user_id=user.id,
            amount=100.00
        )
    """
    with sentry_sdk.push_scope() as scope:
        # Add custom context
        for key, value in kwargs.items():
            scope.set_context(key, {"value": value})

        # Capture the message
        sentry_sdk.capture_message(message, level=level)


def set_user_context(user_id: str, email: str = None, username: str = None):
    """
    Set user context for error reports

    Usage:
        from app.core.sentry import set_user_context

        @app.middleware("http")
        async def add_user_context(request: Request, call_next):
            if hasattr(request.state, "user"):
                set_user_context(
                    user_id=request.state.user.id,
                    email=request.state.user.email
                )
            return await call_next(request)
    """
    sentry_sdk.set_user({
        "id": user_id,
        "email": email,
        "username": username,
    })


def add_breadcrumb(message: str, category: str = "custom", level: str = "info", **data):
    """
    Add a breadcrumb for context in error reports

    Usage:
        from app.core.sentry import add_breadcrumb

        add_breadcrumb(
            message="User started checkout",
            category="user.action",
            level="info",
            cart_total=150.00
        )
    """
    sentry_sdk.add_breadcrumb({
        "message": message,
        "category": category,
        "level": level,
        "data": data,
    })


def start_transaction(name: str, op: str = "task"):
    """
    Start a performance transaction

    Usage:
        from app.core.sentry import start_transaction

        with start_transaction(name="process_payment", op="payment"):
            # Payment processing code
            pass
    """
    return sentry_sdk.start_transaction(name=name, op=op)
