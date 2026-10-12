from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# Users schemas
class UserBase(BaseModel):
    username: Annotated[str, Field(..., min_length=4, max_length=16)]
    email: Annotated[EmailStr, Field(..., max_length=100)]


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    username: Annotated[str | None, Field(default=None, min_length=4, max_length=16)]
    email: Annotated[EmailStr | None, Field(default=None, max_length=100)]
    profile_image: Annotated[str | None, Field(default=None)]


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    profile_image: str | None = None
    image_path: str


# Posts schemas
class PostBase(BaseModel):
    title: Annotated[str, Field(..., min_length=1, max_length=50)]
    content: Annotated[str, Field(..., min_length=1)]


class PostCreate(PostBase):
    user_id: int


class PostUpdate(BaseModel):
    title: Annotated[str | None, Field(default=None, min_length=1, max_length=50)]
    content: Annotated[str | None, Field(default=None, min_length=1)]


class PostResponse(PostBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    date_posted: datetime
    author: UserResponse
