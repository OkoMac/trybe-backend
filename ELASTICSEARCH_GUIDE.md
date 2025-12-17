# Elasticsearch Integration Guide

## Overview

The Trybe platform integrates Elasticsearch to provide powerful full-text search capabilities across opportunities, users, companies, and courses. This guide covers setup, usage, and best practices.

## Features

### Search Capabilities
- **Full-text search** with fuzzy matching for typo tolerance
- **Faceted search** with aggregations for filtering UIs
- **Autocomplete** suggestions for search-as-you-type experiences
- **Geo-location search** for location-based filtering
- **Multi-field search** across titles, descriptions, skills, and more
- **Advanced filtering** by salary, skills, experience level, location, etc.
- **Sorting options** by relevance, date, salary, and custom fields

### Supported Entities
1. **Opportunities** - Jobs, gigs, internships, volunteer positions
2. **Users** - Find talent, collaborators, and network connections
3. **Companies** - Discover employers and industry leaders
4. **Courses** - Search learning resources by skills and topics

## Setup

### 1. Install Elasticsearch

**Using Docker (Recommended):**
```bash
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -p 9300:9300 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  docker.elastic.co/elasticsearch/elasticsearch:8.11.0
```

**Using Docker Compose:**
```yaml
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    container_name: trybe-elasticsearch
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
      - xpack.security.enabled=false
    ports:
      - "9200:9200"
      - "9300:9300"
    volumes:
      - elasticsearch-data:/usr/share/elasticsearch/data
    networks:
      - trybe-network

volumes:
  elasticsearch-data:
```

### 2. Environment Configuration

Add to `.env`:
```env
# Elasticsearch Configuration
ELASTICSEARCH_HOST=localhost:9200
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=your-password-here
```

### 3. Install Python Dependencies

Add to `requirements.txt`:
```
elasticsearch>=8.11.0
```

Install:
```bash
pip install elasticsearch
```

### 4. Create Indices

Initialize Elasticsearch indices (run once):

```bash
# Using curl
curl -X POST http://localhost:8000/api/v1/search/admin/indices/create \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"

# Or using Python
python -c "
from app.services.elasticsearch_service import elasticsearch_service
import asyncio
asyncio.run(elasticsearch_service.create_indices())
"
```

### 5. Index Existing Data

Reindex data from your database:

```bash
# Reindex opportunities
curl -X POST http://localhost:8000/api/v1/search/admin/reindex/opportunities \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

## API Endpoints

### Search Endpoints

#### 1. Search Opportunities
```http
POST /api/v1/search/opportunities
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{
  "query": "software engineer",
  "location": "San Francisco",
  "remote": true,
  "salary_min": 100000,
  "skills": ["python", "react"],
  "experience_level": "mid",
  "page": 1,
  "page_size": 20,
  "sort_by": "_score"
}
```

**Response:**
```json
{
  "results": [
    {
      "id": "uuid",
      "title": "Senior Software Engineer",
      "description": "...",
      "company_name": "Tech Corp",
      "location": "San Francisco, CA",
      "remote": true,
      "salary_min": 120000,
      "salary_max": 180000,
      "skills_required": ["python", "react", "docker"],
      "score": 12.5
    }
  ],
  "total": 156,
  "page": 1,
  "page_size": 20,
  "total_pages": 8,
  "aggregations": {
    "categories": [
      {"key": "software_development", "count": 89},
      {"key": "data_science", "count": 34}
    ],
    "locations": [
      {"key": "San Francisco, CA", "count": 45},
      {"key": "New York, NY", "count": 32}
    ],
    "experience_levels": [
      {"key": "mid", "count": 67},
      {"key": "senior", "count": 54}
    ],
    "salary_ranges": [
      {"key": "100k-150k", "count": 78},
      {"key": "150k+", "count": 45}
    ]
  }
}
```

#### 2. Quick Search (GET)
```http
GET /api/v1/search/opportunities/quick?q=python&location=remote&page=1&page_size=10
Authorization: Bearer YOUR_TOKEN
```

#### 3. Search Users
```http
POST /api/v1/search/users
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{
  "query": "python developer",
  "skills": ["python", "django"],
  "location": "New York",
  "experience_level": "senior",
  "page": 1,
  "page_size": 20
}
```

#### 4. Search Companies
```http
POST /api/v1/search/companies
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{
  "query": "tech startup",
  "industry": "software",
  "location": "Silicon Valley",
  "page": 1,
  "page_size": 20
}
```

#### 5. Autocomplete
```http
POST /api/v1/search/autocomplete
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{
  "query": "soft",
  "field": "title",
  "index_type": "opportunities",
  "limit": 10
}
```

**Response:**
```json
{
  "suggestions": [
    "Software Engineer",
    "Software Developer",
    "Software Architect",
    "Software Tester",
    "Software Manager"
  ],
  "query": "soft"
}
```

### Admin Endpoints (Admin Only)

#### 1. Create Indices
```http
POST /api/v1/search/admin/indices/create
Authorization: Bearer ADMIN_TOKEN
```

#### 2. Delete Index
```http
DELETE /api/v1/search/admin/indices/opportunities
Authorization: Bearer ADMIN_TOKEN
```

#### 3. Reindex Data
```http
POST /api/v1/search/admin/reindex/opportunities
Authorization: Bearer ADMIN_TOKEN
```

#### 4. Get Statistics
```http
GET /api/v1/search/admin/stats
Authorization: Bearer ADMIN_TOKEN
```

**Response:**
```json
{
  "opportunities": {
    "total_documents": 1245,
    "index_name": "trybe_opportunities"
  },
  "users": {
    "total_documents": 5678,
    "index_name": "trybe_users"
  },
  "companies": {
    "total_documents": 234,
    "index_name": "trybe_companies"
  },
  "courses": {
    "total_documents": 456,
    "index_name": "trybe_courses"
  }
}
```

### Utility Endpoints

#### 1. Health Check
```http
GET /api/v1/search/health
```

**Response:**
```json
{
  "connected": true,
  "cluster_name": "docker-cluster",
  "version": "8.11.0"
}
```

#### 2. Supported Filters
```http
GET /api/v1/search/supported-filters
```

## Integration with Your App

### Automatic Indexing

Index documents automatically when they're created or updated:

```python
# In your opportunity creation endpoint
from app.services.elasticsearch_service import elasticsearch_service

