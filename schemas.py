# schemas.py
from datetime import date
from typing import Optional, List
from pydantic import BaseModel


# ===== Category =====

class CategoryBase(BaseModel):
    name: str


class CategoryCreate(CategoryBase):
    pass


class CategoryRead(CategoryBase):
    id: int

    class Config:
        orm_mode = True


# ===== Transaction =====

class TransactionBase(BaseModel):
    date: date
    category_id: int
    amount: int
    note: Optional[str] = None


class TransactionCreate(TransactionBase):
    pass


class TransactionRead(TransactionBase):
    id: int

    class Config:
        orm_mode = True


# ===== Summary =====

class SummaryResponse(BaseModel):
    start_date: date
    end_date: date
    total_amount: int
    category_id: Optional[int] = None
    category_name: Optional[str] = None

# schemas.py（Pydantic：定義 API 用的資料格式）