"""
Search API Endpoints
Provides Elasticsearch-powered full-text search for Trybe platform
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.services.elasticsearch_service import elasticsearch_service

router = APIRouter()


# ==================== Schemas ====================

class SearchOpportunitiesRequest(BaseModel):
    """Request schema for opportunity search"""
    query: str = Field("", description="Search query")
    location: Optional[str] = Field(None, description="Location filter")
    remote: Optional[bool] = Field(None, description="Remote work filter")
    salary_min: Optional[int] = Field(None, description="Minimum salary")
    skills: Optional[List[str]] = Field(None, description="Required skills")
    experience_level: Optional[str] = Field(None, description="Experience level (entry, mid, senior)")
    category: Optional[str] = Field(None, description="Opportunity category")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Results per page")
    sort_by: str = Field("_score", description="Sort by: _score, created_at, salary_max")


class SearchUsersRequest(BaseModel):
    """Request schema for user search"""
    query: str = Field("", description="Search query")
    skills: Optional[List[str]] = Field(None, description="Skills filter")
    location: Optional[str] = Field(None, description="Location filter")
    experience_level: Optional[str] = Field(None, description="Experience level")
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class SearchCompaniesRequest(BaseModel):
    """Request schema for company search"""
    query: str = Field("", description="Search query")
    industry: Optional[str] = Field(None, description="Industry filter")
    location: Optional[str] = Field(None, description="Location filter")
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class AutocompleteRequest(BaseModel):
    """Request schema for autocomplete"""
    query: str = Field(..., min_length=1, description="Partial query")
    field: str = Field("title", description="Field to autocomplete")
    index_type: str = Field("opportunities", description="Index type: opportunities, users, companies, courses")
    limit: int = Field(10, ge=1, le=50, description="Max suggestions")


class SearchResponse(BaseModel):
    """Generic search response"""
    results: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int
    total_pages: int
    aggregations: Optional[Dict[str, Any]] = None


class AutocompleteResponse(BaseModel):
    """Autocomplete response"""
    suggestions: List[str]
    query: str


class IndexStatsResponse(BaseModel):
    """Index statistics response"""
    opportunities: Dict[str, Any]
    users: Dict[str, Any]
    companies: Dict[str, Any]
    courses: Dict[str, Any]


# ==================== Search Endpoints ====================

@router.post("/opportunities", response_model=SearchResponse)
async def search_opportunities(
    request: SearchOpportunitiesRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Search opportunities with full-text search and filters

    Features:
    - Full-text search across title, description, company, skills
    - Fuzzy matching for typo tolerance
    - Location-based filtering
    - Salary range filtering
    - Skills-based filtering
    - Experience level filtering
    - Faceted search (aggregations)
    - Sorting options

    Returns:
    - Paginated search results
    - Total count
    - Aggregations (facets) for filtering UI
    """
    try:
        # Build filters dict for additional filters
        filters = {}
        if request.category:
            filters["category"] = request.category

        result = await elasticsearch_service.search_opportunities(
            query=request.query,
            filters=filters,
            location=request.location,
            remote=request.remote,
            salary_min=request.salary_min,
            skills=request.skills,
            experience_level=request.experience_level,
            page=request.page,
            page_size=request.page_size,
            sort_by=request.sort_by
        )

        return SearchResponse(**result)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/opportunities/quick", response_model=SearchResponse)
