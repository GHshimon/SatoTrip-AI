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
    _apply_simple_migrations()


def _apply_simple_migrations():
    """
    既存テーブルへの後付けカラム追加（簡易マイグレーション）。
    create_all は新規テーブルしか作らないため、既存テーブルに対しては
    「存在しなければ ALTER TABLE ADD COLUMN」を試みる。
    SQLite / PostgreSQL どちらも「既に存在する」場合はエラーになるので、
    素朴に try/except で握りつぶす（冪等）。
    """
    from sqlalchemy import text

    statements = [
        "ALTER TABLE subscriptions ADD COLUMN stripe_customer_id VARCHAR",
        "ALTER TABLE subscriptions ADD COLUMN stripe_subscription_id VARCHAR",
        # スポットの出所・検証カラム（docs/design/SPOT_FIELD_SPEC.md §2）
        "ALTER TABLE spots ADD COLUMN source VARCHAR",
        "ALTER TABLE spots ADD COLUMN verification_status VARCHAR DEFAULT 'unverified'",
        "ALTER TABLE spots ADD COLUMN verified_at TIMESTAMP",
        "ALTER TABLE spots ADD COLUMN verification_score FLOAT",
        "ALTER TABLE spots ADD COLUMN business_status VARCHAR",
        "ALTER TABLE spots ADD COLUMN rating_count INTEGER",
        "ALTER TABLE spots ADD COLUMN price_level INTEGER",
        "ALTER TABLE spots ADD COLUMN price_range_min INTEGER",
        "ALTER TABLE spots ADD COLUMN price_range_max INTEGER",
        "ALTER TABLE spots ADD COLUMN opening_hours JSON",
        "ALTER TABLE spots ADD COLUMN description_source VARCHAR",
        "ALTER TABLE spots ADD COLUMN field_provenance JSON",
        "ALTER TABLE spots ADD COLUMN rejected_reason VARCHAR",
    ]
    for stmt in statements:
        # DDLごとに接続を分ける（失敗したトランザクションを持ち越さないため）
        try:
            with engine.connect() as conn:
                conn.execute(text(stmt))
                conn.commit()
        except Exception:
            # カラムが既に存在する等。起動を妨げない。
            pass
