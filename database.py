# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# ✅ 目前本機用 SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///./account_book.db"

# 如果之後要改 MySQL，大概長這樣：
# SQLALCHEMY_DATABASE_URL = "mysql+mysqlconnector://user:password@localhost:3306/account_book"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}  # 只用在 SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# database.py（資料庫設定）