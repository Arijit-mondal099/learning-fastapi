from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# Users schemas
class UserBase(BaseModel):
    username: Annotated[str, Field(..., min_length=4, max_length=16)]
    email: Annotated[EmailStr, Field(..., max_length=100)]


class UserCreate(UserBase):
    password: Annotated[str, Field(..., min_length=8)]


class UserUpdate(BaseModel):
    username: Annotated[str | None, Field(default=None, min_length=4, max_length=16)]
    email: Annotated[EmailStr | None, Field(default=None, max_length=100)]


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    profile_image: str | None = None
    image_path: str


class UserPrivate(UserPublic):
    model_config = ConfigDict(from_attributes=True)

    email: EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str = "Bearer"


# Posts schemas
class PostBase(BaseModel):
    title: Annotated[str, Field(..., min_length=1, max_length=50)]
    content: Annotated[str, Field(..., min_length=1)]


class PostCreate(PostBase):
    pass


class PostUpdate(BaseModel):
    title: Annotated[str | None, Field(default=None, min_length=1, max_length=50)]
    content: Annotated[str | None, Field(default=None, min_length=1)]


class PostResponse(PostBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    date_posted: datetime
    author: UserPublic
