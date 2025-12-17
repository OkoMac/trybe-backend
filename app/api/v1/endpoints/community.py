"""Community API Endpoints"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, update as sql_update
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.community import (
    CommunityPost,
    Comment,
    Reaction,
    CommunityGroup,
    Poll,
    PollVote,
    Feed,
    ReactionType,
    PostType,
    group_members
)
from app.schemas.community import (
    PostCreate,
    PostUpdate,
    PostResponse,
    CommentCreate,
    CommentUpdate,
    CommentResponse,
    ReactionCreate,
    ReactionResponse,
    ReactionSummary,
    GroupCreate,
    GroupUpdate,
    GroupResponse,
    GroupDetailResponse,
    PollCreate,
    PollResponse,
    PollVoteCreate,
    PollVoteResponse,
    FeedItemResponse,
    CommunityStats,
    ContentReport,
    ModerationAction
)

router = APIRouter()


# ==================== POST ENDPOINTS ====================

@router.post("/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    post_data: PostCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a community post"""

    # If posting to a group, verify membership
    if post_data.group_id:
        query = select(CommunityGroup).where(CommunityGroup.id == post_data.group_id)
        result = await db.execute(query)
        group = result.scalar_one_or_none()

        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Group not found"
            )

        if not group.allow_posts:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Posting is not allowed in this group"
            )

    # Create post
    post = CommunityPost(
        **post_data.model_dump(),
        author_id=current_user.id
    )

    db.add(post)

    # Update group post count
    if post_data.group_id:
        await db.execute(
            sql_update(CommunityGroup)
            .where(CommunityGroup.id == post_data.group_id)
            .values(post_count=CommunityGroup.post_count + 1)
        )

    await db.commit()
    await db.refresh(post)

    return post


@router.get("/posts", response_model=List[PostResponse])
async def list_posts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    group_id: Optional[UUID] = None,
    post_type: Optional[PostType] = None,
    tags: Optional[str] = Query(None),  # Comma-separated tags
    db: AsyncSession = Depends(get_db)
):
    """List community posts"""

    query = select(CommunityPost).options(
        selectinload(CommunityPost.author)
    )

    # Apply filters
    filters = [CommunityPost.is_hidden == False]

    if group_id:
        filters.append(CommunityPost.group_id == group_id)

    if post_type:
        filters.append(CommunityPost.post_type == post_type)

    if tags:
        tag_list = [tag.strip() for tag in tags.split(",")]
        filters.append(CommunityPost.tags.overlap(tag_list))

    query = query.where(and_(*filters))
    query = query.order_by(desc(CommunityPost.is_pinned), desc(CommunityPost.created_at))
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    posts = result.scalars().all()

    return posts


