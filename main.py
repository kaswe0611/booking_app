# main.py
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import date

from database import SessionLocal, engine, Base
import models
import schemas

# 建立資料表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Account Book API",
    description="Step 1: 分類 + 時間區間 + 金額總和",
    version="0.1.0"
)


# ======== DB 依賴注入 ========

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ======== Category APIs ========

@app.post("/api/categories", response_model=schemas.CategoryRead)
def create_category(category: schemas.CategoryCreate, db: Session = Depends(get_db)):
    # 檢查是否重複
    existing = db.query(models.Category).filter(models.Category.name == category.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")

    db_category = models.Category(name=category.name)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


@app.get("/api/categories", response_model=List[schemas.CategoryRead])
def get_categories(db: Session = Depends(get_db)):
    return db.query(models.Category).all()


# ======== Transaction APIs ========

@app.post("/api/transactions", response_model=schemas.TransactionRead)
def create_transaction(tx: schemas.TransactionCreate, db: Session = Depends(get_db)):
    # 確認 category 存在
    category = db.query(models.Category).filter(models.Category.id == tx.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    db_tx = models.Transaction(
        date=tx.date,
        category_id=tx.category_id,
        amount=tx.amount,
        note=tx.note
    )
    db.add(db_tx)
    db.commit()
    db.refresh(db_tx)
    return db_tx

# ======== GET /api/transactions ========
@app.get("/api/transactions", response_model=List[schemas.TransactionRead])
def list_transactions(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    取得交易明細列表：
    - 可用 start_date / end_date 篩日期
    - 可用 category_id 篩分類
    - 預設全部資料（照日期+id 由新到舊）
    """
    query = db.query(models.Transaction)

    if start_date is not None:
        query = query.filter(models.Transaction.date >= start_date)

    if end_date is not None:
        query = query.filter(models.Transaction.date <= end_date)

    if category_id is not None:
        query = query.filter(models.Transaction.category_id == category_id)

    # 照日期由新到舊，如果同一天就照 id 由新到舊
    query = query.order_by(models.Transaction.date.desc(), models.Transaction.id.desc())

    return query.all()

# ======== Summary API ========

@app.get("/api/summary", response_model=schemas.SummaryResponse)
def get_summary(
    start_date: date,
    end_date: date,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    取得某時間區間的總金額
    - 必填：start_date, end_date
    - 選填：category_id -> 若有給，只算該分類
    """

    query = db.query(func.sum(models.Transaction.amount))

    query = query.filter(
        models.Transaction.date >= start_date,
        models.Transaction.date <= end_date
    )

    category_name = None

    if category_id is not None:
        query = query.filter(models.Transaction.category_id == category_id)
        category = db.query(models.Category).filter(models.Category.id == category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        category_name = category.name

    total = query.scalar()  # 可能是 None
    total_amount = total if total is not None else 0

    return schemas.SummaryResponse(
        start_date=start_date,
        end_date=end_date,
        total_amount=total_amount,
        category_id=category_id,
        category_name=category_name
    )


# main.py（FastAPI 主程式 + API endpoints）

# POST /categories：新增分類

# GET /categories：取得所有分類

# POST /transactions：新增收支紀錄

# GET /summary：給一段日期（可選分類），算總金額