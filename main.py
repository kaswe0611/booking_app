# main.py
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import date, datetime
from dateutil.relativedelta import relativedelta # 需要安裝 python-dateutil

from database import SessionLocal, engine, Base
import models
import schemas
from schemas import CategorySummary # 確保這個 Schema 已經定義在 schemas.py 中


# 建立資料表 (重要：如果 models.py 變了，請刪除 account_book.db 後再運行)
# 確保您已經在 models.py, schemas.py 中更新了所有新欄位！
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Account Book API",
    # 💡 建議更新版本號和描述，反映新功能
    description="Step 2: 儀表板、預算、付款方式與週期交易",
    version="0.2.0"
)


# ======== DB 依賴注入 ========

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ======== Category APIs (已更新) ========

@app.post("/api/categories", response_model=schemas.CategoryRead)
def create_category(category: schemas.CategoryCreate, db: Session = Depends(get_db)):
    # 檢查是否重複
    existing = db.query(models.Category).filter(models.Category.name == category.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")

    # ✅ 修正：傳入所有新的欄位
    db_category = models.Category(
        name=category.name,
        icon_name=category.icon_name,
        color_code=category.color_code,
        monthly_budget=category.monthly_budget
    )
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


@app.get("/api/categories", response_model=List[schemas.CategoryRead])
def get_categories(db: Session = Depends(get_db)):
    # 查詢並回傳所有分類
    return db.query(models.Category).all()


# ======== Transaction APIs (已更新) ========

@app.post("/api/transactions", response_model=schemas.TransactionRead)
def create_transaction(tx: schemas.TransactionCreate, db: Session = Depends(get_db)):
    # 確認 category 存在
    category = db.query(models.Category).filter(models.Category.id == tx.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # ✅ 修正：傳入所有新的欄位
    db_tx = models.Transaction(
        date=tx.date,
        category_id=tx.category_id,
        amount=tx.amount,
        note=tx.note,
        merchant=tx.merchant,
        payment_method=tx.payment_method,      # 新欄位
        is_recurring=tx.is_recurring           # 新欄位
    )
    db.add(db_tx)
    db.commit()
    db.refresh(db_tx)
    return db_tx

# ======== GET /api/transactions (不變) ========
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

# ======== Summary API (不變) ========

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

# ======== Dashboard Summary API (已新增) ========

@app.get("/api/dashboard/monthly_summary", response_model=List[CategorySummary])
def get_monthly_dashboard_summary(
    db: Session = Depends(get_db)
):
    """
    取得所有分類在當前月份的總支出與預算資訊，用於主頁儀表板。
    """
    today = date.today()
    # 取得當月的第一天
    start_of_month = today.replace(day=1) 
    # 取得下月的第一天，作為結束日期 (不包含)
    end_of_month = start_of_month + relativedelta(months=1)

    # 查詢當月所有交易，按 category_id 分組並計算總和
    summary_query = (
        db.query(
            models.Transaction.category_id,
            func.sum(models.Transaction.amount).label("total_spent")
        )
        .filter(models.Transaction.date >= start_of_month)
        .filter(models.Transaction.date < end_of_month)
        .group_by(models.Transaction.category_id)
    )
    
    spent_data = summary_query.all()
    
    # 將總支出資料轉換為 {category_id: total_spent} 字典，方便查詢
    spent_map = {item.category_id: item.total_spent for item in spent_data}
    
    # 取得所有分類資訊
    categories = db.query(models.Category).all()

    response_list = []
    for category in categories:
        total_spent = spent_map.get(category.id, 0)
        
        # 建立回覆物件，將 SQLAlchemy model 轉換為 Pydantic schema
        summary_data = CategorySummary(
            id=category.id,
            name=category.name,
            icon_name=category.icon_name,
            color_code=category.color_code,
            monthly_budget=category.monthly_budget,
            total_spent=total_spent
        )
        response_list.append(summary_data)
        
    return response_list