@router.post("/opportunities")
async def create_opportunity(
    opportunity_data: OpportunityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Create in database
    opportunity = Opportunity(**opportunity_data.dict())
    db.add(opportunity)
    await db.commit()
    await db.refresh(opportunity)

    # Index in Elasticsearch
    await elasticsearch_service.index_opportunity(opportunity)

    return opportunity
```

### Update Index on Changes

```python
# In your opportunity update endpoint
@router.put("/opportunities/{opportunity_id}")
async def update_opportunity(
    opportunity_id: str,
    updates: OpportunityUpdate,
    db: AsyncSession = Depends(get_db)
):
    # Update in database
    opportunity = await db.get(Opportunity, opportunity_id)
    for key, value in updates.dict(exclude_unset=True).items():
        setattr(opportunity, key, value)
    await db.commit()

    # Update in Elasticsearch
    await elasticsearch_service.index_opportunity(opportunity)

    return opportunity
```

### Delete from Index

```python
# In your opportunity deletion endpoint
@router.delete("/opportunities/{opportunity_id}")
async def delete_opportunity(
    opportunity_id: str,
    db: AsyncSession = Depends(get_db)
):
    # Delete from database
    opportunity = await db.get(Opportunity, opportunity_id)
    await db.delete(opportunity)
    await db.commit()

    # Delete from Elasticsearch
    await elasticsearch_service.delete_document("opportunities", str(opportunity_id))

    return {"message": "Deleted successfully"}
```

## Frontend Integration

### Search Component Example (React)

```javascript
import React, { useState, useEffect } from 'react';
import axios from 'axios';

function OpportunitySearch() {
  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState({
    location: '',
    remote: null,
    salary_min: null,
    skills: [],
    experience_level: ''
  });
  const [results, setResults] = useState([]);
  const [aggregations, setAggregations] = useState({});
  const [loading, setLoading] = useState(false);

  const searchOpportunities = async () => {
    setLoading(true);
    try {
      const response = await axios.post('/api/v1/search/opportunities', {
        query,
        ...filters,
        page: 1,
        page_size: 20
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });

      setResults(response.data.results);
      setAggregations(response.data.aggregations);
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const debounce = setTimeout(() => {
      if (query.length >= 2) {
        searchOpportunities();
      }
    }, 500);

    return () => clearTimeout(debounce);
  }, [query, filters]);

  return (
    <div>
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search opportunities..."
      />

      {/* Filters */}
      <div className="filters">
        <input
          type="text"
          placeholder="Location"
          value={filters.location}
          onChange={(e) => setFilters({...filters, location: e.target.value})}
        />

        <label>
          <input
            type="checkbox"
            checked={filters.remote}
            onChange={(e) => setFilters({...filters, remote: e.target.checked})}
          />
          Remote only
        </label>

        {/* Salary filter */}
        <input
          type="number"
          placeholder="Min salary"
          value={filters.salary_min || ''}
          onChange={(e) => setFilters({...filters, salary_min: parseInt(e.target.value)})}
        />
      </div>

      {/* Results */}
      {loading ? (
        <p>Loading...</p>
      ) : (
        <div className="results">
          {results.map((opp) => (
            <div key={opp.id} className="opportunity-card">
              <h3>{opp.title}</h3>
              <p>{opp.company_name}</p>
              <p>{opp.location}</p>
              <p>{opp.salary_min} - {opp.salary_max} {opp.currency}</p>
              <div className="skills">
                {opp.skills_required.map(skill => (
                  <span key={skill} className="skill-tag">{skill}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Facets (Aggregations) */}
      <div className="facets">
        <h4>Categories</h4>
        {aggregations.categories?.map(cat => (
          <label key={cat.key}>
            <input type="checkbox" />
            {cat.key} ({cat.count})
          </label>
        ))}
      </div>
    </div>
  );
}
```

### Autocomplete Example

```javascript
import React, { useState, useEffect } from 'react';
import axios from 'axios';

function SearchAutocomplete() {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);

  useEffect(() => {
    const fetchSuggestions = async () => {
      if (query.length < 2) {
        setSuggestions([]);
        return;
      }

      try {
        const response = await axios.post('/api/v1/search/autocomplete', {
          query,
          field: 'title',
          index_type: 'opportunities',
          limit: 10
        }, {
          headers: { Authorization: `Bearer ${token}` }
        });

        setSuggestions(response.data.suggestions);
      } catch (error) {
        console.error('Autocomplete failed:', error);
      }
    };

    const debounce = setTimeout(fetchSuggestions, 300);
    return () => clearTimeout(debounce);
  }, [query]);

  return (
    <div className="autocomplete">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search..."
      />

      {suggestions.length > 0 && (
        <ul className="suggestions">
          {suggestions.map((suggestion, index) => (
            <li key={index} onClick={() => setQuery(suggestion)}>
              {suggestion}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

## Advanced Search Features

### Fuzzy Matching

Elasticsearch automatically handles typos and misspellings:

```
Query: "sofware engineer" → Matches: "Software Engineer"
Query: "pythn" → Matches: "Python"
```

### Proximity Search

Search for terms that appear near each other:

```python
{
  "query": {
    "match_phrase": {
      "description": {
        "query": "machine learning engineer",
        "slop": 2  # Allow 2 words between terms
      }
    }
  }
}
```

### Boosting

Boost certain fields to prioritize them:

```python
# In elasticsearch_service.py search method
"multi_match": {
  "query": query,
  "fields": [
    "title^3",      # 3x boost
    "description^2", # 2x boost
    "skills_required"
  ]
}
```

### Geo-Location Search

Search opportunities near a location:

```python
# Add to search query
{
  "bool": {
    "filter": {
      "geo_distance": {
        "distance": "50km",
        "location_geo": {
          "lat": 37.7749,
          "lon": -122.4194
        }
      }
    }
  }
}
```

## Performance Optimization

### 1. Index Settings

Optimize for your use case:

```python
# For faster indexing (bulk operations)
{
  "settings": {
    "refresh_interval": "30s",  # Default: 1s
    "number_of_replicas": 0     # During bulk indexing
  }
}

# For production
{
  "settings": {
    "refresh_interval": "1s",
    "number_of_replicas": 1
  }
}
```

### 2. Pagination

Use `from` and `size` carefully:

```python
# Good: Small offsets
page = 1, page_size = 20  # from=0, size=20

# Bad: Large offsets (slow)
page = 1000, page_size = 20  # from=19980, size=20

# Better: Use search_after for deep pagination
```

### 3. Caching

Elasticsearch caches frequently accessed queries. Leverage this by:
- Using consistent query structures
- Caching aggregation results
- Using filter context (cached) vs query context (not cached)

### 4. Monitoring

Monitor Elasticsearch health:

```bash
# Check cluster health
curl http://localhost:9200/_cluster/health

# Check index stats
curl http://localhost:9200/trybe_opportunities/_stats

# Monitor slow queries
curl http://localhost:9200/_nodes/stats/indices/search
```

## Troubleshooting

### Connection Issues

**Problem:** Cannot connect to Elasticsearch

**Solution:**
```bash
# Check if Elasticsearch is running
curl http://localhost:9200

# Check Docker container
docker ps | grep elasticsearch

# Check logs
docker logs elasticsearch
```

### Index Not Found

**Problem:** `IndexNotFoundException`

**Solution:**
```bash
# Create indices
curl -X POST http://localhost:8000/api/v1/search/admin/indices/create
```

### Slow Searches

**Problem:** Searches taking too long

**Solutions:**
1. Reduce `page_size`
2. Use filters instead of queries when possible
3. Limit aggregations
4. Add more Elasticsearch nodes
5. Optimize index mappings

### Memory Issues

**Problem:** Elasticsearch runs out of memory

**Solutions:**
```bash
# Increase heap size (in docker-compose.yml)
environment:
  - "ES_JAVA_OPTS=-Xms2g -Xmx2g"  # 2GB heap

# Or adjust based on available RAM (50% of total RAM)
```

## Best Practices

1. **Always index asynchronously** - Don't make users wait for indexing
2. **Use background tasks** - Index in background using Celery or similar
3. **Handle failures gracefully** - Don't fail API requests if indexing fails
4. **Keep database as source of truth** - Elasticsearch is for search only
5. **Reindex periodically** - Schedule reindexing to catch any missed updates
6. **Monitor performance** - Track search query performance
7. **Use appropriate analyzers** - Choose analyzers based on your data
8. **Implement access control** - Don't expose sensitive data in search results
9. **Version your indices** - Use index aliases for zero-downtime reindexing
10. **Test with production-like data** - Search quality depends on data volume

## Security Considerations

### 1. Access Control

Filter search results based on user permissions:

```python
# In search service
filter_clauses.append({
  "term": {"is_active": True}
})

# For private opportunities
if not user.is_admin:
    filter_clauses.append({
        "bool": {
            "should": [
                {"term": {"is_public": True}},
                {"term": {"created_by": str(user.id)}}
            ]
        }
    })
```

### 2. Data Sanitization

Don't index sensitive data:

```python
# Exclude sensitive fields
doc = {
    "id": str(user.id),
    "full_name": user.full_name,
    "bio": user.bio,
    # DON'T index: email, phone, SSN, passwords
}
```

### 3. Rate Limiting

Implement rate limiting for search endpoints:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/opportunities")
@limiter.limit("30/minute")  # 30 searches per minute
async def search_opportunities(...):
    pass
```

## Maintenance

### Regular Tasks

1. **Daily:** Monitor cluster health
2. **Weekly:** Review slow query logs
3. **Monthly:** Reindex all data
4. **Quarterly:** Review and optimize mappings
5. **Annually:** Upgrade Elasticsearch version

### Backup Strategy

```bash
# Create snapshot repository
curl -X PUT "localhost:9200/_snapshot/trybe_backup" -H 'Content-Type: application/json' -d'
{
  "type": "fs",
  "settings": {
    "location": "/backup/elasticsearch"
  }
}'

# Create snapshot
curl -X PUT "localhost:9200/_snapshot/trybe_backup/snapshot_1?wait_for_completion=true"

# Restore snapshot
curl -X POST "localhost:9200/_snapshot/trybe_backup/snapshot_1/_restore"
```

## Additional Resources

- [Elasticsearch Official Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Elasticsearch Python Client](https://elasticsearch-py.readthedocs.io/)
- [Search UI Best Practices](https://www.elastic.co/guide/en/app-search/current/search-ui.html)
- [Elasticsearch Performance Tuning](https://www.elastic.co/guide/en/elasticsearch/reference/current/tune-for-search-speed.html)

## Summary

The Elasticsearch integration provides:
- **14 API endpoints** for comprehensive search functionality
- **Full-text search** with fuzzy matching across all entities
- **Faceted search** with aggregations for filtering
- **Autocomplete** for search-as-you-type
- **Admin tools** for index management
- **Production-ready** with proper error handling and security

Total Endpoints: **180** (166 + 14 search endpoints)
Platform Completeness: **~96%**
