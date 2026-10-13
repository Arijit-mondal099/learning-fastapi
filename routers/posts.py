from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models import Post, User
from schemas import PostCreate, PostResponse, PostUpdate

router = APIRouter()


@router.post(
    "/api/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED
)
async def create_post(post: PostCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(User).where(User.id == post.user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found!"
        )

    new_post = Post(**post.model_dump())
    db.add(new_post)
    await db.commit()
    await db.refresh(new_post, attribute_names=["author"])

    return new_post


@router.get("/api/posts", response_model=list[PostResponse])
async def get_posts(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(Post)
        .order_by(Post.date_posted.desc())
        .options(selectinload(Post.author))
    )
    posts = result.scalars().all()
    return posts


@router.get("/api/posts/{post_id}", response_model=PostResponse)
async def get_post(
    db: Annotated[AsyncSession, Depends(get_db)],
    post_id: int = Path(..., gt=0, description="Get individual post by post id"),
):
    result = await db.execute(
        select(Post).where(Post.id == post_id).options(selectinload(Post.author))
    )
    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found!"
        )

    return post


@router.put("/api/posts/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: int, post_update: PostCreate, db: Annotated[AsyncSession, Depends(get_db)]
):
    result = await db.execute(
        select(Post).where(Post.id == post_id).options(selectinload(Post.author))
    )
    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found!"
        )

    post.title = post_update.title
    post.content = post_update.content

    await db.commit()
    await db.refresh(post, attribute_names=["author"])

    return post


@router.patch("/api/posts/{post_id}", response_model=PostResponse)
async def update_post_partial(
    post_id: int, post_update: PostUpdate, db: Annotated[AsyncSession, Depends(get_db)]
):
    if not post_update.title and not post_update.content:
        return {"success": True, "message": "post updated!"}

    result = await db.execute(
        select(Post).where(Post.id == post_id).options(selectinload(Post.author))
    )
    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found!"
        )

    update_data = post_update.model_dump(exclude_unset=True)
    for filed, value in update_data.items():
        setattr(post, filed, value)

    await db.commit()
    await db.refresh(post, attribute_names=["author"])

    return post


@router.delete("/api/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found!"
        )

    await db.delete(post)
    await db.commit()
