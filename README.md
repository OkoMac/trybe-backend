# 🚀 Trybe Platform - Backend API

> **A comprehensive opportunity marketplace and talent management platform built with FastAPI and PostgreSQL**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-Proprietary-red)]()

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [API Documentation](#api-documentation)
- [Environment Configuration](#environment-configuration)
- [Deployment](#deployment)
- [Contributing](#contributing)

## 🎯 Overview

**Trybe** is a production-ready platform that connects employers, freelancers, learners, and service providers in a secure, feature-rich ecosystem. With 215+ API endpoints, it provides everything needed to run a modern talent marketplace.

**Key Metrics:**
- ✅ **215 API Endpoints**
- ✅ **20+ Services**
- ✅ **8 External Integrations**
- ✅ **~99% Complete**
- ✅ **Production Ready**

## ✨ Features

### Core Platform
- 🔐 **Authentication & Authorization** - JWT-based with role-based access control
- 💼 **Opportunity Marketplace** - Jobs, gigs, internships with advanced search
- 💳 **Payment Processing** - Stripe integration with escrow system
- 💬 **Messaging System** - Real-time direct messaging
- 🔔 **Multi-Channel Notifications** - Email, SMS, WhatsApp, Push
- 📚 **Learning Management** - Courses, quizzes, certificates
- 🎯 **Aptitude Testing** - Automated testing with scoring

### Advanced Features
- 🤖 **AI Career Assistant** - Resume analysis, job matching, career guidance (OpenAI + Anthropic)
- 📄 **Resume Parser** - AI-powered PDF/DOCX parsing with ATS scoring
- 🔍 **Elasticsearch Search** - Full-text search with fuzzy matching
- 📹 **Video Calls** - Virtual interviews via Twilio (1-on-1 and group)
- 🔒 **Payment Escrow** - Secure fund holding with dispute resolution
- ⭐ **Reviews & Ratings** - 5-star system with verified reviews
- 📊 **Analytics & Reporting** - Comprehensive platform metrics

### Integrations
- Stripe (Payments)
- Twilio (SMS, WhatsApp, Video)
- SendGrid (Email)
- Firebase (Push Notifications)
- OpenAI (AI Features)
- Anthropic Claude (AI Features)
- Sentry (Error Tracking)
- Elasticsearch (Search)

## 🛠 Tech Stack

**Backend:**
- FastAPI (Python 3.11+)
- PostgreSQL (Database)
- SQLAlchemy (Async ORM)
- Pydantic (Data Validation)
- Alembic (Migrations)

**Services:**
- Redis (Caching)
- Elasticsearch (Search)
- Celery (Background Tasks)

**External APIs:**
- Stripe, Twilio, SendGrid, Firebase, OpenAI, Anthropic, Sentry

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+ (optional, for caching)
- Elasticsearch 8+ (optional, for search)
- Docker & Docker Compose (optional, for containerized setup)

### Quick Start (Local)

1. **Clone the repository**
```bash
git clone https://github.com/OkoMac/trybe-backend.git
cd trybe-backend
```

2. **Set up virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your credentials
```

5. **Run database migrations**
```bash
alembic upgrade head
```

6. **Start the server**
```bash
uvicorn app.main:app --reload
```

7. **Access the API**
- API: http://localhost:8000
- Documentation: http://localhost:8000/docs
- Alternative Docs: http://localhost:8000/redoc

### Quick Start (Docker)

1. **Clone and configure**
```bash
git clone https://github.com/OkoMac/trybe-backend.git
cd trybe-backend
cp .env.example .env
# Edit .env with your credentials
```

2. **Start all services**
```bash
docker-compose up -d
```

3. **Run migrations**
```bash
docker-compose exec api alembic upgrade head
```

4. **Access the API**
- API: http://localhost:8000
- Documentation: http://localhost:8000/docs
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- Elasticsearch: localhost:9200

## 📚 API Documentation

### Interactive Documentation

Once the server is running, access the auto-generated documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### API Modules (22)

1. **Authentication** - `/api/v1/auth`
2. **Opportunities** - `/api/v1/opportunities`
3. **Payments** - `/api/v1/payments`
4. **Escrow** - `/api/v1/escrow`
5. **Messages** - `/api/v1/messages`
6. **Notifications** - `/api/v1/notifications`
7. **Learning** - `/api/v1/learning`
8. **Aptitude Tests** - `/api/v1/aptitude`
9. **Analytics** - `/api/v1/analytics`
10. **Reports** - `/api/v1/reports`
11. **Hackathons** - `/api/v1/hackathons`
12. **Community** - `/api/v1/community`
13. **Solar** - `/api/v1/solar`
14. **Admin** - `/api/v1/admin`
15. **Files** - `/api/v1/files`
16. **Reviews** - `/api/v1/reviews`
17. **Push Notifications** - `/api/v1/push-notifications`
18. **WhatsApp** - `/api/v1/whatsapp`
19. **Career Assistant** - `/api/v1/career`
20. **Emails** - `/api/v1/emails`
21. **Resume Parser** - `/api/v1/resume`
22. **Search** - `/api/v1/search`
23. **Video Calls** - `/api/v1/video-calls`

### Detailed Guides

- [Elasticsearch Guide](ELASTICSEARCH_GUIDE.md)
- [Video Calls Guide](VIDEO_CALLS_GUIDE.md)
- [Payment Escrow Guide](PAYMENT_ESCROW_GUIDE.md)
- [Email Templates Guide](EMAIL_TEMPLATES_GUIDE.md)
- [Resume Parser Guide](RESUME_PARSER_GUIDE.md)
- [Platform Summary](PLATFORM_SUMMARY.md)

## ⚙️ Environment Configuration

### Required Environment Variables

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/trybe

# Security
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Stripe
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_PUBLIC_KEY=pk_test_xxx

# Twilio (optional)
TWILIO_ACCOUNT_SID=ACxxx
TWILIO_AUTH_TOKEN=xxx

# Email (optional)
SENDGRID_API_KEY=SG.xxx

# AI Services (optional)
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
```

See [.env.example](.env.example) for complete configuration options.

## 🚢 Deployment

### Production Checklist

- [ ] Set `DEBUG=false`
- [ ] Use strong `SECRET_KEY`
- [ ] Configure CORS for production domains
- [ ] Set up SSL/TLS certificates
- [ ] Enable Sentry error tracking
- [ ] Configure backup strategy
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure rate limiting
- [ ] Set up logging
- [ ] Test all external integrations

### Deploy with Docker

```bash
# Build production image
docker build -t trybe-api:latest .

# Run with docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

### Deploy to Cloud

**AWS:**
- Use ECS/Fargate for containers
- RDS for PostgreSQL
- ElastiCache for Redis
- CloudWatch for logging

**DigitalOcean:**
- App Platform for easy deployment
- Managed Database for PostgreSQL
- Spaces for file storage

**Heroku:**
```bash
heroku create trybe-api
heroku addons:create heroku-postgresql:standard-0
git push heroku main
```

## 🧪 Testing

Run tests:
```bash
pytest

# With coverage
pytest --cov=app --cov-report=html
```

## 📊 Database Migrations

Create migration:
```bash
alembic revision --autogenerate -m "Description"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback:
```bash
alembic downgrade -1
```

## 🔒 Security

- JWT authentication with refresh tokens
- Password hashing with bcrypt
- Rate limiting on sensitive endpoints
- SQL injection prevention (SQLAlchemy ORM)
- XSS protection
- CORS configuration
- Input validation (Pydantic)
- Sentry error tracking
- API key authentication for admin routes

## 📈 Performance

- Async/await throughout (FastAPI + AsyncIO)
- Database connection pooling
- Elasticsearch for fast search
- Redis caching (optional)
- CDN-ready file storage
- Background tasks with Celery

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is proprietary software. All rights reserved.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database ORM
- [Stripe](https://stripe.com/) - Payment processing
- [Twilio](https://www.twilio.com/) - Communication services
- [OpenAI](https://openai.com/) & [Anthropic](https://www.anthropic.com/) - AI capabilities

## 📞 Support

For support and questions:
- GitHub Issues: [Create an issue](https://github.com/OkoMac/trybe-backend/issues)
- Documentation: See `/docs` folder
- API Reference: http://localhost:8000/docs

---

**Built with ❤️ using FastAPI**

*Last Updated: 2024-01-15 | Version: 1.0.0 | Status: Production Ready*
