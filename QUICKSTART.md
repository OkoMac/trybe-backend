# Trybe Backend - Quick Start Guide

## 🎉 Backend is Running!

Your Trybe backend is now successfully deployed with Docker.

---

## 🌐 Access Points

| Service | URL | Description |
|---------|-----|-------------|
| **API** | http://localhost:8000 | Main API endpoint |
| **Health Check** | http://localhost:8000/health | Service health status |
| **API Docs (Swagger)** | http://localhost:8000/docs | Interactive API documentation |
| **ReDoc** | http://localhost:8000/redoc | Alternative API docs |
| **PostgreSQL** | localhost:5433 | Database (port changed to avoid conflict) |
| **Redis** | localhost:6380 | Cache (port changed to avoid conflict) |

---

## ✅ What's Working

- ✅ **FastAPI** application running on port 8000
- ✅ **PostgreSQL 16** database (healthy)
- ✅ **Redis 7** cache (healthy)
- ✅ **User model** created with SQLAlchemy
- ✅ **Alembic** migrations configured
- ✅ **CORS** enabled for frontend development
- ✅ **Health check** endpoints
- ✅ **Auto-generated API docs**

---

## 🚀 Quick Commands

### View Logs
```bash
# All services
docker-compose logs -f

# Backend only
docker-compose logs -f backend

# PostgreSQL
docker-compose logs -f postgres

# Redis
docker-compose logs -f redis
```

### Manage Services
```bash
# Stop all services
docker-compose down

# Start all services
docker-compose up -d

# Restart backend
docker-compose restart backend

# View running services
docker-compose ps
```

### Database Operations
```bash
# Create a new migration
docker-compose exec backend alembic revision --autogenerate -m "description"

# Run migrations
docker-compose exec backend alembic upgrade head

# Rollback one migration
docker-compose exec backend alembic downgrade -1

# Access PostgreSQL directly
docker-compose exec postgres psql -U trybe_user -d trybe_db
```

### Redis Operations
```bash
# Access Redis CLI
docker-compose exec redis redis-cli -a redis_password_dev

# Test Redis
docker-compose exec redis redis-cli -a redis_password_dev ping
```

---

## 📊 Test the API

### Using curl:
```bash
# Health check
curl http://localhost:8000/health

# Root endpoint
curl http://localhost:8000/

# Readiness check
curl http://localhost:8000/health/ready
```

### Using browser:
- Open http://localhost:8000/docs for interactive API testing

---

## 🔧 Configuration

### Environment Variables
Edit `/Users/oko/Documents/Builds/Trybe/backend/.env` to configure:

```bash
# Database (using port 5433 to avoid conflict with ItsonWorx)
DB_PORT=5433

# Redis (using port 6380 to avoid conflict with ItsonWorx)
REDIS_PORT=6380

# JWT Secret (change in production!)
SECRET_KEY=your-super-secret-jwt-key-min-32-characters

# API Keys (add when ready)
OPENAI_API_KEY=sk-...
STRIPE_API_KEY=sk_test_...
```

---

## 📁 Project Structure

```
backend/
├── app/
│   ├── main.py               # FastAPI application ✅
│   ├── core/
│   │   ├── config.py         # Settings ✅
│   │   ├── database.py       # PostgreSQL connection ✅
│   │   └── redis.py          # Redis connection ✅
│   ├── models/
│   │   └── user.py           # User model ✅
│   ├── schemas/
│   │   └── user.py           # Pydantic schemas ✅
│   ├── api/v1/endpoints/     # API routes (ready to add)
│   ├── services/             # Business logic (ready to add)
│   └── tasks/                # Celery tasks (ready to add)
├── alembic/                  # Database migrations ✅
├── docker-compose.yml        # Docker orchestration ✅
├── Dockerfile                # Production image ✅
├── Dockerfile.dev            # Development image ✅
└── .env                      # Environment config ✅
```

---

## 🎯 Next Steps

### 1. Create First Migration
```bash
docker-compose exec backend alembic revision --autogenerate -m "create users table"
docker-compose exec backend alembic upgrade head
```

### 2. Add Authentication Endpoint
Create `/Users/oko/Documents/Builds/Trybe/backend/app/api/v1/endpoints/auth.py`

### 3. Add Opportunities API
Create `/Users/oko/Documents/Builds/Trybe/backend/app/api/v1/endpoints/opportunities.py`

### 4. Connect Frontend
Update frontend `.env`:
```bash
VITE_API_URL=http://localhost:8000/api/v1
```

---

## 🐛 Troubleshooting

### Backend won't start
```bash
# Check logs
docker-compose logs backend

# Restart services
docker-compose restart backend
```

### Database connection issues
```bash
# Check PostgreSQL is healthy
docker-compose ps postgres

# Test connection
docker-compose exec backend python -c "from app.core.database import check_db_health; import asyncio; print(asyncio.run(check_db_health()))"
```

### Port conflicts
If you see "port is already allocated":
- Ports 5433 and 6380 are used to avoid conflict with ItsonWorx containers
- Check `.env` file has correct ports
- Stop conflicting services or change ports in `.env`

---

## 📚 Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com
- **SQLAlchemy Docs**: https://docs.sqlalchemy.org
- **Alembic Docs**: https://alembic.sqlalchemy.org
- **Pydantic Docs**: https://docs.pydantic.dev

---

## ✨ Ready to Build!

Your backend infrastructure is ready. You can now:
1. Add API endpoints for each Trybe module
2. Connect the frontend to real backend data
3. Implement Stripe payment processing
4. Add OpenAI integration for AI features
5. Build out the complete Trybe platform!

Happy coding! 🚀
