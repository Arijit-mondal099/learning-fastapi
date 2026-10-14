from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.security import OAuth2PasswordRequestForm
from PIL import UnidentifiedImageError
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.concurrency import run_in_threadpool

from auth import (
    CurrentUser,
    generate_access_token,
    hash_password,
    verify_password,
)
from config import get_settings
from database import get_db
from image_utils import delete_image, process_image
from models import Post, User
from schemas import (
    PaginationPosts,
    PostResponse,
    Token,
    UserCreate,
    UserPrivate,
    UserPublic,
    UserUpdate,
)

router = APIRouter()


@router.post(
    "/",
    response_model=UserPrivate,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(User).where(func.lower(User.username) == user.username.lower())
    )
    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exist!"
        )

    result = await db.execute(
        select(User).where(func.lower(User.email) == user.email.lower())
    )
    existing_email = result.scalars().first()

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exist!"
        )

    new_user = User(
        username=user.username.lower(),
        email=user.email.lower(),
        password_hash=hash_password(user.password),
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


@router.post("/token", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(User).where(
            or_(
                func.lower(User.username) == form_data.username.lower(),
                func.lower(User.email) == form_data.username.lower(),
            )
        )
    )
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid creadintails!",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = generate_access_token(subject=str(user.id))
    return {"access_token": access_token, "token_type": "Bearer"}


@router.get("/me", response_model=UserPrivate)
async def current_user(user: CurrentUser):
    return user


@router.get("/{user_id}", response_model=UserPublic)
async def get_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found!"
        )

    return user


@router.get("/{user_id}/posts", response_model=PaginationPosts)
async def get_user_posts(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 5,
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found!"
        )

    count_result = await db.execute(select(func.count()).select_from(Post))
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Post)
        .where(Post.user_id == user.id)
        .options(selectinload(Post.author))
        .offset(skip)
        .limit(limit)
    )
    posts = result.scalars().all()
    has_more = (skip + len(posts)) < total

    return PaginationPosts(
        posts=[PostResponse.model_validate(post) for post in posts],
        total=total,
        skip=skip,
        limit=limit,
        has_more=has_more,
    )


@router.patch("/{user_id}", response_model=UserPrivate)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized to update user profile!",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found!"
        )

    if (
        user_update.username is not None
        and user_update.username.lower() != user.username.lower()
    ):
        result = await db.execute(
            select(User).where(
                func.lower(User.username) == user_update.username.lower()
            )
        )
        existing_username = result.scalars().first()

        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username is already exist!",
            )

    if (
        user_update.email is not None
        and user_update.email.lower() != user.email.lower()
    ):
        result = await db.execute(
            select(User).where(func.lower(User.email) == user_update.email.lower())
        )
        existing_email = result.scalars().first()

        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already exist!",
            )

    if user_update.username:
        user.username = user_update.username.lower()
    if user_update.email:
        user.email = user_update.email.lower()

    await db.commit()
    await db.refresh(user)

    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized to delete the user account!",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found!"
        )

    profile_pic = user.profile_image

    await db.delete(user)
    await db.commit()

    if profile_pic:
        delete_image(profile_pic)


@router.patch("/{user_id}/picture", response_model=UserPrivate)
async def upload_profile_pic(
    user_id: int,
    file: UploadFile,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized to update user profile pic!",
        )

    content = await file.read()

    if len(content) > get_settings().max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large, max size is {get_settings().max_upload_size_bytes // (1024 * 1024)}MB",
        )

    try:
        # Process image in worker thread, Don't block the main thread
        new_filename = await run_in_threadpool(process_image, content)
    except UnidentifiedImageError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invlaid file please upload a valid image (JPEG, PNG)",
        ) from exc

    old_file = current_user.profile_image
    current_user.profile_image = new_filename

    await db.commit()
    await db.refresh(current_user)

    if old_file:
        delete_image(old_file)

    return current_user


@router.delete("/{user_id}/picture", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile_pic(
    user_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized to delete user profile pic!",
        )

    profile_pic = current_user.profile_image

    if profile_pic is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No profile pic to delete"
        )

    current_user.profile_image = None
    await db.commit()
    await db.refresh(current_user)

    delete_image(profile_pic)
