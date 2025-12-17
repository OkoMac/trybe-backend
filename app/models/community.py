"""Community Models"""

from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Boolean, Enum as SQLEnum, Table
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from enum import Enum

from app.core.database import Base


# Enums
class PostType(str, Enum):
    """Post type"""
    TEXT = "text"
    QUESTION = "question"
    ANNOUNCEMENT = "announcement"
    POLL = "poll"
    RESOURCE = "resource"
    EVENT = "event"


class ReactionType(str, Enum):
    """Reaction type"""
    LIKE = "like"
    LOVE = "love"
    CELEBRATE = "celebrate"
    SUPPORT = "support"
    INSIGHTFUL = "insightful"
    CURIOUS = "curious"


# Association tables
group_members = Table(
    'group_members',
    Base.metadata,
    Column('group_id', PG_UUID(as_uuid=True), ForeignKey('community_groups.id', ondelete='CASCADE')),
    Column('user_id', PG_UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE')),
    Column('joined_at', DateTime, default=datetime.utcnow),
    Column('role', String(50), default='member')  # admin, moderator, member
)

user_followers = Table(
    'user_followers',
    Base.metadata,
    Column('follower_id', PG_UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE')),
    Column('following_id', PG_UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE')),
    Column('followed_at', DateTime, default=datetime.utcnow)
)


# Models
class CommunityPost(Base):
    """Community post model"""
    __tablename__ = "community_posts"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    author_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    group_id = Column(PG_UUID(as_uuid=True), ForeignKey('community_groups.id', ondelete='CASCADE'))

    # Content
    title = Column(String(500))
    content = Column(Text, nullable=False)
    post_type = Column(SQLEnum(PostType), default=PostType.TEXT, index=True)

    # Media
    media_urls = Column(JSONB, default=[])  # [{"type": "image", "url": "..."}]
    attachments = Column(JSONB, default=[])  # [{"name": "...", "url": "...", "type": "..."}]

    # Metadata
    tags = Column(ARRAY(String), default=[])
    is_pinned = Column(Boolean, default=False)
    is_edited = Column(Boolean, default=False)
    edited_at = Column(DateTime)

    # Engagement
    view_count = Column(Integer, default=0)
    reaction_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)

    # Moderation
    is_flagged = Column(Boolean, default=False)
    is_hidden = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    author = relationship("User", back_populates="posts", foreign_keys=[author_id])
    group = relationship("CommunityGroup", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    reactions = relationship("Reaction", back_populates="post", cascade="all, delete-orphan")


class Comment(Base):
    """Comment model"""
    __tablename__ = "comments"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    post_id = Column(PG_UUID(as_uuid=True), ForeignKey('community_posts.id', ondelete='CASCADE'), nullable=False)
    author_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    parent_id = Column(PG_UUID(as_uuid=True), ForeignKey('comments.id', ondelete='CASCADE'))  # For nested comments

    # Content
    content = Column(Text, nullable=False)

    # Media
    media_urls = Column(JSONB, default=[])

    # Engagement
    reaction_count = Column(Integer, default=0)
    reply_count = Column(Integer, default=0)

    # Metadata
    is_edited = Column(Boolean, default=False)
    edited_at = Column(DateTime)
    is_flagged = Column(Boolean, default=False)
    is_hidden = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    post = relationship("CommunityPost", back_populates="comments")
    author = relationship("User", back_populates="comments", foreign_keys=[author_id])
    parent = relationship("Comment", remote_side=[id], backref="replies")
    reactions = relationship("Reaction", back_populates="comment", cascade="all, delete-orphan")


class Reaction(Base):
    """Reaction model (for posts and comments)"""
    __tablename__ = "reactions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    post_id = Column(PG_UUID(as_uuid=True), ForeignKey('community_posts.id', ondelete='CASCADE'))
    comment_id = Column(PG_UUID(as_uuid=True), ForeignKey('comments.id', ondelete='CASCADE'))

    reaction_type = Column(SQLEnum(ReactionType), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")
    post = relationship("CommunityPost", back_populates="reactions")
    comment = relationship("Comment", back_populates="reactions")


class CommunityGroup(Base):
    """Community group/circle model"""
    __tablename__ = "community_groups"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    tagline = Column(String(500))

    # Creator
    created_by_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)

    # Media
    cover_image_url = Column(String(500))
    logo_url = Column(String(500))

    # Configuration
    is_public = Column(Boolean, default=True)
    is_official = Column(Boolean, default=False)  # Official Trybe groups
    allow_posts = Column(Boolean, default=True)
    require_approval = Column(Boolean, default=False)

    # Metadata
    category = Column(String(100))
    tags = Column(ARRAY(String), default=[])
    rules = Column(JSONB, default=[])

    # Stats
    member_count = Column(Integer, default=0)
    post_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    members = relationship("User", secondary=group_members, backref="community_groups")
    posts = relationship("CommunityPost", back_populates="group", cascade="all, delete-orphan")


class Poll(Base):
    """Poll model for community engagement"""
    __tablename__ = "polls"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    post_id = Column(PG_UUID(as_uuid=True), ForeignKey('community_posts.id', ondelete='CASCADE'), nullable=False, unique=True)

    # Poll details
    question = Column(String(500), nullable=False)
    options = Column(JSONB, nullable=False)  # [{"id": 1, "text": "Option A", "votes": 0}]

    # Configuration
    allow_multiple_choices = Column(Boolean, default=False)
    expires_at = Column(DateTime)
    is_anonymous = Column(Boolean, default=False)

    # Stats
    total_votes = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    votes = relationship("PollVote", back_populates="poll", cascade="all, delete-orphan")


class PollVote(Base):
    """Poll vote model"""
    __tablename__ = "poll_votes"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    poll_id = Column(PG_UUID(as_uuid=True), ForeignKey('polls.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    # Vote
    selected_options = Column(ARRAY(Integer), nullable=False)  # Array of option IDs

    voted_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    poll = relationship("Poll", back_populates="votes")
    user = relationship("User")


class Feed(Base):
    """User feed/timeline model (aggregated content)"""
    __tablename__ = "user_feeds"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    # Content reference
    content_type = Column(String(50), nullable=False)  # post, comment, reaction, etc.
    content_id = Column(PG_UUID(as_uuid=True), nullable=False)

    # Metadata
    actor_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))  # Who performed the action
    action = Column(String(100))  # posted, commented, reacted, shared, etc.

    # Ordering
    score = Column(Integer, default=0)  # For ranking/sorting
    is_read = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    actor = relationship("User", foreign_keys=[actor_id])
