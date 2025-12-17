"""API v1 Router - Aggregates all v1 endpoints"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    opportunities,
    payments,
    messages,
    notifications,
    learning,
    analytics,
    reports,
    hackathons,
    community,
    solar,
    admin,
    files,
    reviews,
    push_notifications,
    whatsapp,
    career,
    aptitude
)

api_router = APIRouter()

# Authentication routes
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

# Opportunities routes
api_router.include_router(
    opportunities.router,
    prefix="/opportunities",
    tags=["Opportunities"]
)

# Payments routes
api_router.include_router(
    payments.router,
    prefix="/payments",
    tags=["Payments"]
)

# Messages routes
api_router.include_router(
    messages.router,
    prefix="/messages",
    tags=["Messages"]
)

# Notifications routes
api_router.include_router(
    notifications.router,
    prefix="/notifications",
    tags=["Notifications"]
)

# Learning routes
api_router.include_router(
    learning.router,
    prefix="/learning",
    tags=["Learning"]
)

# Analytics routes
api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["Analytics"]
)

# Reports routes
api_router.include_router(
    reports.router,
    prefix="/reports",
    tags=["Reports"]
)

# Hackathons routes
api_router.include_router(
    hackathons.router,
    prefix="/hackathons",
    tags=["Hackathons"]
)

# Community routes
api_router.include_router(
    community.router,
    prefix="/community",
    tags=["Community"]
)

# Solar Revolution routes
api_router.include_router(
    solar.router,
    prefix="/solar",
    tags=["Solar Revolution"]
)

# Admin routes
api_router.include_router(
    admin.router,
    prefix="/admin",
    tags=["Admin"]
)

# File upload routes
api_router.include_router(
    files.router,
    prefix="/files",
    tags=["Files"]
)

# Reviews and Ratings routes
api_router.include_router(
    reviews.router,
    prefix="/reviews",
    tags=["Reviews & Ratings"]
)

# Push Notifications routes
api_router.include_router(
    push_notifications.router,
    prefix="/push-notifications",
    tags=["Push Notifications"]
)

# WhatsApp routes
api_router.include_router(
    whatsapp.router,
    prefix="/whatsapp",
    tags=["WhatsApp"]
)

# AI Career Assistant routes
api_router.include_router(
    career.router,
    prefix="/career",
    tags=["AI Career Assistant"]
)

# Aptitude Tests routes
api_router.include_router(
    aptitude.router,
    prefix="/aptitude",
    tags=["Aptitude Tests"]
)