@router.get("/posts/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get post by ID"""

    query = select(CommunityPost).where(
        CommunityPost.id == post_id
    ).options(selectinload(CommunityPost.author))

    result = await db.execute(query)
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    # Increment view count
    post.view_count += 1
    await db.commit()

    return post


@router.patch("/posts/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: UUID,
    post_data: PostUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update post (author only)"""

    query = select(CommunityPost).where(CommunityPost.id == post_id)
    result = await db.execute(query)
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    # Check permission
    if post.author_id != current_user.id and current_user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this post"
        )

    # Update fields
    update_data = post_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(post, field, value)

    post.is_edited = True
    post.edited_at = datetime.utcnow()
    post.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(post)

    return post


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete post (author/admin only)"""

    query = select(CommunityPost).where(CommunityPost.id == post_id)
    result = await db.execute(query)
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    # Check permission
    if post.author_id != current_user.id and current_user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this post"
        )

    # Update group post count if applicable
    if post.group_id:
        await db.execute(
            sql_update(CommunityGroup)
            .where(CommunityGroup.id == post.group_id)
            .values(post_count=CommunityGroup.post_count - 1)
        )

    await db.delete(post)
    await db.commit()


# ==================== COMMENT ENDPOINTS ====================

@router.post("/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    comment_data: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a comment"""

    # Verify post exists
    query = select(CommunityPost).where(CommunityPost.id == comment_data.post_id)
    result = await db.execute(query)
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    # Verify parent comment if replying
    if comment_data.parent_id:
        parent_query = select(Comment).where(Comment.id == comment_data.parent_id)
        parent_result = await db.execute(parent_query)
        parent = parent_result.scalar_one_or_none()

        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent comment not found"
            )

    # Create comment
    comment = Comment(
        **comment_data.model_dump(),
        author_id=current_user.id
    )

    db.add(comment)

    # Update post comment count
    post.comment_count += 1

    # Update parent reply count if replying
    if comment_data.parent_id:
        await db.execute(
            sql_update(Comment)
            .where(Comment.id == comment_data.parent_id)
            .values(reply_count=Comment.reply_count + 1)
        )

    await db.commit()
    await db.refresh(comment)

    return comment


@router.get("/posts/{post_id}/comments", response_model=List[CommentResponse])
async def list_post_comments(
    post_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """List comments for a post"""

    query = select(Comment).where(
        and_(
            Comment.post_id == post_id,
            Comment.parent_id.is_(None),  # Top-level comments only
            Comment.is_hidden == False
        )
    ).options(
        selectinload(Comment.author)
    ).order_by(desc(Comment.created_at)).offset(skip).limit(limit)

    result = await db.execute(query)
    comments = result.scalars().all()

    return comments


@router.get("/comments/{comment_id}/replies", response_model=List[CommentResponse])
async def list_comment_replies(
    comment_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """List replies to a comment"""

    query = select(Comment).where(
        and_(
            Comment.parent_id == comment_id,
            Comment.is_hidden == False
        )
    ).options(
        selectinload(Comment.author)
    ).order_by(Comment.created_at)

    result = await db.execute(query)
    replies = result.scalars().all()

    return replies


@router.patch("/comments/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: UUID,
    comment_data: CommentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update comment (author only)"""

    query = select(Comment).where(Comment.id == comment_id)
    result = await db.execute(query)
    comment = result.scalar_one_or_none()

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )

    # Check permission
    if comment.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this comment"
        )

    # Update fields
    update_data = comment_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(comment, field, value)

    comment.is_edited = True
    comment.edited_at = datetime.utcnow()
    comment.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(comment)

    return comment


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete comment (author/admin only)"""

    query = select(Comment).where(Comment.id == comment_id)
    result = await db.execute(query)
    comment = result.scalar_one_or_none()

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )

    # Check permission
    if comment.author_id != current_user.id and current_user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this comment"
        )

    # Update post comment count
    await db.execute(
        sql_update(CommunityPost)
        .where(CommunityPost.id == comment.post_id)
        .values(comment_count=CommunityPost.comment_count - 1)
    )

    # Update parent reply count if applicable
    if comment.parent_id:
        await db.execute(
            sql_update(Comment)
            .where(Comment.id == comment.parent_id)
            .values(reply_count=Comment.reply_count - 1)
        )

    await db.delete(comment)
    await db.commit()


# ==================== REACTION ENDPOINTS ====================

@router.post("/reactions", response_model=ReactionResponse, status_code=status.HTTP_201_CREATED)
async def create_reaction(
    reaction_data: ReactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """React to a post or comment"""

    if not reaction_data.post_id and not reaction_data.comment_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must specify either post_id or comment_id"
        )

    # Check if already reacted
    existing_query = select(Reaction).where(
        and_(
            Reaction.user_id == current_user.id,
            or_(
                Reaction.post_id == reaction_data.post_id,
                Reaction.comment_id == reaction_data.comment_id
            )
        )
    )
    existing = await db.execute(existing_query)
    existing_reaction = existing.scalar_one_or_none()

    if existing_reaction:
        # Update reaction type
        existing_reaction.reaction_type = reaction_data.reaction_type
        await db.commit()
        await db.refresh(existing_reaction)
        return existing_reaction

    # Create new reaction
    reaction = Reaction(
        **reaction_data.model_dump(),
        user_id=current_user.id
    )

    db.add(reaction)

    # Update reaction count
    if reaction_data.post_id:
        await db.execute(
            sql_update(CommunityPost)
            .where(CommunityPost.id == reaction_data.post_id)
            .values(reaction_count=CommunityPost.reaction_count + 1)
        )
    elif reaction_data.comment_id:
        await db.execute(
            sql_update(Comment)
            .where(Comment.id == reaction_data.comment_id)
            .values(reaction_count=Comment.reaction_count + 1)
        )

    await db.commit()
    await db.refresh(reaction)

    return reaction


@router.delete("/reactions/{reaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reaction(
    reaction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a reaction"""

    query = select(Reaction).where(Reaction.id == reaction_id)
    result = await db.execute(query)
    reaction = result.scalar_one_or_none()

    if not reaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reaction not found"
        )

    # Check permission
    if reaction.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this reaction"
        )

    # Update reaction count
    if reaction.post_id:
        await db.execute(
            sql_update(CommunityPost)
            .where(CommunityPost.id == reaction.post_id)
            .values(reaction_count=CommunityPost.reaction_count - 1)
        )
    elif reaction.comment_id:
        await db.execute(
            sql_update(Comment)
            .where(Comment.id == reaction.comment_id)
            .values(reaction_count=Comment.reaction_count - 1)
        )

    await db.delete(reaction)
    await db.commit()


# ==================== GROUP ENDPOINTS ====================

@router.post("/groups", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    group_data: GroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a community group"""

    # Create group
    group = CommunityGroup(
        **group_data.model_dump(),
        created_by_id=current_user.id,
        member_count=1
    )

    db.add(group)
    await db.commit()
    await db.refresh(group)

    # Add creator as first member (admin)
    await db.execute(
        group_members.insert().values(
            group_id=group.id,
            user_id=current_user.id,
            joined_at=datetime.utcnow(),
            role='admin'
        )
    )
    await db.commit()

    return group


@router.get("/groups", response_model=List[GroupResponse])
async def list_groups(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List community groups"""

    query = select(CommunityGroup)

    # Apply filters
    filters = [CommunityGroup.is_public == True]

    if category:
        filters.append(CommunityGroup.category == category)

    if search:
        filters.append(
            or_(
                CommunityGroup.name.ilike(f"%{search}%"),
                CommunityGroup.description.ilike(f"%{search}%")
            )
        )

    query = query.where(and_(*filters))
    query = query.order_by(desc(CommunityGroup.member_count))
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    groups = result.scalars().all()

    return groups


@router.get("/groups/{group_id}", response_model=GroupDetailResponse)
async def get_group(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get group details"""

    query = select(CommunityGroup).where(
        CommunityGroup.id == group_id
    ).options(selectinload(CommunityGroup.members))

    result = await db.execute(query)
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )

    # Check if user is a member
    is_member = current_user in group.members
    user_role = None

    if is_member:
        # Get user's role in group
        role_query = select(group_members.c.role).where(
            and_(
                group_members.c.group_id == group_id,
                group_members.c.user_id == current_user.id
            )
        )
        role_result = await db.execute(role_query)
        user_role = role_result.scalar_one_or_none()

    # Build response
    group_dict = GroupResponse.model_validate(group).model_dump()
    group_dict['members'] = group.members
    group_dict['is_member'] = is_member
    group_dict['user_role'] = user_role

    return group_dict


@router.post("/groups/{group_id}/join", response_model=dict)
async def join_group(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Join a community group"""

    # Get group
    query = select(CommunityGroup).where(
        CommunityGroup.id == group_id
    ).options(selectinload(CommunityGroup.members))

    result = await db.execute(query)
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )

    # Check if already a member
    if current_user in group.members:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already a member of this group"
        )

    # Add user to group
    await db.execute(
        group_members.insert().values(
            group_id=group.id,
            user_id=current_user.id,
            joined_at=datetime.utcnow(),
            role='member'
        )
    )

    # Update member count
    group.member_count += 1

    await db.commit()

    return {"message": "Successfully joined group"}


@router.post("/groups/{group_id}/leave", response_model=dict)
async def leave_group(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Leave a community group"""

    # Get group
    query = select(CommunityGroup).where(CommunityGroup.id == group_id)
    result = await db.execute(query)
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )

    # Group creator cannot leave
    if group.created_by_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group creator cannot leave. Transfer ownership first or delete the group."
        )

    # Remove user from group
    await db.execute(
        group_members.delete().where(
            and_(
                group_members.c.group_id == group.id,
                group_members.c.user_id == current_user.id
            )
        )
    )

    # Update member count
    group.member_count -= 1

    await db.commit()

    return {"message": "Successfully left group"}


# ==================== FEED ENDPOINTS ====================

@router.get("/feed", response_model=List[FeedItemResponse])
async def get_user_feed(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get personalized user feed"""

    query = select(Feed).where(
        Feed.user_id == current_user.id
    ).order_by(desc(Feed.score), desc(Feed.created_at)).offset(skip).limit(limit)

    result = await db.execute(query)
    feed_items = result.scalars().all()

    # TODO: Populate content and actor details
    return feed_items


# ==================== STATISTICS ENDPOINTS ====================

@router.get("/stats", response_model=CommunityStats)
async def get_community_stats(
    db: AsyncSession = Depends(get_db)
):
    """Get community statistics"""

    # Get counts
    posts_count = await db.execute(select(func.count()).select_from(CommunityPost))
    total_posts = posts_count.scalar()

    comments_count = await db.execute(select(func.count()).select_from(Comment))
    total_comments = comments_count.scalar()

    reactions_count = await db.execute(select(func.count()).select_from(Reaction))
    total_reactions = reactions_count.scalar()

    groups_count = await db.execute(select(func.count()).select_from(CommunityGroup))
    total_groups = groups_count.scalar()

    # TODO: Calculate trending topics and top contributors

    return CommunityStats(
        total_posts=total_posts or 0,
        total_comments=total_comments or 0,
        total_reactions=total_reactions or 0,
        total_groups=total_groups or 0,
        total_members=0,  # TODO: Count unique members
        trending_topics=[],
        top_contributors=[]
    )
