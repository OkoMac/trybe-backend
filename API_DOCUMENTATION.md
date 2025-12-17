# Trybe Backend API Documentation
**Version:** 0.5.0  
**Base URL:** `http://localhost:8000` (development) | `https://api.trybe.app` (production)  
**Date:** December 16, 2025

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Error Handling](#error-handling)
4. [Rate Limiting](#rate-limiting)
5. [Pagination](#pagination)
6. [API Endpoints](#api-endpoints)
   - [Authentication](#authentication-endpoints)
   - [Opportunities](#opportunities-endpoints)
   - [Geolocation Search](#geolocation-search)
   - [Reviews & Ratings](#reviews--ratings-endpoints)
   - [Push Notifications](#push-notifications-endpoints)
   - [Files](#file-upload-endpoints)
   - [Payments](#payments-endpoints)
   - [Messages](#messages-endpoints)
   - [Analytics](#analytics-endpoints)
7. [Webhooks](#webhooks)
8. [SDKs & Libraries](#sdks--libraries)

---

## Overview

The Trybe API is a RESTful API that enables developers to build applications on top of the Trybe People's Market platform. The API provides access to opportunities, user matching, payments, messaging, reviews, and more.

### Base Features
- ✅ RESTful design
- ✅ JSON request/response format
- ✅ JWT-based authentication
- ✅ Rate limiting
- ✅ Pagination on list endpoints
- ✅ Comprehensive error messages
- ✅ OpenAPI/Swagger documentation

---

## Authentication

Trybe uses **JWT (JSON Web Tokens)** for authentication. Most endpoints require a valid access token in the Authorization header.

### Register a New User

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "full_name": "John Doe",
  "username": "johndoe",
  "user_type": "professional"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "full_name": "John Doe",
    "username": "johndoe",
    "user_type": "professional"
  }
}
```

### Login

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

### Using Access Tokens

Include the access token in the Authorization header for all authenticated requests:

```http
GET /api/v1/opportunities/
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Refresh Token

Access tokens expire after 15 minutes. Use the refresh token to get a new access token:

```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

## Error Handling

The API uses conventional HTTP response codes to indicate success or failure.

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 204 | No Content | Request successful, no content to return |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |

### Error Response Format

```json
{
  "detail": "Error message",
  "type": "validation_error",
  "errors": [
    {
      "field": "email",
      "message": "Invalid email format"
    }
  ]
}
```

---

## Rate Limiting

The API implements rate limiting to prevent abuse. Rate limits are applied per IP address and per user.

### Default Limits
- **Authentication endpoints:** 5 requests per 5 minutes
- **Standard endpoints:** 30 requests per minute
- **Upload endpoints:** 20 uploads per hour

### Rate Limit Headers

Every API response includes rate limit information:

```http
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 25
X-RateLimit-Reset: 1734345780
```

### Handling Rate Limits

When you exceed the rate limit, you'll receive a 429 status code:

```json
{
  "detail": "Rate limit exceeded. Try again in 45 seconds."
}
```

---

## Pagination

List endpoints support pagination using query parameters.

### Query Parameters
- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 20, max: 100)

### Example

```http
GET /api/v1/opportunities/?page=2&page_size=50
```

### Response Format

```json
{
  "items": [...],
  "total": 150,
  "page": 2,
  "page_size": 50,
  "total_pages": 3
}
```

---

## API Endpoints

### Authentication Endpoints

#### POST /api/v1/auth/register
Register a new user account.

**Body Parameters:**
- `email` (string, required) - User's email
- `password` (string, required) - Password (min 8 characters)
- `full_name` (string, required) - Full name
- `username` (string, required) - Unique username
- `user_type` (enum, required) - `professional`, `employer`, `company`

---

### Opportunities Endpoints

#### GET /api/v1/opportunities/
List all opportunities with filters.

**Query Parameters:**
- `page` (integer) - Page number
- `page_size` (integer) - Items per page
- `status_filter` (string) - Filter by status: `open`, `closed`, `filled`, `archived`, `all`
- `opportunity_type` (string) - Filter by type: `full_time`, `part_time`, `contract`, `freelance`, `gig`, `internship`
- `is_remote` (boolean) - Filter remote opportunities

**Example:**
```bash
curl -X GET "http://localhost:8000/api/v1/opportunities/?status_filter=open&is_remote=true" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### POST /api/v1/opportunities/
Create a new opportunity (employers/companies only).

**Body Parameters:**
- `title` (string, required) - Opportunity title
- `description` (string, required) - Detailed description
- `company_name` (string, required) - Company name
- `opportunity_type` (enum, required)
- `location` (object, optional) - Location with coordinates
- `is_remote` (boolean) - Remote work option
- `required_skills` (array) - Required skills
- `salary_min` (integer) - Minimum salary
- `salary_max` (integer) - Maximum salary
- `salary_currency` (string) - Currency code (default: USD)

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/opportunities/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Senior Python Developer",
    "description": "We are looking for an experienced Python developer...",
    "company_name": "Tech Corp",
    "opportunity_type": "full_time",
    "location": {
      "city": "Lagos",
      "country": "Nigeria",
      "coordinates": {
        "latitude": 6.5244,
        "longitude": 3.3792
      }
    },
    "is_remote": false,
    "required_skills": ["Python", "FastAPI", "PostgreSQL"],
    "salary_min": 80000,
    "salary_max": 120000,
    "salary_currency": "USD"
  }'
```

---

### Geolocation Search

#### GET /api/v1/opportunities/nearby/search
Search for opportunities near a specific location using haversine distance calculation.

**Query Parameters:**
- `latitude` (float, required) - User's latitude (-90 to 90)
- `longitude` (float, required) - User's longitude (-180 to 180)
- `radius_km` (float) - Search radius in kilometers (default: 25, max: 500)
- `page` (integer) - Page number
- `page_size` (integer) - Items per page
- `opportunity_type` (string) - Filter by type
- `is_remote` (boolean) - Include/exclude remote jobs

**Example:**
```bash
# Find opportunities within 50km of Lagos
curl -X GET "http://localhost:8000/api/v1/opportunities/nearby/search?latitude=6.5244&longitude=3.3792&radius_km=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Python Developer",
      "company_name": "Tech Corp",
      "location": {...},
      "distance_km": 12.5,
      "distance_text": "12.5 km",
      ...
    },
    {
      "id": "661f9511-f3ac-52e5-b827-557766551111",
      "title": "Remote Full Stack Developer",
      "is_remote": true,
      "distance_km": null,
      "distance_text": "Remote",
      ...
    }
  ],
  "total": 25,
  "page": 1,
  "page_size": 20,
  "total_pages": 2,
  "search_radius_km": 50,
  "search_location": {
    "latitude": 6.5244,
    "longitude": 3.3792
  }
}
```

**Features:**
- Uses Haversine formula for accurate distance calculation
- Efficient bounding box filtering before distance calculation
- Sorts results by distance (closest first)
- Remote jobs included at the end of results
- Returns formatted distance text (e.g., "12.5 km", "350 m", "Remote")

---

### Reviews & Ratings Endpoints

#### POST /api/v1/reviews/
Create a new review.

**Body Parameters:**
- `review_type` (enum, required) - Type: `opportunity`, `user`, `employer`, `hackathon`
- `target_id` (uuid, required) - ID of the entity being reviewed
- `rating` (integer, required) - Star rating (1-5)
- `title` (string, optional) - Review title
- `comment` (string, required) - Review text (min 10 characters)
- `ratings_breakdown` (object, optional) - Additional ratings

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/reviews/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "review_type": "opportunity",
    "target_id": "550e8400-e29b-41d4-a716-446655440000",
    "rating": 5,
    "title": "Great Experience!",
    "comment": "The opportunity was well-described and the team was very professional.",
    "ratings_breakdown": {
      "communication": 5,
      "work_environment": 4,
      "compensation": 5
    }
  }'
```

#### GET /api/v1/reviews/
List reviews with filters.

**Query Parameters:**
- `review_type` (string) - Filter by type
- `target_id` (uuid) - Filter by target
- `rating` (integer) - Filter by rating
- `verified_only` (boolean) - Show only verified purchases
- `min_rating` (integer) - Minimum rating
- `sort_by` (string) - Sort by: `created_at`, `rating`, `helpful_count`
- `sort_order` (string) - Order: `asc`, `desc`

#### POST /api/v1/reviews/{review_id}/helpful
Vote if a review is helpful.

#### POST /api/v1/reviews/{review_id}/flag
Flag a review for moderation (spam, inappropriate, etc.).

#### GET /api/v1/reviews/summary/{review_type}/{target_id}
Get aggregated review statistics.

**Response:**
```json
{
  "target_id": "550e8400-e29b-41d4-a716-446655440000",
  "review_type": "opportunity",
  "total_reviews": 42,
  "average_rating": 4.3,
  "rating_distribution": {
    "5": 20,
    "4": 15,
    "3": 5,
    "2": 1,
    "1": 1
  }
}
```

---

### Push Notifications Endpoints

#### POST /api/v1/push-notifications/tokens
Register a device for push notifications.

**Body Parameters:**
- `token` (string, required) - FCM device token
- `platform` (enum, required) - `ios`, `android`, `web`
- `device_name` (string, optional) - Friendly device name
- `device_id` (string, optional) - Unique device ID
- `app_version` (string, optional) - App version

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/push-notifications/tokens" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "token": "fcm_device_token_here",
    "platform": "ios",
    "device_name": "iPhone 13",
    "app_version": "1.0.0"
  }'
```

#### POST /api/v1/push-notifications/topics/subscribe
Subscribe to a notification topic.

**Topics:**
- `new_opportunities` - New opportunity notifications
- `hackathon_updates` - Hackathon event updates
- `system_announcements` - Platform announcements

#### POST /api/v1/push-notifications/test
Send a test notification to your devices.

---

### File Upload Endpoints

#### POST /api/v1/files/upload/avatar
Upload user avatar (auto-resized to 800x800).

**Form Data:**
- `file` (file, required) - Image file (JPEG, PNG, GIF, WebP, max 5MB)

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/files/upload/avatar" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@avatar.jpg"
```

**Response:**
```json
{
  "success": true,
  "filename": "avatar_550e8400.jpg",
  "file_path": "/uploads/avatars/550e8400.jpg",
  "file_url": "https://trybe.app/uploads/avatars/550e8400.jpg",
  "file_size": 145678,
  "content_type": "image/jpeg"
}
```

#### POST /api/v1/files/upload/document
Upload documents (resume, portfolio, etc.).

**Form Data:**
- `file` (file, required) - Document file (PDF, DOCX, TXT, max 10MB)
- `document_type` (string, required) - Type: `resume`, `portfolio`, `certificate`, `other`

---

## Webhooks

Trybe can send webhook events to your application when certain events occur.

### Setting Up Webhooks

```http
POST /api/v1/webhooks/
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{
  "url": "https://your-app.com/webhooks/trybe",
  "events": [
    "opportunity.created",
    "match.created",
    "payment.completed",
    "review.created"
  ],
  "secret": "your_webhook_secret"
}
```

### Webhook Events

| Event | Description |
|-------|-------------|
| `opportunity.created` | New opportunity posted |
| `opportunity.updated` | Opportunity details changed |
| `match.created` | User matched with opportunity |
| `application.submitted` | New application received |
| `payment.completed` | Payment processed |
| `payment.failed` | Payment failed |
| `review.created` | New review submitted |
| `message.received` | New message received |

### Webhook Payload

```json
{
  "event": "opportunity.created",
  "timestamp": "2025-12-16T10:30:00Z",
  "data": {
    "opportunity_id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Python Developer",
    "employer_id": "661f9511-f3ac-52e5-b827-557766551111"
  }
}
```

### Verifying Webhooks

Verify webhook signatures using HMAC-SHA256:

```python
import hmac
import hashlib

def verify_webhook(payload, signature, secret):
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)
```

---

## SDKs & Libraries

### Official SDKs

- **Python:** `pip install trybe-sdk`
- **JavaScript/TypeScript:** `npm install @trybe/sdk`
- **Mobile (React Native):** `npm install @trybe/react-native-sdk`

### Python SDK Example

```python
from trybe import TrybeClient

client = TrybeClient(api_key="your_api_key")

# Search nearby opportunities
opportunities = client.opportunities.search_nearby(
    latitude=6.5244,
    longitude=3.3792,
    radius_km=25
)

for opp in opportunities:
    print(f"{opp.title} - {opp.distance_text}")
```

### JavaScript SDK Example

```javascript
import { TrybeClient } from '@trybe/sdk';

const client = new TrybeClient({ apiKey: 'your_api_key' });

// Get opportunities
const opportunities = await client.opportunities.list({
  status: 'open',
  isRemote: true
});
```

---

## Best Practices

### 1. Use Pagination
Always use pagination for list endpoints to avoid large responses.

### 2. Handle Rate Limits
Implement exponential backoff when rate limited.

### 3. Cache Responses
Cache responses where appropriate to reduce API calls.

### 4. Use Webhooks
Use webhooks for real-time updates instead of polling.

### 5. Error Handling
Always handle errors gracefully and provide user feedback.

### 6. Security
- Never expose API keys in client-side code
- Use HTTPS in production
- Validate webhook signatures
- Refresh tokens before expiration

---

## Support & Resources

- **API Status:** https://status.trybe.app
- **Interactive API Docs:** http://localhost:8000/docs
- **Support:** support@trybe.app
- **GitHub:** https://github.com/trybe/api
- **Community:** https://community.trybe.app

---

*Last updated: December 16, 2025*  
*API Version: 0.5.0*
