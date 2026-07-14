"""
テスト共通フィクスチャ

- ライブAPI（YouTube/Places/Gemini）は一切呼ばない純ロジックのテストを対象にする。
- DBが必要なテストはインメモリSQLiteで完結させる。
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture()
def db_session():
    """インメモリSQLiteのセッション（予算テスト用に places_monthly_usage のみ作成）。

    全テーブルを作らないのは、モデル間のFK（Plan→plan_folders 等）の解決に
    全モデルの import が必要で、テストの独立性を損なうため。ここで必要なのは
    月次使用量テーブルのみ。
    """
    from app.models.places_usage import PlacesMonthlyUsage

    engine = create_engine("sqlite:///:memory:")
    PlacesMonthlyUsage.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
