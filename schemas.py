# schemas.py
from datetime import date
from typing import Optional, List
from pydantic import BaseModel


# ===== Category =====

class CategoryBase(BaseModel):
    name: str
    icon_name: Optional[str] = "default_icon"
    color_code: Optional[str] = "#CCCCCC"
    monthly_budget: Optional[int] = 0

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
    merchant: Optional[str] = None

    payment_method: Optional[str] = None
    is_recurring: Optional[bool] = False


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


class CategorySummary(CategoryRead):
    """繼承 CategoryRead，並新增本期總支出"""
    total_spent: int
    
# schemas.py（Pydantic：定義 API 用的資料格式）