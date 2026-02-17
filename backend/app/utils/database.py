"""
データベース接続とセッション管理
SQLAlchemyを使用
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings
import os

# データベースディレクトリを作成
db_path = settings.DATABASE_URL.replace("sqlite:///", "")
if db_path != settings.DATABASE_URL:  # SQLiteの場合
    os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)

# SQLAlchemyエンジン
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

# セッションファクトリ
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ベースクラス
Base = declarative_base()


def get_db() -> Session:
    """
    データベースセッションを取得
    依存性注入で使用
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """データベースを初期化（テーブル作成）"""
    Base.metadata.create_all(bind=engine)
