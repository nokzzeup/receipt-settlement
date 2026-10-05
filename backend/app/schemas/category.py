from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.schemas.common import NonNegativeWon

CategoryName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    # 원 단위. null = 예산 미설정
    budget_amount: int | None


class CategoryCreate(BaseModel):
    name: CategoryName
    budget_amount: NonNegativeWon | None = None


class CategoryUpdate(BaseModel):
    """보낸 필드만 바뀐다. budget_amount: null 을 보내면 예산 해제"""

    name: CategoryName | None = None
    budget_amount: NonNegativeWon | None = None
