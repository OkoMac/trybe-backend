"""Community Schemas"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from app.models.community import PostType, ReactionType


# Post Schemas
class PostBase(BaseModel):
    """Base post schema"""
    title: Optional[str] = Field(None, max_length=500)
    content: str = Field(..., min_length=1)
    post_type: PostType = PostType.TEXT
    tags: List[str] = []
    group_id: Optional[UUID] = None


class PostCreate(PostBase):
    """Create post schema"""
    media_urls: List[dict] = []


class PostUpdate(BaseModel):
    """Update post schema"""
    title: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = Field(None, min_length=1)
    tags: Optional[List[str]] = None
    is_pinned: Optional[bool] = None


class AuthorInfo(BaseModel):
    """Author information"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    username: str
    avatar_url: Optional[str] = None


class PostResponse(PostBase):
    """Post response schema"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    author_id: UUID
    author: Optional[AuthorInfo] = None
    is_pinned: bool
    is_edited: bool
    edited_at: Optional[datetime] = None
    view_count: int
    reaction_count: int
    comment_count: int
    share_count: int
    created_at: datetime
    updated_at: datetime


# Comment Schemas
class CommentBase(BaseModel):
    """Base comment schema"""
    content: str = Field(..., min_length=1)


class CommentCreate(CommentBase):
    """Create comment schema"""
    post_id: UUID
    parent_id: Optional[UUID] = None
    media_urls: List[dict] = []


class CommentUpdate(BaseModel):
    """Update comment schema"""
    content: Optional[str] = Field(None, min_length=1)


class CommentResponse(CommentBase):
    """Comment response schema"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    post_id: UUID
    author_id: UUID
    parent_id: Optional[UUID] = None
    author: Optional[AuthorInfo] = None
    media_urls: List[dict] = []
    reaction_count: int
    reply_count: int
    is_edited: bool
    edited_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# Reaction Schemas
class ReactionCreate(BaseModel):
    """Create reaction schema"""
    post_id: Optional[UUID] = None
    comment_id: Optional[UUID] = None
    reaction_type: ReactionType


class ReactionResponse(BaseModel):
    """Reaction response schema"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    post_id: Optional[UUID] = None
    comment_id: Optional[UUID] = None
    reaction_type: ReactionType
    created_at: datetime


class ReactionSummary(BaseModel):
    """Reaction summary for a post/comment"""
    reaction_type: ReactionType
    count: int
    users: List[AuthorInfo] = []  # Top reactors


# Group Schemas
class GroupBase(BaseModel):
    """Base group schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    tagline: Optional[str] = Field(None, max_length=500)
    is_public: bool = True
    allow_posts: bool = True
    require_approval: bool = False
    category: Optional[str] = None
    tags: List[str] = []


class GroupCreate(GroupBase):
    """Create group schema"""
    cover_image_url: Optional[str] = None
    logo_url: Optional[str] = None
    rules: List[dict] = []


class GroupUpdate(BaseModel):
    """Update group schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    tagline: Optional[str] = Field(None, max_length=500)
    is_public: Optional[bool] = None
    allow_posts: Optional[bool] = None
    require_approval: Optional[bool] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    cover_image_url: Optional[str] = None
    logo_url: Optional[str] = None
    rules: Optional[List[dict]] = None


class GroupResponse(GroupBase):
    """Group response schema"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_by_id: UUID
    cover_image_url: Optional[str] = None
    logo_url: Optional[str] = None
    is_official: bool
    rules: List[dict] = []
    member_count: int
    post_count: int
    created_at: datetime
    updated_at: datetime


class GroupDetailResponse(GroupResponse):
    """Detailed group response with members"""
    members: List[AuthorInfo] = []
    is_member: bool = False
    user_role: Optional[str] = None  # admin, moderator, member


# Poll Schemas
class PollOption(BaseModel):
    """Poll option"""
    id: int
    text: str
    votes: int = 0


class PollCreate(BaseModel):
    """Create poll schema"""
    question: str = Field(..., max_length=500)
    options: List[str]  # Will be converted to PollOption objects
    allow_multiple_choices: bool = False
    expires_at: Optional[datetime] = None
    is_anonymous: bool = False


class PollResponse(BaseModel):
    """Poll response schema"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    post_id: UUID
    question: str
    options: List[dict]
    allow_multiple_choices: bool
    expires_at: Optional[datetime] = None
    is_anonymous: bool
    total_votes: int
    created_at: datetime


class PollVoteCreate(BaseModel):
    """Poll vote schema"""
    poll_id: UUID
    selected_options: List[int]  # Option IDs


class PollVoteResponse(BaseModel):
    """Poll vote response"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    poll_id: UUID
    user_id: UUID
    selected_options: List[int]
    voted_at: datetime


# Feed Schemas
class FeedItemResponse(BaseModel):
    """Feed item response"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    content_type: str
    content_id: UUID
    actor_id: Optional[UUID] = None
    action: Optional[str] = None
    score: int
    is_read: bool
    created_at: datetime
    # Populated fields
    content: Optional[dict] = None  # The actual post/comment/etc
    actor: Optional[AuthorInfo] = None


# Statistics
class CommunityStats(BaseModel):
    """Community statistics"""
    total_posts: int
    total_comments: int
    total_reactions: int
    total_groups: int
    total_members: int
    trending_topics: List[str]
    top_contributors: List[dict]


# Moderation
class ContentReport(BaseModel):
    """Content report schema"""
    content_type: str  # post, comment
    content_id: UUID
    reason: str
    description: Optional[str] = None


class ModerationAction(BaseModel):
    """Moderation action schema"""
    content_type: str
    content_id: UUID
    action: str  # hide, flag, delete
    reason: Optional[str] = None
