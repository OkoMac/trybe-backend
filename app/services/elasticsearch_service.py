"""
Elasticsearch Service for Trybe Platform
Provides full-text search capabilities for opportunities, users, companies, and courses
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from elasticsearch import AsyncElasticsearch, helpers
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
import os

from app.models.user import User
from app.models.opportunity import Opportunity
from app.models.company import Company
from app.models.course import Course

logger = logging.getLogger(__name__)


class ElasticsearchService:
    """Service for Elasticsearch operations"""

    def __init__(self):
        """Initialize Elasticsearch client"""
        self.es_host = os.getenv("ELASTICSEARCH_HOST", "localhost:9200")
        self.es_username = os.getenv("ELASTICSEARCH_USERNAME", "elastic")
        self.es_password = os.getenv("ELASTICSEARCH_PASSWORD", "")

        # Initialize client
        self.client = AsyncElasticsearch(
            [self.es_host],
            basic_auth=(self.es_username, self.es_password) if self.es_password else None,
            verify_certs=False
        )

        # Index names
        self.indices = {
            "opportunities": "trybe_opportunities",
            "users": "trybe_users",
            "companies": "trybe_companies",
            "courses": "trybe_courses"
        }

    async def close(self):
        """Close Elasticsearch connection"""
        await self.client.close()

    # ==================== Index Management ====================

    async def create_indices(self):
        """Create all search indices with mappings"""
        await self._create_opportunities_index()
        await self._create_users_index()
        await self._create_companies_index()
        await self._create_courses_index()
        logger.info("All Elasticsearch indices created successfully")

    async def _create_opportunities_index(self):
        """Create opportunities index"""
        index_name = self.indices["opportunities"]

        if await self.client.indices.exists(index=index_name):
            logger.info(f"Index {index_name} already exists")
            return

        mapping = {
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "title": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {
                            "keyword": {"type": "keyword"},
                            "suggest": {
                                "type": "completion",
                                "analyzer": "simple"
                            }
                        }
                    },
                    "description": {"type": "text", "analyzer": "standard"},
                    "company_name": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}}
                    },
                    "company_id": {"type": "keyword"},
                    "category": {"type": "keyword"},
                    "type": {"type": "keyword"},
                    "location": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}}
                    },
                    "location_geo": {"type": "geo_point"},
                    "remote": {"type": "boolean"},
                    "salary_min": {"type": "integer"},
                    "salary_max": {"type": "integer"},
                    "currency": {"type": "keyword"},
                    "skills_required": {"type": "keyword"},
                    "experience_level": {"type": "keyword"},
                    "deadline": {"type": "date"},
                    "status": {"type": "keyword"},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"},
                    "is_active": {"type": "boolean"},
                    "application_count": {"type": "integer"},
                    "view_count": {"type": "integer"}
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 1,
                "analysis": {
                    "analyzer": {
                        "autocomplete": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "autocomplete_filter"]
                        }
                    },
                    "filter": {
                        "autocomplete_filter": {
                            "type": "edge_ngram",
                            "min_gram": 2,
                            "max_gram": 20
                        }
                    }
                }
            }
        }

        await self.client.indices.create(index=index_name, body=mapping)
        logger.info(f"Created index: {index_name}")

    async def _create_users_index(self):
        """Create users index"""
        index_name = self.indices["users"]

        if await self.client.indices.exists(index=index_name):
            logger.info(f"Index {index_name} already exists")
            return

        mapping = {
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "email": {"type": "keyword"},
                    "full_name": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {
                            "keyword": {"type": "keyword"},
                            "suggest": {"type": "completion"}
                        }
                    },
                    "username": {"type": "keyword"},
                    "bio": {"type": "text"},
                    "location": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}}
                    },
                    "location_geo": {"type": "geo_point"},
                    "skills": {"type": "keyword"},
                    "interests": {"type": "keyword"},
                    "experience_level": {"type": "keyword"},
                    "user_type": {"type": "keyword"},
                    "is_verified": {"type": "boolean"},
                    "is_active": {"type": "boolean"},
                    "created_at": {"type": "date"},
                    "profile_completion": {"type": "integer"}
                }
            }
        }

        await self.client.indices.create(index=index_name, body=mapping)
        logger.info(f"Created index: {index_name}")

    async def _create_companies_index(self):
        """Create companies index"""
        index_name = self.indices["companies"]

        if await self.client.indices.exists(index=index_name):
            logger.info(f"Index {index_name} already exists")
            return

        mapping = {
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "name": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {
                            "keyword": {"type": "keyword"},
                            "suggest": {"type": "completion"}
                        }
                    },
                    "description": {"type": "text"},
                    "industry": {"type": "keyword"},
                    "size": {"type": "keyword"},
                    "location": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}}
                    },
                    "location_geo": {"type": "geo_point"},
                    "website": {"type": "keyword"},
                    "is_verified": {"type": "boolean"},
                    "created_at": {"type": "date"},
                    "active_opportunities_count": {"type": "integer"}
                }
            }
        }

        await self.client.indices.create(index=index_name, body=mapping)
        logger.info(f"Created index: {index_name}")

    async def _create_courses_index(self):
        """Create courses index"""
        index_name = self.indices["courses"]

        if await self.client.indices.exists(index=index_name):
            logger.info(f"Index {index_name} already exists")
            return

        mapping = {
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "title": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {
                            "keyword": {"type": "keyword"},
                            "suggest": {"type": "completion"}
                        }
                    },
                    "description": {"type": "text"},
                    "category": {"type": "keyword"},
                    "level": {"type": "keyword"},
                    "skills_taught": {"type": "keyword"},
                    "instructor_name": {"type": "text"},
                    "duration_weeks": {"type": "integer"},
                    "price": {"type": "float"},
                    "rating": {"type": "float"},
                    "enrollment_count": {"type": "integer"},
                    "is_active": {"type": "boolean"},
                    "created_at": {"type": "date"}
                }
            }
        }

        await self.client.indices.create(index=index_name, body=mapping)
        logger.info(f"Created index: {index_name}")

    async def delete_index(self, index_type: str):
        """Delete an index"""
        index_name = self.indices.get(index_type)
        if not index_name:
            raise ValueError(f"Invalid index type: {index_type}")

        if await self.client.indices.exists(index=index_name):
            await self.client.indices.delete(index=index_name)
            logger.info(f"Deleted index: {index_name}")
        else:
            logger.info(f"Index {index_name} does not exist")

    # ==================== Indexing Operations ====================

    async def index_opportunity(self, opportunity: Opportunity):
        """Index a single opportunity"""
        index_name = self.indices["opportunities"]

        doc = {
            "id": str(opportunity.id),
            "title": opportunity.title,
            "description": opportunity.description,
            "company_name": opportunity.company.name if opportunity.company else "",
            "company_id": str(opportunity.company_id) if opportunity.company_id else None,
            "category": opportunity.category,
            "type": opportunity.opportunity_type,
            "location": opportunity.location,
            "remote": opportunity.remote,
            "salary_min": opportunity.salary_min,
            "salary_max": opportunity.salary_max,
            "currency": opportunity.currency,
            "skills_required": opportunity.skills_required or [],
            "experience_level": opportunity.experience_level,
            "deadline": opportunity.deadline.isoformat() if opportunity.deadline else None,
            "status": opportunity.status,
            "created_at": opportunity.created_at.isoformat(),
            "updated_at": opportunity.updated_at.isoformat(),
            "is_active": opportunity.is_active,
            "application_count": 0,  # You can add this field to Opportunity model
            "view_count": 0
        }

        # Add geolocation if latitude and longitude are available
        if hasattr(opportunity, 'latitude') and hasattr(opportunity, 'longitude'):
            if opportunity.latitude and opportunity.longitude:
                doc["location_geo"] = {
                    "lat": float(opportunity.latitude),
                    "lon": float(opportunity.longitude)
                }

        await self.client.index(index=index_name, id=str(opportunity.id), document=doc)
        logger.debug(f"Indexed opportunity: {opportunity.id}")

    async def index_user(self, user: User):
        """Index a single user"""
        index_name = self.indices["users"]

        # Extract data from user_metadata
        metadata = user.user_metadata or {}

        doc = {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name or "",
            "username": user.username,
            "bio": metadata.get("bio", ""),
            "location": metadata.get("location", ""),
            "skills": metadata.get("skills", []),
            "interests": metadata.get("interests", []),
            "experience_level": metadata.get("experience_level", ""),
            "user_type": user.user_type,
            "is_verified": user.is_verified,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat(),
            "profile_completion": metadata.get("profile_completion", 0)
        }

        await self.client.index(index=index_name, id=str(user.id), document=doc)
        logger.debug(f"Indexed user: {user.id}")

    async def index_company(self, company: Company):
        """Index a single company"""
        index_name = self.indices["companies"]

        doc = {
            "id": str(company.id),
            "name": company.name,
            "description": company.description or "",
            "industry": company.industry or "",
            "size": company.size or "",
            "location": company.location or "",
            "website": company.website or "",
            "is_verified": company.is_verified,
            "created_at": company.created_at.isoformat(),
            "active_opportunities_count": 0  # Can be calculated
        }

        await self.client.index(index=index_name, id=str(company.id), document=doc)
        logger.debug(f"Indexed company: {company.id}")

    async def index_course(self, course: Course):
        """Index a single course"""
        index_name = self.indices["courses"]

        doc = {
            "id": str(course.id),
            "title": course.title,
            "description": course.description or "",
            "category": course.category or "",
            "level": course.level or "",
            "skills_taught": course.skills_taught or [],
            "instructor_name": course.instructor_name or "",
            "duration_weeks": course.duration_weeks or 0,
            "price": float(course.price) if course.price else 0.0,
            "rating": float(course.rating) if hasattr(course, 'rating') else 0.0,
            "enrollment_count": course.enrollment_count if hasattr(course, 'enrollment_count') else 0,
            "is_active": course.is_active,
            "created_at": course.created_at.isoformat()
        }

        await self.client.index(index=index_name, id=str(course.id), document=doc)
        logger.debug(f"Indexed course: {course.id}")

    async def bulk_index_opportunities(self, db: AsyncSession):
        """Bulk index all opportunities"""
        index_name = self.indices["opportunities"]

        result = await db.execute(select(Opportunity))
        opportunities = result.scalars().all()

        actions = []
        for opp in opportunities:
            doc = {
                "_index": index_name,
                "_id": str(opp.id),
                "_source": {
                    "id": str(opp.id),
                    "title": opp.title,
                    "description": opp.description,
                    "company_name": opp.company.name if opp.company else "",
                    "company_id": str(opp.company_id) if opp.company_id else None,
                    "category": opp.category,
                    "type": opp.opportunity_type,
                    "location": opp.location,
                    "remote": opp.remote,
                    "salary_min": opp.salary_min,
                    "salary_max": opp.salary_max,
                    "currency": opp.currency,
                    "skills_required": opp.skills_required or [],
                    "experience_level": opp.experience_level,
                    "deadline": opp.deadline.isoformat() if opp.deadline else None,
                    "status": opp.status,
                    "created_at": opp.created_at.isoformat(),
                    "updated_at": opp.updated_at.isoformat(),
                    "is_active": opp.is_active
                }
            }
            actions.append(doc)

        if actions:
            await helpers.async_bulk(self.client, actions)
            logger.info(f"Bulk indexed {len(actions)} opportunities")

        return len(actions)

    async def delete_document(self, index_type: str, doc_id: str):
        """Delete a document from index"""
        index_name = self.indices.get(index_type)
        if not index_name:
            raise ValueError(f"Invalid index type: {index_type}")

        await self.client.delete(index=index_name, id=doc_id)
        logger.debug(f"Deleted document {doc_id} from {index_name}")

    # ==================== Search Operations ====================

    async def search_opportunities(
        self,
        query: str = "",
        filters: Optional[Dict[str, Any]] = None,
        location: Optional[str] = None,
        remote: Optional[bool] = None,
        salary_min: Optional[int] = None,
        skills: Optional[List[str]] = None,
        experience_level: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "_score"
    ) -> Dict[str, Any]:
        """
        Search opportunities with filters

        Args:
            query: Search query
            filters: Additional filters
            location: Location filter
            remote: Remote work filter
            salary_min: Minimum salary filter
            skills: Required skills filter
            experience_level: Experience level filter
            page: Page number
            page_size: Results per page
            sort_by: Sort field (_score, created_at, salary_max)

        Returns:
            Dict with results, total count, aggregations
        """
        index_name = self.indices["opportunities"]

        # Build query
        must_clauses = []
        filter_clauses = []

        # Text search
        if query:
            must_clauses.append({
                "multi_match": {
                    "query": query,
                    "fields": ["title^3", "description^2", "company_name", "skills_required"],
                    "fuzziness": "AUTO",
                    "type": "best_fields"
                }
            })
        else:
            must_clauses.append({"match_all": {}})

        # Filters
        filter_clauses.append({"term": {"is_active": True}})

        if location:
            filter_clauses.append({
                "match": {
                    "location": {
                        "query": location,
                        "fuzziness": "AUTO"
                    }
                }
            })

        if remote is not None:
            filter_clauses.append({"term": {"remote": remote}})

        if salary_min is not None:
            filter_clauses.append({"range": {"salary_max": {"gte": salary_min}}})

        if skills:
            for skill in skills:
                filter_clauses.append({"term": {"skills_required": skill.lower()}})

        if experience_level:
            filter_clauses.append({"term": {"experience_level": experience_level.lower()}})

        # Additional custom filters
        if filters:
            for key, value in filters.items():
                if isinstance(value, list):
                    filter_clauses.append({"terms": {key: value}})
                else:
                    filter_clauses.append({"term": {key: value}})

        # Build full query
        search_query = {
            "bool": {
                "must": must_clauses,
                "filter": filter_clauses
            }
        }

        # Sorting
        sort_options = {
            "_score": [{"_score": {"order": "desc"}}],
            "created_at": [{"created_at": {"order": "desc"}}],
            "salary_max": [{"salary_max": {"order": "desc"}}]
        }
        sort = sort_options.get(sort_by, [{"_score": {"order": "desc"}}])

        # Aggregations for faceted search
        aggs = {
            "categories": {"terms": {"field": "category", "size": 20}},
            "locations": {"terms": {"field": "location.keyword", "size": 20}},
            "experience_levels": {"terms": {"field": "experience_level", "size": 10}},
            "remote_options": {"terms": {"field": "remote"}},
            "salary_ranges": {
                "range": {
                    "field": "salary_max",
                    "ranges": [
                        {"key": "0-50k", "to": 50000},
                        {"key": "50k-100k", "from": 50000, "to": 100000},
                        {"key": "100k-150k", "from": 100000, "to": 150000},
                        {"key": "150k+", "from": 150000}
                    ]
                }
            }
        }

        # Execute search
        from_offset = (page - 1) * page_size
        response = await self.client.search(
            index=index_name,
            query=search_query,
            sort=sort,
            from_=from_offset,
            size=page_size,
            aggs=aggs,
            track_total_hits=True
        )

        # Format results
        hits = response["hits"]["hits"]
        total = response["hits"]["total"]["value"]

        results = []
        for hit in hits:
            source = hit["_source"]
            source["score"] = hit["_score"]
            results.append(source)

        # Format aggregations
        aggregations = {}
        if "aggregations" in response:
            for agg_name, agg_data in response["aggregations"].items():
                if "buckets" in agg_data:
                    aggregations[agg_name] = [
                        {"key": bucket["key"], "count": bucket["doc_count"]}
                        for bucket in agg_data["buckets"]
                    ]

        return {
            "results": results,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "aggregations": aggregations
        }

    async def search_users(
        self,
        query: str = "",
        skills: Optional[List[str]] = None,
        location: Optional[str] = None,
        experience_level: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """Search users with filters"""
        index_name = self.indices["users"]

        must_clauses = []
        filter_clauses = [{"term": {"is_active": True}}]

        if query:
            must_clauses.append({
                "multi_match": {
                    "query": query,
                    "fields": ["full_name^3", "username^2", "bio", "skills"],
                    "fuzziness": "AUTO"
                }
            })
        else:
            must_clauses.append({"match_all": {}})

        if skills:
            for skill in skills:
                filter_clauses.append({"term": {"skills": skill.lower()}})

        if location:
            filter_clauses.append({"match": {"location": location}})

        if experience_level:
            filter_clauses.append({"term": {"experience_level": experience_level.lower()}})

        search_query = {"bool": {"must": must_clauses, "filter": filter_clauses}}

        from_offset = (page - 1) * page_size
        response = await self.client.search(
            index=index_name,
            query=search_query,
            from_=from_offset,
            size=page_size,
            track_total_hits=True
        )

        hits = response["hits"]["hits"]
        total = response["hits"]["total"]["value"]

        results = [hit["_source"] for hit in hits]

        return {
            "results": results,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }

    async def search_companies(
        self,
        query: str = "",
        industry: Optional[str] = None,
        location: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """Search companies with filters"""
        index_name = self.indices["companies"]

        must_clauses = []
        filter_clauses = []

        if query:
            must_clauses.append({
                "multi_match": {
                    "query": query,
                    "fields": ["name^3", "description"],
                    "fuzziness": "AUTO"
                }
            })
        else:
            must_clauses.append({"match_all": {}})

        if industry:
            filter_clauses.append({"term": {"industry": industry.lower()}})

        if location:
            filter_clauses.append({"match": {"location": location}})

        search_query = {"bool": {"must": must_clauses, "filter": filter_clauses}}

        from_offset = (page - 1) * page_size
        response = await self.client.search(
            index=index_name,
            query=search_query,
            from_=from_offset,
            size=page_size,
            track_total_hits=True
        )

        hits = response["hits"]["hits"]
        total = response["hits"]["total"]["value"]

        results = [hit["_source"] for hit in hits]

        return {
            "results": results,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }

    async def autocomplete(
        self,
        query: str,
        field: str = "title",
        index_type: str = "opportunities",
        limit: int = 10
    ) -> List[str]:
        """
        Autocomplete suggestions

        Args:
            query: Partial query string
            field: Field to autocomplete (title, name, etc.)
            index_type: Index to search (opportunities, users, companies, courses)
            limit: Max suggestions

        Returns:
            List of suggestions
        """
        index_name = self.indices.get(index_type)
        if not index_name:
            raise ValueError(f"Invalid index type: {index_type}")

        suggest_field = f"{field}.suggest"

        response = await self.client.search(
            index=index_name,
            suggest={
                "autocomplete": {
                    "prefix": query,
                    "completion": {
                        "field": suggest_field,
                        "size": limit,
                        "skip_duplicates": True
                    }
                }
            }
        )

        suggestions = []
        if "suggest" in response and "autocomplete" in response["suggest"]:
            for option in response["suggest"]["autocomplete"][0]["options"]:
                suggestions.append(option["text"])

        return suggestions

    async def get_search_analytics(self) -> Dict[str, Any]:
        """Get search analytics and statistics"""
        stats = {}

        for index_type, index_name in self.indices.items():
            if await self.client.indices.exists(index=index_name):
                count_response = await self.client.count(index=index_name)
                stats[index_type] = {
                    "total_documents": count_response["count"],
                    "index_name": index_name
                }

        return stats


# Global service instance
elasticsearch_service = ElasticsearchService()
