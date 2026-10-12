from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class PostBase(BaseModel):
    title: Annotated[str, Field(..., min_length=1, max_length=50)]
    content: Annotated[str, Field(..., min_length=1, max_length=100)]
    author: Annotated[str, Field(..., min_length=1, max_length=50)]


class PostCreate(PostBase):
    pass


class PostResponse(PostBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date_posted: str