async def quick_search_opportunities(
    q: str = Query("", description="Search query"),
    location: Optional[str] = Query(None, description="Location filter"),
    remote: Optional[bool] = Query(None, description="Remote work"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
):
    """
    Quick opportunity search using GET (for simple searches)

    Simpler version of POST /search/opportunities for basic queries
    """
    try:
        result = await elasticsearch_service.search_opportunities(
            query=q,
            location=location,
            remote=remote,
            page=page,
            page_size=page_size
        )

        return SearchResponse(**result)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.post("/users", response_model=SearchResponse)
async def search_users(
    request: SearchUsersRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Search users with filters

    Features:
    - Full-text search across name, username, bio, skills
    - Skills-based filtering
    - Location filtering
    - Experience level filtering

    Use cases:
    - Find talent for opportunities
    - Discover collaborators
    - Network with professionals
    """
    try:
        result = await elasticsearch_service.search_users(
            query=request.query,
            skills=request.skills,
            location=request.location,
            experience_level=request.experience_level,
            page=request.page,
            page_size=request.page_size
        )

        return SearchResponse(**result)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/users/quick", response_model=SearchResponse)
async def quick_search_users(
    q: str = Query("", description="Search query"),
    skills: Optional[str] = Query(None, description="Comma-separated skills"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
):
    """Quick user search using GET"""
    try:
        skills_list = [s.strip() for s in skills.split(",")] if skills else None

        result = await elasticsearch_service.search_users(
            query=q,
            skills=skills_list,
            page=page,
            page_size=page_size
        )

        return SearchResponse(**result)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.post("/companies", response_model=SearchResponse)
async def search_companies(
    request: SearchCompaniesRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Search companies with filters

    Features:
    - Full-text search across company name and description
    - Industry filtering
    - Location filtering

    Use cases:
    - Find potential employers
    - Research companies
    - Discover industry leaders
    """
    try:
        result = await elasticsearch_service.search_companies(
            query=request.query,
            industry=request.industry,
            location=request.location,
            page=request.page,
            page_size=request.page_size
        )

        return SearchResponse(**result)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/companies/quick", response_model=SearchResponse)
async def quick_search_companies(
    q: str = Query("", description="Search query"),
    industry: Optional[str] = Query(None, description="Industry filter"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
):
    """Quick company search using GET"""
    try:
        result = await elasticsearch_service.search_companies(
            query=q,
            industry=industry,
            page=page,
            page_size=page_size
        )

        return SearchResponse(**result)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.post("/autocomplete", response_model=AutocompleteResponse)
async def autocomplete(
    request: AutocompleteRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Autocomplete suggestions for search queries

    Provides type-ahead suggestions as users type in search boxes

    Supported fields:
    - opportunities: title
    - users: full_name
    - companies: name
    - courses: title

    Example usage:
    ```
    POST /api/v1/search/autocomplete
    {
        "query": "soft",
        "field": "title",
        "index_type": "opportunities",
        "limit": 10
    }
    ```

    Returns suggestions like:
    ["Software Engineer", "Software Developer", "Software Architect"]
    """
    try:
        suggestions = await elasticsearch_service.autocomplete(
            query=request.query,
            field=request.field,
            index_type=request.index_type,
            limit=request.limit
        )

        return AutocompleteResponse(
            suggestions=suggestions,
            query=request.query
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Autocomplete failed: {str(e)}"
        )


@router.get("/autocomplete/quick")
async def quick_autocomplete(
    q: str = Query(..., min_length=1, description="Partial query"),
    field: str = Query("title", description="Field to autocomplete"),
    index_type: str = Query("opportunities", description="Index type"),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_active_user)
):
    """Quick autocomplete using GET (for simple autocomplete)"""
    try:
        suggestions = await elasticsearch_service.autocomplete(
            query=q,
            field=field,
            index_type=index_type,
            limit=limit
        )

        return {"suggestions": suggestions, "query": q}

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Autocomplete failed: {str(e)}"
        )


# ==================== Index Management Endpoints (Admin) ====================

@router.post("/admin/indices/create", status_code=status.HTTP_201_CREATED)
async def create_indices(
    current_user: User = Depends(get_current_active_user)
):
    """
    Create all Elasticsearch indices (Admin only)

    Creates indices for:
    - Opportunities
    - Users
    - Companies
    - Courses

    Note: Requires admin privileges
    """
    # TODO: Add admin check
    if current_user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create indices"
        )

    try:
        await elasticsearch_service.create_indices()
        return {
            "message": "All indices created successfully",
            "indices": list(elasticsearch_service.indices.keys())
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create indices: {str(e)}"
        )


@router.delete("/admin/indices/{index_type}", status_code=status.HTTP_200_OK)
async def delete_index(
    index_type: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete an Elasticsearch index (Admin only)

    Available index types:
    - opportunities
    - users
    - companies
    - courses

    Warning: This will delete all data in the index!
    """
    if current_user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete indices"
        )

    try:
        await elasticsearch_service.delete_index(index_type)
        return {"message": f"Index '{index_type}' deleted successfully"}

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete index: {str(e)}"
        )


@router.post("/admin/reindex/{index_type}", status_code=status.HTTP_200_OK)
async def reindex_data(
    index_type: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Reindex data from database to Elasticsearch (Admin only)

    Rebuilds the search index from the database

    Available index types:
    - opportunities
    - users
    - companies
    - courses
    - all (reindex everything)

    This operation may take some time for large datasets
    """
    if current_user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can reindex data"
        )

    try:
        if index_type == "opportunities" or index_type == "all":
            count = await elasticsearch_service.bulk_index_opportunities(db)
            return {
                "message": f"Reindexed {count} opportunities successfully",
                "index_type": index_type,
                "count": count
            }

        # TODO: Add bulk indexing for other entity types
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bulk reindexing not yet implemented for '{index_type}'"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reindexing failed: {str(e)}"
        )


@router.get("/admin/stats", response_model=IndexStatsResponse)
async def get_search_stats(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get search index statistics (Admin only)

    Returns:
    - Total documents in each index
    - Index names
    - Index health status
    """
    if current_user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view search statistics"
        )

    try:
        stats = await elasticsearch_service.get_search_analytics()
        return IndexStatsResponse(**stats)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )


# ==================== Helper Endpoints ====================

@router.get("/health")
async def search_health_check():
    """
    Check Elasticsearch connection health

    Returns:
    - connected: Whether Elasticsearch is reachable
    - cluster_info: Basic cluster information
    """
    try:
        info = await elasticsearch_service.client.info()
        return {
            "connected": True,
            "cluster_name": info.get("cluster_name"),
            "version": info.get("version", {}).get("number")
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e)
        }


@router.get("/supported-filters")
async def get_supported_filters():
    """
    Get list of supported filters for each search type

    Useful for building dynamic search UIs
    """
    return {
        "opportunities": {
            "filters": [
                "location",
                "remote",
                "salary_min",
                "skills",
                "experience_level",
                "category"
            ],
            "sort_options": ["_score", "created_at", "salary_max"],
            "aggregations": [
                "categories",
                "locations",
                "experience_levels",
                "remote_options",
                "salary_ranges"
            ]
        },
        "users": {
            "filters": ["skills", "location", "experience_level"],
            "sort_options": ["_score", "created_at"]
        },
        "companies": {
            "filters": ["industry", "location"],
            "sort_options": ["_score", "created_at"]
        },
        "courses": {
            "filters": ["category", "level", "skills_taught"],
            "sort_options": ["_score", "rating", "enrollment_count"]
        }
    }
